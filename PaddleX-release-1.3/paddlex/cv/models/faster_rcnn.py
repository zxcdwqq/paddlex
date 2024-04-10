# copyright (c) 2020 PaddlePaddle Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import
import math
import tqdm
import numpy as np
from multiprocessing.pool import ThreadPool
import paddle.fluid as fluid
import paddlex.utils.logging as logging
import paddlex
import os.path as osp
import copy
from paddlex.cv.transforms import arrange_transforms
from paddlex.cv.datasets import generate_minibatch
from .base import BaseAPI
from collections import OrderedDict
from .utils.detection_eval import eval_results, bbox2out


class FasterRCNN(BaseAPI):
    """构建FasterRCNN，并实现其训练、评估、预测和模型导出。

    Args:
        num_classes (int): 包含了背景类的类别数。默认为81。
        backbone (str): FasterRCNN的backbone网络，取值范围为['ResNet18', 'ResNet50',
            'ResNet50_vd', 'ResNet101', 'ResNet101_vd', 'HRNet_W18', 'ResNet50_vd_ssld']。默认为'ResNet50'。
        with_fpn (bool): 是否使用FPN结构。默认为True。
        aspect_ratios (list): 生成anchor高宽比的可选值。默认为[0.5, 1.0, 2.0]。
        anchor_sizes (list): 生成anchor大小的可选值。默认为[32, 64, 128, 256, 512]。
        with_dcn (bool): backbone网络中是否使用deformable convolution network v2。默认为False。
        rpn_cls_loss (str): RPN部分的分类损失函数，取值范围为['SigmoidCrossEntropy', 'SigmoidFocalLoss']。
            当遇到模型误检了很多背景区域时，可以考虑使用'SigmoidFocalLoss'，并调整适合的`rpn_focal_loss_alpha`
            和`rpn_focal_loss_gamma`。默认为'SigmoidCrossEntropy'。
        rpn_focal_loss_alpha (float)：当RPN的分类损失函数设置为'SigmoidFocalLoss'时，用于调整
            正样本和负样本的比例因子，默认为0.25。当PN的分类损失函数设置为'SigmoidCrossEntropy'时，
            `rpn_focal_loss_alpha`的设置不生效。
        rpn_focal_loss_gamma (float): 当RPN的分类损失函数设置为'SigmoidFocalLoss'时，用于调整
            易分样本和难分样本的比例因子，默认为2。当RPN的分类损失函数设置为'SigmoidCrossEntropy'时，
            `rpn_focal_loss_gamma`的设置不生效。
        rcnn_bbox_loss (str): RCNN部分的位置回归损失函数，取值范围为['SmoothL1Loss', 'CIoULoss']。
            默认为'SmoothL1Loss'。
        rcnn_nms (str): RCNN部分的非极大值抑制的计算方法，取值范围为['MultiClassNMS', 'MultiClassSoftNMS',
            'MultiClassCiouNMS']。默认为'MultiClassNMS'。当选择'MultiClassNMS'时，可以将`keep_top_k`设置成100、
            `nms_threshold`设置成0.5、`score_threshold`设置成0.05。当选择'MultiClassSoftNMS'时，可以将`keep_top_k`设置为300、
            `score_threshold`设置为0.01、`softnms_sigma`设置为0.5。当选择'MultiClassCiouNMS'时，可以将`keep_top_k`设置为100、
            `score_threshold`设置成0.05、`nms_threshold`设置成0.5。
        keep_top_k (int): RCNN部分在进行非极大值抑制计算后，每张图像保留最多保存`keep_top_k`个检测框。默认为100。
        nms_threshold (float): RCNN部分在进行非极大值抑制时，用于剔除检测框所需的IoU阈值。
            当`rcnn_nms`设置为`MultiClassSoftNMS`时，`nms_threshold`的设置不生效。默认为0.5。
        score_threshold (float): RCNN部分在进行非极大值抑制前，用于过滤掉低置信度边界框所需的置信度阈值。默认为0.05。
        softnms_sigma (float): 当`rcnn_nms`设置为`MultiClassSoftNMS`时，用于调整被抑制的检测框的置信度，
            调整公式为`score = score * weights, weights = exp(-(iou * iou) / softnms_sigma)`。默认设为0.5。
        bbox_assigner (str): 训练阶段，RCNN部分生成正负样本的采样方式。可选范围为['BBoxAssigner', 'LibraBBoxAssigner']。
            当目标物体的区域只占原始图像的一小部分时，使用`LibraBBoxAssigner`采样方式模型效果更佳。默认为'BBoxAssigner'。
        fpn_num_channels (int): FPN部分特征层的通道数量。默认为256。
        input_channel (int): 输入图像的通道数量。默认为3。
        rpn_batch_size_per_im (int): 训练阶段，RPN部分每张图片的正负样本的数量总和。默认为256。
        rpn_fg_fraction (float): 训练阶段，RPN部分每张图片的正负样本数量总和中正样本的占比。默认为0.5。
        test_pre_nms_top_n (int)：预测阶段，RPN部分做非极大值抑制计算的候选框的数量。若设置为None,
            有FPN结构的话，`test_pre_nms_top_n`会被设置成6000, 无FPN结构的话，`test_pre_nms_top_n`会被设置成
            1000。默认为None。
        test_post_nms_top_n (int): 预测阶段，RPN部分做完非极大值抑制后保留的候选框的数量。默认为1000。
    """

    def __init__(self,
                 num_classes=81,
                 backbone='ResNet50',
                 with_fpn=True,
                 aspect_ratios=[0.5, 1.0, 2.0],
                 anchor_sizes=[32, 64, 128, 256, 512],
                 with_dcn=False,
                 rpn_cls_loss='SigmoidCrossEntropy',
                 rpn_focal_loss_alpha=0.25,
                 rpn_focal_loss_gamma=2,
                 rcnn_bbox_loss='SmoothL1Loss',
                 rcnn_nms='MultiClassNMS',
                 keep_top_k=100,
                 nms_threshold=0.5,
                 score_threshold=0.05,
                 softnms_sigma=0.5,
                 bbox_assigner='BBoxAssigner',
                 fpn_num_channels=256,
                 input_channel=3,
                 rpn_batch_size_per_im=256,
                 rpn_fg_fraction=0.5,
                 test_pre_nms_top_n=None,
                 test_post_nms_top_n=1000):
        self.init_params = locals()
        super(FasterRCNN, self).__init__('detector')
        backbones = [
            'ResNet18', 'ResNet50', 'ResNet50_vd', 'ResNet101', 'ResNet101_vd',
            'HRNet_W18', 'ResNet50_vd_ssld'
        ]
        assert backbone in backbones, "backbone should be one of {}".format(
            backbones)
        self.backbone = backbone
        self.num_classes = num_classes
        self.with_fpn = with_fpn
        self.aspect_ratios = aspect_ratios
        self.anchor_sizes = anchor_sizes
        self.labels = None
        self.fixed_input_shape = None
        self.with_dcn = with_dcn
        rpn_cls_losses = ['SigmoidFocalLoss', 'SigmoidCrossEntropy']
        assert rpn_cls_loss in rpn_cls_losses, "rpn_cls_loss should be one of {}".format(
            rpn_cls_losses)
        self.rpn_cls_loss = rpn_cls_loss
        self.rpn_focal_loss_alpha = rpn_focal_loss_alpha
        self.rpn_focal_loss_gamma = rpn_focal_loss_gamma
        self.rcnn_bbox_loss = rcnn_bbox_loss
        self.rcnn_nms = rcnn_nms
        self.keep_top_k = keep_top_k
        self.nms_threshold = nms_threshold
        self.score_threshold = score_threshold
        self.softnms_sigma = softnms_sigma
        self.bbox_assigner = bbox_assigner
        self.fpn_num_channels = fpn_num_channels
        self.input_channel = input_channel
        self.rpn_batch_size_per_im = rpn_batch_size_per_im
        self.rpn_fg_fraction = rpn_fg_fraction
        self.test_pre_nms_top_n = test_pre_nms_top_n
        self.test_post_nms_top_n = test_post_nms_top_n

    def _get_backbone(self, backbone_name):
        norm_type = None
        lr_mult_list = [1.0, 1.0, 1.0, 1.0, 1.0]
        if backbone_name == 'ResNet18':
            layers = 18
            variant = 'b'
        elif backbone_name == 'ResNet50':
            layers = 50
            variant = 'b'
        elif backbone_name == 'ResNet50_vd':
            layers = 50
            variant = 'd'
            norm_type = 'affine_channel'
        elif backbone_name == 'ResNet101':
            layers = 101
            variant = 'b'
            norm_type = 'affine_channel'
        elif backbone_name == 'ResNet101_vd':
            layers = 101
            variant = 'd'
            norm_type = 'affine_channel'
        elif backbone_name == 'HRNet_W18':
            backbone = paddlex.cv.nets.hrnet.HRNet(
                width=18, freeze_norm=True, norm_decay=0., freeze_at=0)
            if self.with_fpn is False:
                self.with_fpn = True
            return backbone
        elif backbone_name == 'ResNet50_vd_ssld':
            layers = 50
            variant = 'd'
            norm_type = 'bn'
            lr_mult_list = [1.0, 0.05, 0.05, 0.1, 0.15]
        if self.with_fpn:
            backbone = paddlex.cv.nets.resnet.ResNet(
                norm_type='bn' if norm_type is None else norm_type,
                layers=layers,
                variant=variant,
                freeze_norm=True,
                norm_decay=0.,
                feature_maps=[2, 3, 4, 5],
                freeze_at=2,
                lr_mult_list=lr_mult_list,
                dcn_v2_stages=[3, 4, 5] if self.with_dcn else [])
        else:
            backbone = paddlex.cv.nets.resnet.ResNet(
                norm_type='affine_channel' if norm_type is None else norm_type,
                layers=layers,
                variant=variant,
                freeze_norm=True,
                norm_decay=0.,
                feature_maps=4,
                freeze_at=2,
                lr_mult_list=lr_mult_list,
                dcn_v2_stages=[3, 4, 5] if self.with_dcn else [])
        return backbone

    def build_net(self, mode='train'):
        train_pre_nms_top_n = 2000 if self.with_fpn else 12000
        test_pre_nms_top_n = 1000 if self.with_fpn else 6000
        if self.test_pre_nms_top_n is not None:
            test_pre_nms_top_n = self.test_pre_nms_top_n
        model = paddlex.cv.nets.detection.FasterRCNN(
            backbone=self._get_backbone(self.backbone),
            mode=mode,
            num_classes=self.num_classes,
            with_fpn=self.with_fpn,
            aspect_ratios=self.aspect_ratios,
            anchor_sizes=self.anchor_sizes,
            train_pre_nms_top_n=train_pre_nms_top_n,
            test_pre_nms_top_n=test_pre_nms_top_n,
            fixed_input_shape=self.fixed_input_shape,
            rpn_cls_loss=self.rpn_cls_loss,
            rpn_focal_loss_alpha=self.rpn_focal_loss_alpha,
            rpn_focal_loss_gamma=self.rpn_focal_loss_gamma,
            rcnn_bbox_loss=self.rcnn_bbox_loss,
            rcnn_nms=self.rcnn_nms,
            keep_top_k=self.keep_top_k,
            nms_threshold=self.nms_threshold,
            score_threshold=self.score_threshold,
            softnms_sigma=self.softnms_sigma,
            bbox_assigner=self.bbox_assigner,
            fpn_num_channels=self.fpn_num_channels,
            input_channel=self.input_channel,
            rpn_batch_size_per_im=self.rpn_batch_size_per_im,
            rpn_fg_fraction=self.rpn_fg_fraction,
            test_post_nms_top_n=self.test_post_nms_top_n)
        inputs = model.generate_inputs()
        if mode == 'train':
            model_out = model.build_net(inputs)
            loss = model_out['loss']
            self.optimizer.minimize(loss)
            outputs = OrderedDict(
                [('loss', model_out['loss']),
                 ('loss_cls', model_out['loss_cls']),
                 ('loss_bbox', model_out['loss_bbox']),
                 ('loss_rpn_cls', model_out['loss_rpn_cls']), (
                     'loss_rpn_bbox', model_out['loss_rpn_bbox'])])
        else:
            outputs = model.build_net(inputs)
        return inputs, outputs

    def default_optimizer(self, learning_rate, warmup_steps, warmup_start_lr,
                          lr_decay_epochs, lr_decay_gamma,
                          num_steps_each_epoch):
        if warmup_steps > lr_decay_epochs[0] * num_steps_each_epoch:
            logging.error(
                "In function train(), parameters should satisfy: warmup_steps <= lr_decay_epochs[0]*num_samples_in_train_dataset",
                exit=False)
            logging.error(
                "See this doc for more information: https://github.com/PaddlePaddle/PaddleX/blob/develop/docs/appendix/parameters.md#notice",
                exit=False)
            logging.error(
                "warmup_steps should less than {} or lr_decay_epochs[0] greater than {}, please modify 'lr_decay_epochs' or 'warmup_steps' in train function".
                format(lr_decay_epochs[0] * num_steps_each_epoch, warmup_steps
                       // num_steps_each_epoch))
        boundaries = [b * num_steps_each_epoch for b in lr_decay_epochs]
        values = [(lr_decay_gamma**i) * learning_rate
                  for i in range(len(lr_decay_epochs) + 1)]
        lr_decay = fluid.layers.piecewise_decay(
            boundaries=boundaries, values=values)
        lr_warmup = fluid.layers.linear_lr_warmup(
            learning_rate=lr_decay,
            warmup_steps=warmup_steps,
            start_lr=warmup_start_lr,
            end_lr=learning_rate)
        optimizer = fluid.optimizer.Momentum(
            learning_rate=lr_warmup,
            momentum=0.9,
            regularization=fluid.regularizer.L2Decay(1e-04))
        return optimizer

    def train(self,
              num_epochs,
              train_dataset,
              train_batch_size=2,
              eval_dataset=None,
              save_interval_epochs=1,
              log_interval_steps=2,
              save_dir='output',
              pretrain_weights='IMAGENET',
              optimizer=None,
              learning_rate=0.0025,
              warmup_steps=500,
              warmup_start_lr=1.0 / 1200,
              lr_decay_epochs=[8, 11],
              lr_decay_gamma=0.1,
              metric=None,
              use_vdl=False,
              early_stop=False,
              early_stop_patience=5,
              resume_checkpoint=None,
              sensitivities_file=None,
              eval_metric_loss=0.05):
        """训练。

        Args:
            num_epochs (int): 训练迭代轮数。
            train_dataset (paddlex.datasets): 训练数据读取器。
            train_batch_size (int): 训练数据batch大小。目前检测仅支持单卡评估，训练数据batch大小与
                显卡数量之商为验证数据batch大小。默认为2。
            eval_dataset (paddlex.datasets): 验证数据读取器。
            save_interval_epochs (int): 模型保存间隔（单位：迭代轮数）。默认为1。
            log_interval_steps (int): 训练日志输出间隔（单位：迭代次数）。默认为20。
            save_dir (str): 模型保存路径。默认值为'output'。
            pretrain_weights (str): 若指定为路径时，则加载路径下预训练模型；若为字符串'IMAGENET'，
                则自动下载在ImageNet图片数据上预训练的模型权重；若为字符串'COCO'，
                则自动下载在COCO数据集上预训练的模型权重；若为None，则不使用预训练模型。默认为'IMAGENET'。
            optimizer (paddle.fluid.optimizer): 优化器。当该参数为None时，使用默认优化器：
                fluid.layers.piecewise_decay衰减策略，fluid.optimizer.Momentum优化方法。
            learning_rate (float): 默认优化器的初始学习率。默认为0.0025。
            warmup_steps (int):  默认优化器进行warmup过程的步数。默认为500。
            warmup_start_lr (int): 默认优化器warmup的起始学习率。默认为1.0/1200。
            lr_decay_epochs (list): 默认优化器的学习率衰减轮数。默认为[8, 11]。
            lr_decay_gamma (float): 默认优化器的学习率衰减率。默认为0.1。
            metric (bool): 训练过程中评估的方式，取值范围为['COCO', 'VOC']。默认值为None。
            use_vdl (bool): 是否使用VisualDL进行可视化。默认值为False。
            early_stop (bool): 是否使用提前终止训练策略。默认值为False。
            early_stop_patience (int): 当使用提前终止训练策略时，如果验证集精度在`early_stop_patience`个epoch内
                连续下降或持平，则终止训练。默认值为5。
            resume_checkpoint (str): 恢复训练时指定上次训练保存的模型路径。若为None，则不会恢复训练。默认值为None。
            sensitivities_file (str): 若指定为路径时，则加载路径下敏感度信息进行裁剪；若为字符串'DEFAULT'，
                则自动下载在ImageNet图片数据上获得的敏感度信息进行裁剪；若为None，则不进行裁剪。默认为None。
            eval_metric_loss (float): 可容忍的精度损失。默认为0.05。

        Raises:
            ValueError: 评估类型不在指定列表中。
            ValueError: 模型从inference model进行加载。
        """
        if metric is None:
            if isinstance(train_dataset, paddlex.datasets.CocoDetection):
                metric = 'COCO'
            elif isinstance(train_dataset, paddlex.datasets.VOCDetection) or \
                    isinstance(train_dataset, paddlex.datasets.EasyDataDet):
                metric = 'VOC'
            else:
                raise ValueError(
                    "train_dataset should be datasets.VOCDetection or datasets.COCODetection or datasets.EasyDataDet."
                )
        assert metric in ['COCO', 'VOC'], "Metric only support 'VOC' or 'COCO'"
        self.metric = metric
        if not self.trainable:
            raise ValueError("Model is not trainable from load_model method.")
        self.labels = copy.deepcopy(train_dataset.labels)
        self.labels.insert(0, 'background')
        # 构建训练网络
        if optimizer is None:
            # 构建默认的优化策略
            num_steps_each_epoch = train_dataset.num_samples // train_batch_size
            optimizer = self.default_optimizer(
                learning_rate, warmup_steps, warmup_start_lr, lr_decay_epochs,
                lr_decay_gamma, num_steps_each_epoch)
        self.optimizer = optimizer
        # 构建训练、验证、测试网络
        self.build_program()
        fuse_bn = True
        if self.with_fpn and self.backbone in [
                'ResNet18', 'ResNet50', 'HRNet_W18'
        ]:
            fuse_bn = False
        self.net_initialize(
            startup_prog=fluid.default_startup_program(),
            pretrain_weights=pretrain_weights,
            fuse_bn=fuse_bn,
            save_dir=save_dir,
            resume_checkpoint=resume_checkpoint,
            sensitivities_file=sensitivities_file,
            eval_metric_loss=eval_metric_loss)

        # 训练
        self.train_loop(
            num_epochs=num_epochs,
            train_dataset=train_dataset,
            train_batch_size=train_batch_size,
            eval_dataset=eval_dataset,
            save_interval_epochs=save_interval_epochs,
            log_interval_steps=log_interval_steps,
            save_dir=save_dir,
            use_vdl=use_vdl,
            early_stop=early_stop,
            early_stop_patience=early_stop_patience)

    def evaluate(self,
                 eval_dataset,
                 batch_size=1,
                 epoch_id=None,
                 metric=None,
                 return_details=False):
        """评估。

        Args:
            eval_dataset (paddlex.datasets): 验证数据读取器。
            batch_size (int): 验证数据批大小。默认为1。当前只支持设置为1。
            epoch_id (int): 当前评估模型所在的训练轮数。
            metric (bool): 训练过程中评估的方式，取值范围为['COCO', 'VOC']。默认为None，
                根据用户传入的Dataset自动选择，如为VOCDetection，则metric为'VOC';
                如为COCODetection，则metric为'COCO'。
            return_details (bool): 是否返回详细信息。默认值为False。

        Returns:
            tuple (metrics, eval_details) /dict (metrics): 当return_details为True时，返回(metrics, eval_details)，
                当return_details为False时，返回metrics。metrics为dict，包含关键字：'bbox_mmap'或者’bbox_map‘，
                分别表示平均准确率平均值在各个阈值下的结果取平均值的结果（mmAP）、平均准确率平均值（mAP）。
                eval_details为dict，包含bbox和gt两个关键字。其中关键字bbox的键值是一个列表，列表中每个元素代表一个预测结果，
                一个预测结果是一个由图像id，预测框类别id, 预测框坐标，预测框得分组成的列表。而关键字gt的键值是真实标注框的相关信息。
        """

        input_channel = getattr(self, 'input_channel', 3)
        arrange_transforms(
            model_type=self.model_type,
            class_name=self.__class__.__name__,
            transforms=eval_dataset.transforms,
            mode='eval',
            input_channel=input_channel)
        if metric is None:
            if hasattr(self, 'metric') and self.metric is not None:
                metric = self.metric
            else:
                if isinstance(eval_dataset, paddlex.datasets.CocoDetection):
                    metric = 'COCO'
                elif isinstance(eval_dataset, paddlex.datasets.VOCDetection):
                    metric = 'VOC'
                else:
                    raise Exception(
                        "eval_dataset should be datasets.VOCDetection or datasets.COCODetection."
                    )
        assert metric in ['COCO', 'VOC'], "Metric only support 'VOC' or 'COCO'"
        if batch_size > 1:
            batch_size = 1
            logging.warning(
                "Faster RCNN supports batch_size=1 only during evaluating, so batch_size is forced to be set to 1."
            )
        dataset = eval_dataset.generator(
            batch_size=batch_size, drop_last=False)

        total_steps = math.ceil(eval_dataset.num_samples * 1.0 / batch_size)
        results = list()
        logging.info(
            "Start to evaluating(total_samples={}, total_steps={})...".format(
                eval_dataset.num_samples, total_steps))
        for step, data in tqdm.tqdm(enumerate(dataset()), total=total_steps):
            images = np.array([d[0] for d in data]).astype('float32')
            im_infos = np.array([d[1] for d in data]).astype('float32')
            im_shapes = np.array([d[3] for d in data]).astype('float32')
            feed_data = {
                'image': images,
                'im_info': im_infos,
                'im_shape': im_shapes,
            }
            with fluid.scope_guard(self.scope):
                outputs = self.exe.run(
                    self.test_prog,
                    feed=[feed_data],
                    fetch_list=list(self.test_outputs.values()),
                    return_numpy=False)
            res = {
                'bbox': (np.array(outputs[0]),
                         outputs[0].recursive_sequence_lengths())
            }
            res_im_id = [d[2] for d in data]
            res['im_info'] = (im_infos, [])
            res['im_shape'] = (im_shapes, [])
            res['im_id'] = (np.array(res_im_id), [])
            if metric == 'VOC':
                res_gt_box = []
                res_gt_label = []
                res_is_difficult = []
                for d in data:
                    res_gt_box.extend(d[4])
                    res_gt_label.extend(d[5])
                    res_is_difficult.extend(d[6])
                res_gt_box_lod = [d[4].shape[0] for d in data]
                res_gt_label_lod = [d[5].shape[0] for d in data]
                res_is_difficult_lod = [d[6].shape[0] for d in data]
                res['gt_box'] = (np.array(res_gt_box), [res_gt_box_lod])
                res['gt_label'] = (np.array(res_gt_label), [res_gt_label_lod])
                res['is_difficult'] = (np.array(res_is_difficult),
                                       [res_is_difficult_lod])
            results.append(res)
            logging.debug("[EVAL] Epoch={}, Step={}/{}".format(epoch_id, step +
                                                               1, total_steps))
        box_ap_stats, eval_details = eval_results(
            results, metric, eval_dataset.coco_gt, with_background=True)
        metrics = OrderedDict(
            zip(['bbox_mmap'
                 if metric == 'COCO' else 'bbox_map'], box_ap_stats))
        if return_details:
            return metrics, eval_details
        return metrics

    @staticmethod
    def _preprocess(images,
                    transforms,
                    model_type,
                    class_name,
                    thread_pool=None,
                    input_channel=3):
        arrange_transforms(
            model_type=model_type,
            class_name=class_name,
            transforms=transforms,
            mode='test',
            input_channel=input_channel)
        if thread_pool is not None:
            batch_data = thread_pool.map(transforms, images)
        else:
            batch_data = list()
            for image in images:
                batch_data.append(transforms(image))
        padding_batch = generate_minibatch(batch_data)
        im = np.array([data[0] for data in padding_batch])
        im_resize_info = np.array([data[1] for data in padding_batch])
        im_shape = np.array([data[2] for data in padding_batch])

        return im, im_resize_info, im_shape

    @staticmethod
    def _postprocess(res, batch_size, num_classes, labels):
        clsid2catid = dict({i: i for i in range(num_classes)})
        xywh_results = bbox2out([res], clsid2catid)
        preds = [[] for i in range(batch_size)]
        for xywh_res in xywh_results:
            image_id = xywh_res['image_id']
            del xywh_res['image_id']
            xywh_res['category'] = labels[xywh_res['category_id']]
            preds[image_id].append(xywh_res)

        return preds

    def predict(self, img_file, transforms=None):
        """预测。

        Args:
            img_file(str|np.ndarray): 预测图像路径，或者是解码后的排列格式为（H, W, C）且类型为float32且为BGR格式的数组。
            transforms (paddlex.det.transforms): 数据预处理操作。

        Returns:
            list: 预测结果列表，每个预测结果由预测框类别标签、
              预测框类别名称、预测框坐标(坐标格式为[xmin, ymin, w, h]）、
              预测框得分组成。
        """
        if transforms is None and not hasattr(self, 'test_transforms'):
            raise Exception("transforms need to be defined, now is None.")
        if isinstance(img_file, (str, np.ndarray)):
            images = [img_file]
        else:
            raise Exception("img_file must be str/np.ndarray")

        if transforms is None:
            transforms = self.test_transforms
        input_channel = getattr(self, 'input_channel', 3)
        im, im_resize_info, im_shape = FasterRCNN._preprocess(
            images,
            transforms,
            self.model_type,
            self.__class__.__name__,
            input_channel=input_channel)

        with fluid.scope_guard(self.scope):
            result = self.exe.run(self.test_prog,
                                  feed={
                                      'image': im,
                                      'im_info': im_resize_info,
                                      'im_shape': im_shape
                                  },
                                  fetch_list=list(self.test_outputs.values()),
                                  return_numpy=False,
                                  use_program_cache=True)

        res = {
            k: (np.array(v), v.recursive_sequence_lengths())
            for k, v in zip(list(self.test_outputs.keys()), result)
        }
        res['im_id'] = (np.array(
            [[i] for i in range(len(images))]).astype('int32'), [])
        preds = FasterRCNN._postprocess(res,
                                        len(images), self.num_classes,
                                        self.labels)

        return preds[0]

    def batch_predict(self, img_file_list, transforms=None):
        """预测。

        Args:
            img_file_list(list|tuple): 对列表（或元组）中的图像同时进行预测，列表中的元素可以是图像路径
                也可以是解码后的排列格式为（H，W，C）且类型为float32且为BGR格式的数组。
            transforms (paddlex.det.transforms): 数据预处理操作。

        Returns:
            list: 每个元素都为列表，表示各图像的预测结果。在各图像的预测结果列表中，每个预测结果由预测框类别标签、
              预测框类别名称、预测框坐标(坐标格式为[xmin, ymin, w, h]）、
              预测框得分组成。
        """
        if transforms is None and not hasattr(self, 'test_transforms'):
            raise Exception("transforms need to be defined, now is None.")

        if not isinstance(img_file_list, (list, tuple)):
            raise Exception("im_file must be list/tuple")

        if transforms is None:
            transforms = self.test_transforms
        input_channel = getattr(self, 'input_channel', 3)
        im, im_resize_info, im_shape = FasterRCNN._preprocess(
            img_file_list,
            transforms,
            self.model_type,
            self.__class__.__name__,
            self.thread_pool,
            input_channel=input_channel)

        with fluid.scope_guard(self.scope):
            result = self.exe.run(self.test_prog,
                                  feed={
                                      'image': im,
                                      'im_info': im_resize_info,
                                      'im_shape': im_shape
                                  },
                                  fetch_list=list(self.test_outputs.values()),
                                  return_numpy=False,
                                  use_program_cache=True)

        res = {
            k: (np.array(v), v.recursive_sequence_lengths())
            for k, v in zip(list(self.test_outputs.keys()), result)
        }
        res['im_id'] = (np.array(
            [[i] for i in range(len(img_file_list))]).astype('int32'), [])
        preds = FasterRCNN._postprocess(res,
                                        len(img_file_list), self.num_classes,
                                        self.labels)

        return preds
