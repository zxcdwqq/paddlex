# Object Detection

## paddlex.det.PPYOLO

```python
paddlex.det.PPYOLO(num_classes=80, backbone='ResNet50_vd_ssld', with_dcn_v2=True, anchors=None, anchor_masks=None, use_coord_conv=True, use_iou_aware=True, use_spp=True, use_drop_block=True, scale_x_y=1.05, ignore_threshold=0.7, label_smooth=False, use_iou_loss=True, use_matrix_nms=True, nms_score_threshold=0.01, nms_topk=1000, nms_keep_topk=100, nms_iou_threshold=0.45, train_random_shapes=[320, 352, 384, 416, 448, 480, 512, 544, 576, 608], input_channel=3)
```

> 构建PPYOLO检测器。**注意在PPYOLO，num_classes不需要包含背景类，如目标包括human、dog两种，则num_classes设为2即可，这里与FasterRCNN/MaskRCNN有差别**

> **参数**
>
> > - **num_classes** (int): 类别数。默认为80。
> > - **backbone** (str): PPYOLO的backbone网络，取值范围为['ResNet50_vd_ssld']。默认为'ResNet50_vd_ssld'。
> > - **with_dcn_v2** (bool): Backbone是否使用DCNv2结构。默认为True。
> > - **anchors** (list|tuple): anchor框的宽度和高度，为None时表示使用默认值
> >                  [[10, 13], [16, 30], [33, 23], [30, 61], [62, 45],
>                   [59, 119], [116, 90], [156, 198], [373, 326]]。
> > - **anchor_masks** (list|tuple): 在计算PPYOLO损失时，使用anchor的mask索引，为None时表示使用默认值
> >                    [[6, 7, 8], [3, 4, 5], [0, 1, 2]]。
> > - **use_coord_conv** (bool): 是否使用CoordConv。默认值为True。
> > - **use_iou_aware** (bool): 是否使用IoU Aware分支。默认值为True。
> > - **use_spp** (bool): 是否使用Spatial Pyramid Pooling结构。默认值为True。
> > - **use_drop_block** (bool): 是否使用Drop Block。默认值为True。
> > - **scale_x_y** (float): 调整中心点位置时的系数因子。默认值为1.05。
> > - **use_iou_loss** (bool): 是否使用IoU loss。默认值为True。
> > - **use_matrix_nms** (bool): 是否使用Matrix NMS。默认值为True。  
> > - **ignore_threshold** (float): 在计算PPYOLO损失时，IoU大于`ignore_threshold`的预测框的置信度被忽略。默认为0.7。
> > - **nms_score_threshold** (float): 检测框的置信度得分阈值，置信度得分低于阈值的框应该被忽略。默认为0.01。
> > - **nms_topk** (int): 进行NMS时，根据置信度保留的最大检测框数。默认为1000。
> > - **nms_keep_topk** (int): 进行NMS后，每个图像要保留的总检测框数。默认为100。
> > - **nms_iou_threshold** (float): 进行NMS时，用于剔除检测框IOU的阈值。默认为0.45。
> > - **label_smooth** (bool): 是否使用label smooth。默认值为False。
> > - **train_random_shapes** (list|tuple): 训练时从列表中随机选择图像大小。默认值为[320, 352, 384, 416, 448, 480, 512, 544, 576, 608]。
> > - **input_channel** (int): 输入图像的通道数量。默认为3。

### train

```python
train(self, num_epochs, train_dataset, train_batch_size=8, eval_dataset=None, save_interval_epochs=20, log_interval_steps=2, save_dir='output', pretrain_weights='IMAGENET', optimizer=None, learning_rate=1.0/8000, warmup_steps=1000, warmup_start_lr=0.0, lr_decay_epochs=[213, 240], lr_decay_gamma=0.1, metric=None, use_vdl=False, sensitivities_file=None, eval_metric_loss=0.05, early_stop=False, early_stop_patience=5, resume_checkpoint=None, use_ema=True, ema_decay=0.9998)
```

> PPYOLO模型的训练接口，函数内置了`piecewise`学习率衰减策略和`momentum`优化器。

> **参数**
>
> > - **num_epochs** (int): 训练迭代轮数。
> > - **train_dataset** (paddlex.datasets): 训练数据读取器。
> > - **train_batch_size** (int): 训练数据batch大小。目前检测仅支持单卡评估，训练数据batch大小与显卡数量之商为验证数据batch大小。默认值为8。
> > - **eval_dataset** (paddlex.datasets): 验证数据读取器。
> > - **save_interval_epochs** (int): 模型保存间隔（单位：迭代轮数）。默认为20。
> > - **log_interval_steps** (int): 训练日志输出间隔（单位：迭代次数）。默认为2。
> > - **save_dir** (str): 模型保存路径。默认值为'output'。
> > - **pretrain_weights** (str): 若指定为路径时，则加载路径下预训练模型；若为字符串'IMAGENET'，则自动下载在ImageNet图片数据上预训练的模型权重；若为字符串'COCO'，则自动下载在COCO数据集上预训练的模型权重；若为None，则不使用预训练模型。默认为'IMAGENET'。
> > - **optimizer** (paddle.fluid.optimizer): 优化器。当该参数为None时，使用默认优化器：fluid.layers.piecewise_decay衰减策略，fluid.optimizer.Momentum优化方法。
> > - **learning_rate** (float): 默认优化器的学习率。默认为1.0/8000。
> > - **warmup_steps** (int):  默认优化器进行warmup过程的步数。默认为1000。
> > - **warmup_start_lr** (int): 默认优化器warmup的起始学习率。默认为0.0。
> > - **lr_decay_epochs** (list): 默认优化器的学习率衰减轮数。默认为[213, 240]。
> > - **lr_decay_gamma** (float): 默认优化器的学习率衰减率。默认为0.1。
> > - **metric** (bool): 训练过程中评估的方式，取值范围为['COCO', 'VOC']。默认值为None。
> > - **use_vdl** (bool): 是否使用VisualDL进行可视化。默认值为False。
> > - **sensitivities_file** (str): 若指定为路径时，则加载路径下敏感度信息进行裁剪；若为字符串'DEFAULT'，则自动下载在PascalVOC数据上获得的敏感度信息进行裁剪；若为None，则不进行裁剪。默认为None。
> > - **eval_metric_loss** (float): 可容忍的精度损失。默认为0.05。
> > - **early_stop** (bool): 是否使用提前终止训练策略。默认值为False。
> > - **early_stop_patience** (int): 当使用提前终止训练策略时，如果验证集精度在`early_stop_patience`个epoch内连续下降或持平，则终止训练。默认值为5。
> > - **resume_checkpoint** (str): 恢复训练时指定上次训练保存的模型路径。若为None，则不会恢复训练。默认值为None。
> > - **use_ema** (bool): 是否使用指数衰减计算参数的滑动平均值。默认值为True。
> > - **ema_decay** (float): 指数衰减率。默认值为0.9998。

### evaluate

```python
evaluate(self, eval_dataset, batch_size=1, epoch_id=None, metric=None, return_details=False)
```

> PPYOLO模型的评估接口，模型评估后会返回在验证集上的指标`box_map`(metric指定为'VOC'时)或`box_mmap`(metric指定为`COCO`时)。

> **参数**
>
> > - **eval_dataset** (paddlex.datasets): 验证数据读取器。
> > - **batch_size** (int): 验证数据批大小。默认为1。
> > - **epoch_id** (int): 当前评估模型所在的训练轮数。
> > - **metric** (bool): 训练过程中评估的方式，取值范围为['COCO', 'VOC']。默认为None，根据用户传入的Dataset自动选择，如为VOCDetection，则`metric`为'VOC'；如为COCODetection，则`metric`为'COCO'默认为None， 如为EasyData类型数据集，同时也会使用'VOC'。
> > - **return_details** (bool): 是否返回详细信息。默认值为False。
> >
>  **返回值**
>
> > - **tuple** (metrics, eval_details) | **dict** (metrics): 当`return_details`为True时，返回(metrics, eval_details)，当`return_details`为False时，返回metrics。metrics为dict，包含关键字：'bbox_mmap'或者’bbox_map‘，分别表示平均准确率平均值在各个阈值下的结果取平均值的结果（mmAP）、平均准确率平均值（mAP）。eval_details为dict，包含bbox和gt两个关键字。其中关键字bbox的键值是一个列表，列表中每个元素代表一个预测结果，一个预测结果是一个由图像id，预测框类别id, 预测框坐标，预测框得分组成的列表。而关键字gt的键值是真实标注框的相关信息。

### predict

```python
predict(self, img_file, transforms=None)
```

> PPYOLO模型预测接口。需要注意的是，只有在训练过程中定义了eval_dataset，模型在保存时才会将预测时的图像处理流程保存在`PPYOLO.test_transforms`和`PPYOLO.eval_transforms`中。如未在训练时定义eval_dataset，那在调用预测`predict`接口时，用户需要再重新定义`test_transforms`传入给`predict`接口

> **参数**
>
> > - **img_file** (str|np.ndarray): 预测图像路径或numpy数组(HWC排列，BGR格式)。
> > - **transforms** (paddlex.det.transforms): 数据预处理操作。
>
> **返回值**
>
> > - **list**: 预测结果列表，列表中每个元素均为一个dict，key包括'bbox', 'category', 'category_id', 'score'，分别表示每个预测目标的框坐标信息、类别、类别id、置信度，其中框坐标信息为[xmin, ymin, w, h]，即左上角x, y坐标和框的宽和高。


### batch_predict

```python
batch_predict(self, img_file_list, transforms=None)
```

> PPYOLO模型批量预测接口。需要注意的是，只有在训练过程中定义了eval_dataset，模型在保存时才会将预测时的图像处理流程保存在`PPYOLO.test_transforms`和`PPYOLO.eval_transforms`中。如未在训练时定义eval_dataset，那在调用预测`batch_predict`接口时，用户需要再重新定义`test_transforms`传入给`batch_predict`接口

> **参数**
>
> > - **img_file_list** (str|np.ndarray): 对列表（或元组）中的图像同时进行预测，列表中的元素是预测图像路径或numpy数组(HWC排列，BGR格式)。
> > - **transforms** (paddlex.det.transforms): 数据预处理操作。
>
> **返回值**
>
> > - **list**: 每个元素都为列表，表示各图像的预测结果。在各图像的预测结果列表中，每个元素均为一个dict，key包括'bbox', 'category', 'category_id', 'score'，分别表示每个预测目标的框坐标信息、类别、类别id、置信度，其中框坐标信息为[xmin, ymin, w, h]，即左上角x, y坐标和框的宽和高。


## paddlex.det.YOLOv3

```python
paddlex.det.YOLOv3(num_classes=80, backbone='MobileNetV1', anchors=None, anchor_masks=None, ignore_threshold=0.7, nms_score_threshold=0.01, nms_topk=1000, nms_keep_topk=100, nms_iou_threshold=0.45, label_smooth=False, train_random_shapes=[320, 352, 384, 416, 448, 480, 512, 544, 576, 608], input_channel=3)
```

> 构建YOLOv3检测器。**注意在YOLOv3，num_classes不需要包含背景类，如目标包括human、dog两种，则num_classes设为2即可，这里与FasterRCNN/MaskRCNN有差别**

> **参数**
>
> > - **num_classes** (int): 类别数。默认为80。
> > - **backbone** (str): YOLOv3的backbone网络，取值范围为['DarkNet53', 'ResNet34', 'MobileNetV1', 'MobileNetV3_large']。默认为'MobileNetV1'。
> > - **anchors** (list|tuple): anchor框的宽度和高度，为None时表示使用默认值
> >                  [[10, 13], [16, 30], [33, 23], [30, 61], [62, 45],
>                   [59, 119], [116, 90], [156, 198], [373, 326]]。
> > - **anchor_masks** (list|tuple): 在计算YOLOv3损失时，使用anchor的mask索引，为None时表示使用默认值
> >                    [[6, 7, 8], [3, 4, 5], [0, 1, 2]]。
> > - **ignore_threshold** (float): 在计算YOLOv3损失时，IoU大于`ignore_threshold`的预测框的置信度被忽略。默认为0.7。
> > - **nms_score_threshold** (float): 检测框的置信度得分阈值，置信度得分低于阈值的框应该被忽略。默认为0.01。
> > - **nms_topk** (int): 进行NMS时，根据置信度保留的最大检测框数。默认为1000。
> > - **nms_keep_topk** (int): 进行NMS后，每个图像要保留的总检测框数。默认为100。
> > - **nms_iou_threshold** (float): 进行NMS时，用于剔除检测框IoU的阈值。默认为0.45。
> > - **label_smooth** (bool): 是否使用label smooth。默认值为False。
> > - **train_random_shapes** (list|tuple): 训练时从列表中随机选择图像大小。默认值为[320, 352, 384, 416, 448, 480, 512, 544, 576, 608]。
> > - **input_channel** (int): 输入图像的通道数量。默认为3。

### train

```python
train(self, num_epochs, train_dataset, train_batch_size=8, eval_dataset=None, save_interval_epochs=20, log_interval_steps=2, save_dir='output', pretrain_weights='IMAGENET', optimizer=None, learning_rate=1.0/8000, warmup_steps=1000, warmup_start_lr=0.0, lr_decay_epochs=[213, 240], lr_decay_gamma=0.1, metric=None, use_vdl=False, sensitivities_file=None, eval_metric_loss=0.05, early_stop=False, early_stop_patience=5, resume_checkpoint=None)
```

> YOLOv3模型的训练接口，函数内置了`piecewise`学习率衰减策略和`momentum`优化器。

> **参数**
>
> > - **num_epochs** (int): 训练迭代轮数。
> > - **train_dataset** (paddlex.datasets): 训练数据读取器。
> > - **train_batch_size** (int): 训练数据batch大小。目前检测仅支持单卡评估，训练数据batch大小与显卡数量之商为验证数据batch大小。默认值为8。
> > - **eval_dataset** (paddlex.datasets): 验证数据读取器。
> > - **save_interval_epochs** (int): 模型保存间隔（单位：迭代轮数）。默认为20。
> > - **log_interval_steps** (int): 训练日志输出间隔（单位：迭代次数）。默认为2。
> > - **save_dir** (str): 模型保存路径。默认值为'output'。
> > - **pretrain_weights** (str): 若指定为路径时，则加载路径下预训练模型；若为字符串'IMAGENET'，则自动下载在ImageNet图片数据上预训练的模型权重；若为字符串'COCO'，则自动下载在COCO数据集上预训练的模型权重；若为None，则不使用预训练模型。默认为'IMAGENET'。
> > - **optimizer** (paddle.fluid.optimizer): 优化器。当该参数为None时，使用默认优化器：fluid.layers.piecewise_decay衰减策略，fluid.optimizer.Momentum优化方法。
> > - **learning_rate** (float): 默认优化器的学习率。默认为1.0/8000。
> > - **warmup_steps** (int):  默认优化器进行warmup过程的步数。默认为1000。
> > - **warmup_start_lr** (int): 默认优化器warmup的起始学习率。默认为0.0。
> > - **lr_decay_epochs** (list): 默认优化器的学习率衰减轮数。默认为[213, 240]。
> > - **lr_decay_gamma** (float): 默认优化器的学习率衰减率。默认为0.1。
> > - **metric** (bool): 训练过程中评估的方式，取值范围为['COCO', 'VOC']。默认值为None。
> > - **use_vdl** (bool): 是否使用VisualDL进行可视化。默认值为False。
> > - **sensitivities_file** (str): 若指定为路径时，则加载路径下敏感度信息进行裁剪；若为字符串'DEFAULT'，则自动下载在PascalVOC数据上获得的敏感度信息进行裁剪；若为None，则不进行裁剪。默认为None。
> > - **eval_metric_loss** (float): 可容忍的精度损失。默认为0.05。
> > - **early_stop** (bool): 是否使用提前终止训练策略。默认值为False。
> > - **early_stop_patience** (int): 当使用提前终止训练策略时，如果验证集精度在`early_stop_patience`个epoch内连续下降或持平，则终止训练。默认值为5。
> > - **resume_checkpoint** (str): 恢复训练时指定上次训练保存的模型路径。若为None，则不会恢复训练。默认值为None。

### evaluate

```python
evaluate(self, eval_dataset, batch_size=1, epoch_id=None, metric=None, return_details=False)
```

> YOLOv3模型的评估接口，模型评估后会返回在验证集上的指标`box_map`(metric指定为'VOC'时)或`box_mmap`(metric指定为`COCO`时)。

> **参数**
>
> > - **eval_dataset** (paddlex.datasets): 验证数据读取器。
> > - **batch_size** (int): 验证数据批大小。默认为1。
> > - **epoch_id** (int): 当前评估模型所在的训练轮数。
> > - **metric** (bool): 训练过程中评估的方式，取值范围为['COCO', 'VOC']。默认为None，根据用户传入的Dataset自动选择，如为VOCDetection，则`metric`为'VOC'；如为COCODetection，则`metric`为'COCO'默认为None， 如为EasyData类型数据集，同时也会使用'VOC'。
> > - **return_details** (bool): 是否返回详细信息。默认值为False。
> >
>  **返回值**
>
> > - **tuple** (metrics, eval_details) | **dict** (metrics): 当`return_details`为True时，返回(metrics, eval_details)，当`return_details`为False时，返回metrics。metrics为dict，包含关键字：'bbox_mmap'或者’bbox_map‘，分别表示平均准确率平均值在各个阈值下的结果取平均值的结果（mmAP）、平均准确率平均值（mAP）。eval_details为dict，包含bbox和gt两个关键字。其中关键字bbox的键值是一个列表，列表中每个元素代表一个预测结果，一个预测结果是一个由图像id，预测框类别id, 预测框坐标，预测框得分组成的列表。而关键字gt的键值是真实标注框的相关信息。

### predict

```python
predict(self, img_file, transforms=None)
```

> YOLOv3模型预测接口。需要注意的是，只有在训练过程中定义了eval_dataset，模型在保存时才会将预测时的图像处理流程保存在`YOLOv3.test_transforms`和`YOLOv3.eval_transforms`中。如未在训练时定义eval_dataset，那在调用预测`predict`接口时，用户需要再重新定义`test_transforms`传入给`predict`接口

> **参数**
>
> > - **img_file** (str|np.ndarray): 预测图像路径或numpy数组(HWC排列，BGR格式)。
> > - **transforms** (paddlex.det.transforms): 数据预处理操作。
>
> **返回值**
>
> > - **list**: 预测结果列表，列表中每个元素均为一个dict，key包括'bbox', 'category', 'category_id', 'score'，分别表示每个预测目标的框坐标信息、类别、类别id、置信度，其中框坐标信息为[xmin, ymin, w, h]，即左上角x, y坐标和框的宽和高。


### batch_predict

```python
batch_predict(self, img_file_list, transforms=None)
```

> YOLOv3模型批量预测接口。需要注意的是，只有在训练过程中定义了eval_dataset，模型在保存时才会将预测时的图像处理流程保存在`YOLOv3.test_transforms`和`YOLOv3.eval_transforms`中。如未在训练时定义eval_dataset，那在调用预测`batch_predict`接口时，用户需要再重新定义`test_transforms`传入给`batch_predict`接口

> **参数**
>
> > - **img_file_list** (str|np.ndarray): 对列表（或元组）中的图像同时进行预测，列表中的元素是预测图像路径或numpy数组(HWC排列，BGR格式)。
> > - **transforms** (paddlex.det.transforms): 数据预处理操作。
>
> **返回值**
>
> > - **list**: 每个元素都为列表，表示各图像的预测结果。在各图像的预测结果列表中，每个元素均为一个dict，key包括'bbox', 'category', 'category_id', 'score'，分别表示每个预测目标的框坐标信息、类别、类别id、置信度，其中框坐标信息为[xmin, ymin, w, h]，即左上角x, y坐标和框的宽和高。



## paddlex.det.FasterRCNN

```python
paddlex.det.FasterRCNN(num_classes=81, backbone='ResNet50', with_fpn=True, aspect_ratios=[0.5, 1.0, 2.0], anchor_sizes=[32, 64, 128, 256, 512], with_dcn=False, rpn_cls_loss='SigmoidCrossEntropy', rpn_focal_loss_alpha=0.25, rpn_focal_loss_gamma=2, rcnn_bbox_loss='SmoothL1Loss', rcnn_nms='MultiClassNMS', keep_top_k=100, nms_threshold=0.5, score_threshold=0.05, softnms_sigma=0.5, bbox_assigner='BBoxAssigner', fpn_num_channels=256, input_channel=3, rpn_batch_size_per_im=256, rpn_fg_fraction=0.5, test_pre_nms_top_n=None, test_post_nms_top_n=1000)
```

> 构建FasterRCNN检测器。 **注意在FasterRCNN中，num_classes需要设置为类别数+背景类，如目标包括human、dog两种，则num_classes需设为3，多的一种为背景background类别**

> **参数**

> > - **num_classes** (int): 包含了背景类的类别数。默认为81。
> > - **backbone** (str): FasterRCNN的backbone网络，取值范围为['ResNet18', 'ResNet50', 'ResNet50_vd', 'ResNet101', 'ResNet101_vd', 'HRNet_W18', 'ResNet50_vd_ssld']。默认为'ResNet50'。
> > - **with_fpn** (bool): 是否使用FPN结构。默认为True。
> > - **aspect_ratios** (list): 生成anchor高宽比的可选值。默认为[0.5, 1.0, 2.0]。
> > - **anchor_sizes** (list): 生成anchor大小的可选值。默认为[32, 64, 128, 256, 512]。
> > - **with_dcn** (bool): backbone网络中是否使用deformable convolution network v2。默认为False。
> > - **rpn_cls_loss** (str): RPN部分的分类损失函数，取值范围为['SigmoidCrossEntropy', 'SigmoidFocalLoss']。当遇到模型误检了很多背景区域时，可以考虑使用'SigmoidFocalLoss'，并调整适合的`rpn_focal_loss_alpha`和`rpn_focal_loss_gamma`。默认为'SigmoidCrossEntropy'。
> > - **rpn_focal_loss_alpha** (float)：当RPN的分类损失函数设置为'SigmoidFocalLoss'时，用于调整正样本和负样本的比例因子，默认为0.25。当PN的分类损失函数设置为'SigmoidCrossEntropy'时，`rpn_focal_loss_alpha`的设置不生效。
> > - **rpn_focal_loss_gamma** (float): 当RPN的分类损失函数设置为'SigmoidFocalLoss'时，用于调整易分样本和难分样本的比例因子，默认为2。当RPN的分类损失函数设置为'SigmoidCrossEntropy'时，`rpn_focal_loss_gamma`的设置不生效。
> > - **rcnn_bbox_loss** (str): RCNN部分的位置回归损失函数，取值范围为['SmoothL1Loss', 'CIoULoss']。默认为'SmoothL1Loss'。
> > - **rcnn_nms** (str): RCNN部分的非极大值抑制的计算方法，取值范围为['MultiClassNMS', 'MultiClassSoftNMS','MultiClassCiouNMS']。默认为'MultiClassNMS'。当选择'MultiClassNMS'时，可以将`keep_top_k`设置成100、`nms_threshold`设置成0.5、`score_threshold`设置成0.05。当选择'MultiClassSoftNMS'时，可以将`keep_top_k`设置为300、`score_threshold`设置为0.01、`softnms_sigma`设置为0.5。当选择'MultiClassCiouNMS'时，可以将`keep_top_k`设置为100、`score_threshold`设置成0.05、`nms_threshold`设置成0.5。
> > - **keep_top_k** (int): RCNN部分在进行非极大值抑制计算后，每张图像保留最多保存`keep_top_k`个检测框。默认为100。
> > - **nms_threshold** (float): RCNN部分在进行非极大值抑制时，用于剔除检测框所需的IoU阈值。当`rcnn_nms`设置为`MultiClassSoftNMS`时，`nms_threshold`的设置不生效。默认为0.5。
> > - **score_threshold** (float): RCNN部分在进行非极大值抑制前，用于过滤掉低置信度边界框所需的置信度阈值。默认为0.05。
> > - **softnms_sigma** (float): 当`rcnn_nms`设置为`MultiClassSoftNMS`时，用于调整被抑制的检测框的置信度，调整公式为`score = score * weights, weights = exp(-(iou * iou) / softnms_sigma)`。默认设为0.5。
> > - **bbox_assigner** (str): 训练阶段，RCNN部分生成正负样本的采样方式。可选范围为['BBoxAssigner', 'LibraBBoxAssigner']。当目标物体的区域只占原始图像的一小部分时，可以考虑采用[LibraRCNN](https://arxiv.org/abs/1904.02701)中提出的IoU-balanced Sampling采样方式来获取更多的难分负样本，设置为'LibraBBoxAssigner'即可。默认为'BBoxAssigner'。
> > - **fpn_num_channels** (int): FPN部分特征层的通道数量。默认为256。
> > - **input_channel** (int): 输入图像的通道数量。默认为3。
> > - **rpn_batch_size_per_im** (int): 训练阶段，RPN部分每张图片的正负样本的数量总和。默认为256。
> > - **rpn_fg_fraction** (float): 训练阶段，RPN部分每张图片的正负样本数量总和中正样本的占比。默认为0.5。
> > - **test_pre_nms_top_n** (int)：预测阶段，RPN部分做非极大值抑制计算的候选框的数量。若设置为None, 有FPN结构的话，`test_pre_nms_top_n`会被设置成6000, 无FPN结构的话，`test_pre_nms_top_n`会被设置成1000。默认为None。
> > - **test_post_nms_top_n** (int): 预测阶段，RPN部分做完非极大值抑制后保留的候选框的数量。默认为1000。

### train

```python
train(self, num_epochs, train_dataset, train_batch_size=2, eval_dataset=None, save_interval_epochs=1, log_interval_steps=2,save_dir='output', pretrain_weights='IMAGENET', optimizer=None, learning_rate=0.0025, warmup_steps=500, warmup_start_lr=1.0/1200, lr_decay_epochs=[8, 11], lr_decay_gamma=0.1, metric=None, use_vdl=False, early_stop=False, early_stop_patience=5, resume_checkpoint=None)
```

> FasterRCNN模型的训练接口，函数内置了`piecewise`学习率衰减策略和`momentum`优化器。

> **参数**
>
> > - **num_epochs** (int): 训练迭代轮数。
> > - **train_dataset** (paddlex.datasets): 训练数据读取器。
> > - **train_batch_size** (int): 训练数据batch大小。目前检测仅支持单卡评估，训练数据batch大小与显卡数量之商为验证数据batch大小。默认为2。
> > - **eval_dataset** (paddlex.datasets): 验证数据读取器。
> > - **save_interval_epochs** (int): 模型保存间隔（单位：迭代轮数）。默认为1。
> > - **log_interval_steps** (int): 训练日志输出间隔（单位：迭代次数）。默认为2。
> > - **save_dir** (str): 模型保存路径。默认值为'output'。
> > - **pretrain_weights** (str): 若指定为路径时，则加载路径下预训练模型；若为字符串'IMAGENET'，则自动下载在ImageNet图片数据上预训练的模型权重；若为字符串'COCO'，则自动下载在COCO数据集上预训练的模型权重（注意：暂未提供ResNet18的COCO预训练模型）；为None，则不使用预训练模型。默认为'IMAGENET'。
> > - **optimizer** (paddle.fluid.optimizer): 优化器。当该参数为None时，使用默认优化器：fluid.layers.piecewise_decay衰减策略，fluid.optimizer.Momentum优化方法。
> > - **learning_rate** (float): 默认优化器的初始学习率。默认为0.0025。
> > - **warmup_steps** (int):  默认优化器进行warmup过程的步数。默认为500。
> > - **warmup_start_lr** (int): 默认优化器warmup的起始学习率。默认为1.0/1200。
> > - **lr_decay_epochs** (list): 默认优化器的学习率衰减轮数。默认为[8, 11]。
> > - **lr_decay_gamma** (float): 默认优化器的学习率衰减率。默认为0.1。
> > - **metric** (bool): 训练过程中评估的方式，取值范围为['COCO', 'VOC']。默认值为None。
> > - **use_vdl** (bool): 是否使用VisualDL进行可视化。默认值为False。
> > - **early_stop** (float): 是否使用提前终止训练策略。默认值为False。
> > - **early_stop_patience** (int): 当使用提前终止训练策略时，如果验证集精度在`early_stop_patience`个epoch内连续下降或持平，则终止训练。默认值为5。
> > - **resume_checkpoint** (str): 恢复训练时指定上次训练保存的模型路径。若为None，则不会恢复训练。默认值为None。

### evaluate

```python
evaluate(self, eval_dataset, batch_size=1, epoch_id=None, metric=None, return_details=False)
```

> FasterRCNN模型的评估接口，模型评估后会返回在验证集上的指标box_map(metric指定为’VOC’时)或box_mmap(metric指定为COCO时)。

> **参数**
>
> > - **eval_dataset** (paddlex.datasets): 验证数据读取器。
> > - **batch_size** (int): 验证数据批大小。默认为1。当前只支持设置为1。
> > - **epoch_id** (int): 当前评估模型所在的训练轮数。
> > - **metric** (bool): 训练过程中评估的方式，取值范围为['COCO', 'VOC']。默认为None，根据用户传入的Dataset自动选择，如为VOCDetection，则`metric`为'VOC'; 如为COCODetection，则`metric`为'COCO'。
> > - **return_details** (bool): 是否返回详细信息。默认值为False。
> >
> **返回值**
>
> > - **tuple** (metrics, eval_details) | **dict** (metrics): 当`return_details`为True时，返回(metrics, eval_details)，当`return_details`为False时，返回metrics。metrics为dict，包含关键字：'bbox_mmap'或者’bbox_map‘，分别表示平均准确率平均值在各个IoU阈值下的结果取平均值的结果（mmAP）、平均准确率平均值（mAP）。eval_details为dict，包含bbox和gt两个关键字。其中关键字bbox的键值是一个列表，列表中每个元素代表一个预测结果，一个预测结果是一个由图像id，预测框类别id, 预测框坐标，预测框得分组成的列表。而关键字gt的键值是真实标注框的相关信息。

### predict

```python
predict(self, img_file, transforms=None)
```

> FasterRCNN模型预测接口。需要注意的是，只有在训练过程中定义了eval_dataset，模型在保存时才会将预测时的图像处理流程保存在`FasterRCNN.test_transforms`和`FasterRCNN.eval_transforms`中。如未在训练时定义eval_dataset，那在调用预测`predict`接口时，用户需要再重新定义test_transforms传入给`predict`接口。

> **参数**
>
> > - **img_file** (str|np.ndarray): 预测图像路径或numpy数组(HWC排列，BGR格式)。
> > - **transforms** (paddlex.det.transforms): 数据预处理操作。
>
> **返回值**
>
> > - **list**: 预测结果列表，列表中每个元素均为一个dict，key包括'bbox', 'category', 'category_id', 'score'，分别表示每个预测目标的框坐标信息、类别、类别id、置信度，其中框坐标信息为[xmin, ymin, w, h]，即左上角x, y坐标和框的宽和高。


### batch_predict

```python
batch_predict(self, img_file_list, transforms=None)
```

> FasterRCNN模型批量预测接口。需要注意的是，只有在训练过程中定义了eval_dataset，模型在保存时才会将预测时的图像处理流程保存在`FasterRCNN.test_transforms`和`FasterRCNN.eval_transforms`中。如未在训练时定义eval_dataset，那在调用预测`batch_predict`接口时，用户需要再重新定义test_transforms传入给`batch_predict`接口。

> **参数**
>
> > - **img_file_list** (list|tuple): 对列表（或元组）中的图像同时进行预测，列表中的元素是预测图像路径或numpy数组(HWC排列，BGR格式)。
> > - **transforms** (paddlex.det.transforms): 数据预处理操作。
>
> **返回值**
>
> > - **list**: 每个元素都为列表，表示各图像的预测结果。在各图像的预测结果列表中，每个元素均为一个dict，key包括'bbox', 'category', 'category_id', 'score'，分别表示每个预测目标的框坐标信息、类别、类别id、置信度，其中框坐标信息为[xmin, ymin, w, h]，即左上角x, y坐标和框的宽和高。
