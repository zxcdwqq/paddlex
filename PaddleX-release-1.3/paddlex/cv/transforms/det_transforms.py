# copyright (c) 2020 PaddlePaddle Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

try:
    from collections.abc import Sequence
except Exception:
    from collections import Sequence

import random
import os.path as osp
import numpy as np

import cv2

from .imgaug_support import execute_imgaug
from .ops import *
from .box_utils import *
import paddlex.utils.logging as logging


class DetTransform:
    """检测数据处理基类
    """

    def __init__(self):
        pass


class Compose(DetTransform):
    """根据数据预处理/增强列表对输入数据进行操作。
       所有操作的输入图像流形状均是[H, W, C]，其中H为图像高，W为图像宽，C为图像通道数。
    Args:
        transforms (list): 数据预处理/增强列表。
    Raises:
        TypeError: 形参数据类型不满足需求。
        ValueError: 数据长度不匹配。
    """

    def __init__(self, transforms):
        if not isinstance(transforms, list):
            raise TypeError('The transforms must be a list!')
        if len(transforms) < 1:
            raise ValueError('The length of transforms ' + \
                            'must be equal or larger than 1!')
        self.transforms = transforms
        self.batch_transforms = None
        self.use_mixup = False
        self.data_type = np.uint8
        self.to_rgb = True
        for t in self.transforms:
            if type(t).__name__ == 'MixupImage':
                self.use_mixup = True
        # 检查transforms里面的操作，目前支持PaddleX定义的或者是imgaug操作
        for op in self.transforms:
            if not isinstance(op, DetTransform):
                import imgaug.augmenters as iaa
                if not isinstance(op, iaa.Augmenter):
                    raise Exception(
                        "Elements in transforms should be defined in 'paddlex.det.transforms' or class of imgaug.augmenters.Augmenter, see docs here: https://paddlex.readthedocs.io/zh_CN/latest/apis/transforms/"
                    )

    def __call__(self, im, im_info=None, label_info=None):
        """
        Args:
            im (str/np.ndarray): 图像路径/图像np.ndarray数据。
            im_info (dict): 存储与图像相关的信息，dict中的字段如下：
                - im_id (np.ndarray): 图像序列号，形状为(1,)。
                - image_shape (np.ndarray): 图像原始大小，形状为(2,)，
                                        image_shape[0]为高，image_shape[1]为宽。
                - mixup (list): list为[im, im_info, label_info]，分别对应
                                与当前图像进行mixup的图像np.ndarray数据、图像相关信息、标注框相关信息；
                                注意，当前epoch若无需进行mixup，则无该字段。
            label_info (dict): 存储与标注框相关的信息，dict中的字段如下：
                - gt_bbox (np.ndarray): 真实标注框坐标[x1, y1, x2, y2]，形状为(n, 4)，
                                   其中n代表真实标注框的个数。
                - gt_class (np.ndarray): 每个真实标注框对应的类别序号，形状为(n, 1)，
                                    其中n代表真实标注框的个数。
                - gt_score (np.ndarray): 每个真实标注框对应的混合得分，形状为(n, 1)，
                                    其中n代表真实标注框的个数。
                - gt_poly (list): 每个真实标注框内的多边形分割区域，每个分割区域由点的x、y坐标组成，
                                  长度为n，其中n代表真实标注框的个数。
                - is_crowd (np.ndarray): 每个真实标注框中是否是一组对象，形状为(n, 1)，
                                    其中n代表真实标注框的个数。
                - difficult (np.ndarray): 每个真实标注框中的对象是否为难识别对象，形状为(n, 1)，
                                     其中n代表真实标注框的个数。
        Returns:
            tuple: 根据网络所需字段所组成的tuple；
                字段由transforms中的最后一个数据预处理操作决定。
        """

        def decode_image(im_file, im_info, label_info, input_channel=3):
            if im_info is None:
                im_info = dict()
            if isinstance(im_file, np.ndarray):
                if len(im_file.shape) != 3:
                    raise Exception(
                        "im should be 3-dimensions, but now is {}-dimensions".
                        format(len(im_file.shape)))
                im = im_file
            else:
                try:
                    if input_channel == 3:
                        im = cv2.imread(im_file, cv2.IMREAD_ANYDEPTH |
                                        cv2.IMREAD_ANYCOLOR | cv2.IMREAD_COLOR)
                    else:
                        im = cv2.imread(im_file, cv2.IMREAD_ANYDEPTH |
                                        cv2.IMREAD_ANYCOLOR)
                        if im.ndim < 3:
                            im = np.expand_dims(im, axis=-1)
                except:
                    raise TypeError('Can\'t read The image file {}!'.format(
                        im_file))
            self.data_type = im.dtype
            im = im.astype('float32')
            if input_channel == 3 and self.to_rgb:
                im = cv2.cvtColor(im, cv2.COLOR_BGR2RGB)
            # make default im_info with [h, w, 1]
            im_info['im_resize_info'] = np.array(
                [im.shape[0], im.shape[1], 1.], dtype=np.float32)
            im_info['image_shape'] = np.array([im.shape[0],
                                               im.shape[1]]).astype('int32')
            if not self.use_mixup:
                if 'mixup' in im_info:
                    del im_info['mixup']
            # decode mixup image
            if 'mixup' in im_info:
                im_info['mixup'] = \
                  decode_image(im_info['mixup'][0],
                               im_info['mixup'][1],
                               im_info['mixup'][2],
                               input_channel)
            if label_info is None:
                return (im, im_info)
            else:
                return (im, im_info, label_info)

        input_channel = getattr(self, 'input_channel', 3)
        outputs = decode_image(im, im_info, label_info, input_channel)
        im = outputs[0]
        im_info = outputs[1]
        if len(outputs) == 3:
            label_info = outputs[2]
        for op in self.transforms:
            if im is None:
                return None
            if isinstance(op, DetTransform):
                if op.__class__.__name__ == 'RandomDistort':
                    op.to_rgb = self.to_rgb
                    op.data_type = self.data_type
                outputs = op(im, im_info, label_info)
                im = outputs[0]
            else:
                import imgaug.augmenters as iaa
                if im.shape[-1] != 3:
                    raise Exception(
                        "Only the 3-channel RGB image is supported in the imgaug operator, but recieved image channel is {}".
                        format(im.shape[-1]))
                if isinstance(op, iaa.Augmenter):
                    im = execute_imgaug(op, im)
                if label_info is not None:
                    outputs = (im, im_info, label_info)
                else:
                    outputs = (im, im_info)
        return outputs

    def add_augmenters(self, augmenters):
        if not isinstance(augmenters, list):
            raise Exception(
                "augmenters should be list type in func add_augmenters()")
        transform_names = [type(x).__name__ for x in self.transforms]
        for aug in augmenters:
            if type(aug).__name__ in transform_names:
                logging.error(
                    "{} is already in ComposedTransforms, need to remove it from add_augmenters().".
                    format(type(aug).__name__))
        self.transforms = augmenters + self.transforms


class ResizeByShort(DetTransform):
    """根据图像的短边调整图像大小（resize）。

    1. 获取图像的长边和短边长度。
    2. 根据短边与short_size的比例，计算长边的目标长度，
       此时高、宽的resize比例为short_size/原图短边长度。
       若short_size为数组，则随机从该数组中挑选一个数值
       作为short_size。
    3. 如果max_size>0，调整resize比例：
       如果长边的目标长度>max_size，则高、宽的resize比例为max_size/原图长边长度。
    4. 根据调整大小的比例对图像进行resize。

    Args:
        short_size (int|list): 短边目标长度。默认为800。
        max_size (int): 长边目标长度的最大限制。默认为1333。

     Raises:
        TypeError: 形参数据类型不满足需求。
    """

    def __init__(self, short_size=800, max_size=1333):
        self.max_size = int(max_size)
        if not (isinstance(short_size, int) or isinstance(short_size, list)):
            raise TypeError(
                "Type of short_size is invalid. Must be Integer or List, now is {}".
                format(type(short_size)))
        self.short_size = short_size
        if not (isinstance(self.max_size, int)):
            raise TypeError("max_size: input type is invalid.")

    def __call__(self, im, im_info=None, label_info=None):
        """
        Args:
            im (numnp.ndarraypy): 图像np.ndarray数据。
            im_info (dict, 可选): 存储与图像相关的信息。
            label_info (dict, 可选): 存储与标注框相关的信息。

        Returns:
            tuple: 当label_info为空时，返回的tuple为(im, im_info)，分别对应图像np.ndarray数据、存储与图像相关信息的字典；
                   当label_info不为空时，返回的tuple为(im, im_info, label_info)，分别对应图像np.ndarray数据、
                   存储与标注框相关信息的字典。
                   其中，im_info更新字段为：
                       - im_resize_info (np.ndarray): resize后的图像高、resize后的图像宽、resize后的图像相对原始图的缩放比例
                                                 三者组成的np.ndarray，形状为(3,)。

        Raises:
            TypeError: 形参数据类型不满足需求。
            ValueError: 数据长度不匹配。
        """
        if im_info is None:
            im_info = dict()
        if not isinstance(im, np.ndarray):
            raise TypeError("ResizeByShort: image type is not numpy.")
        if len(im.shape) != 3:
            raise ValueError('ResizeByShort: image is not 3-dimensional.')
        im_short_size = min(im.shape[0], im.shape[1])
        im_long_size = max(im.shape[0], im.shape[1])
        if isinstance(self.short_size, list):
            # Case for multi-scale training
            selected_size = random.choice(self.short_size)
        else:
            selected_size = self.short_size
        scale = float(selected_size) / im_short_size
        if self.max_size > 0 and np.round(scale *
                                          im_long_size) > self.max_size:
            scale = float(self.max_size) / float(im_long_size)
        resized_width = int(round(im.shape[1] * scale))
        resized_height = int(round(im.shape[0] * scale))
        im_resize_info = [resized_height, resized_width, scale]
        im = cv2.resize(
            im, (resized_width, resized_height),
            interpolation=cv2.INTER_LINEAR)
        if im.ndim < 3:
            im = np.expand_dims(im, axis=-1)
        im_info['im_resize_info'] = np.array(im_resize_info).astype(np.float32)
        if label_info is None:
            return (im, im_info)
        else:
            return (im, im_info, label_info)


class Padding(DetTransform):
    """1.将图像的长和宽padding至coarsest_stride的倍数。如输入图像为[300, 640],
       `coarsest_stride`为32，则由于300不为32的倍数，因此在图像最右和最下使用0值
       进行padding，最终输出图像为[320, 640]。
       2.或者，将图像的长和宽padding到target_size指定的shape，如输入的图像为[300，640]，
         a. `target_size` = 960，在图像最右和最下使用0值进行padding，最终输出
            图像为[960, 960]。
         b. `target_size` = [640, 960]，在图像最右和最下使用0值进行padding，最终
            输出图像为[640, 960]。

    1. 如果coarsest_stride为1，target_size为None则直接返回。
    2. 获取图像的高H、宽W。
    3. 计算填充后图像的高H_new、宽W_new。
    4. 构建大小为(H_new, W_new, 3)像素值为0的np.ndarray，
       并将原图的np.ndarray粘贴于左上角。

    Args:
        coarsest_stride (int): 填充后的图像长、宽为该参数的倍数，默认为1。
        target_size (int|list|tuple): 填充后的图像长、宽，默认为None，coarsest_stride优先级更高。

    Raises:
        TypeError: 形参`target_size`数据类型不满足需求。
        ValueError: 形参`target_size`为(list|tuple)时，长度不满足需求。
    """

    def __init__(self, coarsest_stride=1, target_size=None):
        self.coarsest_stride = coarsest_stride
        if target_size is not None:
            if not isinstance(target_size, int):
                if not isinstance(target_size, tuple) and not isinstance(
                        target_size, list):
                    raise TypeError(
                        "Padding: Type of target_size must in (int|list|tuple)."
                    )
                elif len(target_size) != 2:
                    raise ValueError(
                        "Padding: Length of target_size must equal 2.")
        self.target_size = target_size

    def __call__(self, im, im_info=None, label_info=None):
        """
        Args:
            im (numnp.ndarraypy): 图像np.ndarray数据。
            im_info (dict, 可选): 存储与图像相关的信息。
            label_info (dict, 可选): 存储与标注框相关的信息。

        Returns:
            tuple: 当label_info为空时，返回的tuple为(im, im_info)，分别对应图像np.ndarray数据、存储与图像相关信息的字典；
                   当label_info不为空时，返回的tuple为(im, im_info, label_info)，分别对应图像np.ndarray数据、
                   存储与标注框相关信息的字典。

        Raises:
            TypeError: 形参数据类型不满足需求。
            ValueError: 数据长度不匹配。
            ValueError: coarsest_stride，target_size需有且只有一个被指定。
            ValueError: target_size小于原图的大小。
        """
        if im_info is None:
            im_info = dict()
        if not isinstance(im, np.ndarray):
            raise TypeError("Padding: image type is not numpy.")
        if len(im.shape) != 3:
            raise ValueError('Padding: image is not 3-dimensional.')
        im_h, im_w, im_c = im.shape[:]

        if isinstance(self.target_size, int):
            padding_im_h = self.target_size
            padding_im_w = self.target_size
        elif isinstance(self.target_size, list) or isinstance(self.target_size,
                                                              tuple):
            padding_im_w = self.target_size[0]
            padding_im_h = self.target_size[1]
        elif self.coarsest_stride > 0:
            padding_im_h = int(
                np.ceil(im_h / self.coarsest_stride) * self.coarsest_stride)
            padding_im_w = int(
                np.ceil(im_w / self.coarsest_stride) * self.coarsest_stride)
        else:
            raise ValueError(
                "coarsest_stridei(>1) or target_size(list|int) need setting in Padding transform"
            )
        pad_height = padding_im_h - im_h
        pad_width = padding_im_w - im_w
        if pad_height < 0 or pad_width < 0:
            raise ValueError(
                'the size of image should be less than target_size, but the size of image ({}, {}), is larger than target_size ({}, {})'
                .format(im_w, im_h, padding_im_w, padding_im_h))
        padding_im = np.zeros(
            (padding_im_h, padding_im_w, im_c), dtype=np.float32)
        padding_im[:im_h, :im_w, :] = im
        if label_info is None:
            return (padding_im, im_info)
        else:
            return (padding_im, im_info, label_info)


class Resize(DetTransform):
    """调整图像大小（resize）。

    - 当目标大小（target_size）类型为int时，根据插值方式，
      将图像resize为[target_size, target_size]。
    - 当目标大小（target_size）类型为list或tuple时，根据插值方式，
      将图像resize为target_size。
    注意：当插值方式为“RANDOM”时，则随机选取一种插值方式进行resize。

    Args:
        target_size (int/list/tuple): 短边目标长度。默认为608。
        interp (str): resize的插值方式，与opencv的插值方式对应，取值范围为
            ['NEAREST', 'LINEAR', 'CUBIC', 'AREA', 'LANCZOS4', 'RANDOM']。默认为"LINEAR"。

    Raises:
        TypeError: 形参数据类型不满足需求。
        ValueError: 插值方式不在['NEAREST', 'LINEAR', 'CUBIC',
                    'AREA', 'LANCZOS4', 'RANDOM']中。
    """

    # The interpolation mode
    interp_dict = {
        'NEAREST': cv2.INTER_NEAREST,
        'LINEAR': cv2.INTER_LINEAR,
        'CUBIC': cv2.INTER_CUBIC,
        'AREA': cv2.INTER_AREA,
        'LANCZOS4': cv2.INTER_LANCZOS4
    }

    def __init__(self, target_size=608, interp='LINEAR'):
        self.interp = interp
        if not (interp == "RANDOM" or interp in self.interp_dict):
            raise ValueError("interp should be one of {}".format(
                self.interp_dict.keys()))
        if isinstance(target_size, list) or isinstance(target_size, tuple):
            if len(target_size) != 2:
                raise TypeError(
                    'when target is list or tuple, it should include 2 elements, but it is {}'
                    .format(target_size))
        elif not isinstance(target_size, int):
            raise TypeError(
                "Type of target_size is invalid. Must be Integer or List or tuple, now is {}"
                .format(type(target_size)))

        self.target_size = target_size

    def __call__(self, im, im_info=None, label_info=None):
        """
        Args:
            im (np.ndarray): 图像np.ndarray数据。
            im_info (dict, 可选): 存储与图像相关的信息。
            label_info (dict, 可选): 存储与标注框相关的信息。

        Returns:
            tuple: 当label_info为空时，返回的tuple为(im, im_info)，分别对应图像np.ndarray数据、存储与图像相关信息的字典；
                   当label_info不为空时，返回的tuple为(im, im_info, label_info)，分别对应图像np.ndarray数据、
                   存储与标注框相关信息的字典。

        Raises:
            TypeError: 形参数据类型不满足需求。
            ValueError: 数据长度不匹配。
        """
        if im_info is None:
            im_info = dict()
        if not isinstance(im, np.ndarray):
            raise TypeError("Resize: image type is not numpy.")
        if len(im.shape) != 3:
            raise ValueError('Resize: image is not 3-dimensional.')
        if self.interp == "RANDOM":
            interp = random.choice(list(self.interp_dict.keys()))
        else:
            interp = self.interp
        im = resize(im, self.target_size, self.interp_dict[interp])
        if label_info is None:
            return (im, im_info)
        else:
            return (im, im_info, label_info)


class RandomHorizontalFlip(DetTransform):
    """随机翻转图像、标注框、分割信息，模型训练时的数据增强操作。

    1. 随机采样一个0-1之间的小数，当小数小于水平翻转概率时，
       执行2-4步操作，否则直接返回。
    2. 水平翻转图像。
    3. 计算翻转后的真实标注框的坐标，更新label_info中的gt_bbox信息。
    4. 计算翻转后的真实分割区域的坐标，更新label_info中的gt_poly信息。

    Args:
        prob (float): 随机水平翻转的概率。默认为0.5。

    Raises:
        TypeError: 形参数据类型不满足需求。
    """

    def __init__(self, prob=0.5):
        self.prob = prob
        if not isinstance(self.prob, float):
            raise TypeError("RandomHorizontalFlip: input type is invalid.")

    def __call__(self, im, im_info=None, label_info=None):
        """
        Args:
            im (np.ndarray): 图像np.ndarray数据。
            im_info (dict, 可选): 存储与图像相关的信息。
            label_info (dict, 可选): 存储与标注框相关的信息。

        Returns:
            tuple: 当label_info为空时，返回的tuple为(im, im_info)，分别对应图像np.ndarray数据、存储与图像相关信息的字典；
                   当label_info不为空时，返回的tuple为(im, im_info, label_info)，分别对应图像np.ndarray数据、
                   存储与标注框相关信息的字典。
                   其中，im_info更新字段为：
                       - gt_bbox (np.ndarray): 水平翻转后的标注框坐标[x1, y1, x2, y2]，形状为(n, 4)，
                                          其中n代表真实标注框的个数。
                       - gt_poly (list): 水平翻转后的多边形分割区域的x、y坐标，长度为n，
                                         其中n代表真实标注框的个数。

        Raises:
            TypeError: 形参数据类型不满足需求。
            ValueError: 数据长度不匹配。
        """
        if not isinstance(im, np.ndarray):
            raise TypeError(
                "RandomHorizontalFlip: image is not a numpy array.")
        if len(im.shape) != 3:
            raise ValueError(
                "RandomHorizontalFlip: image is not 3-dimensional.")
        if im_info is None or label_info is None:
            raise TypeError(
                'Cannot do RandomHorizontalFlip! ' +
                'Becasuse the im_info and label_info can not be None!')
        if 'gt_bbox' not in label_info:
            raise TypeError('Cannot do RandomHorizontalFlip! ' + \
                            'Becasuse gt_bbox is not in label_info!')
        image_shape = im_info['image_shape']
        gt_bbox = label_info['gt_bbox']
        height = image_shape[0]
        width = image_shape[1]

        if np.random.uniform(0, 1) < self.prob:
            im = horizontal_flip(im)
            if gt_bbox.shape[0] == 0:
                if label_info is None:
                    return (im, im_info)
                else:
                    return (im, im_info, label_info)
            label_info['gt_bbox'] = box_horizontal_flip(gt_bbox, width)
            if 'gt_poly' in label_info and \
                    len(label_info['gt_poly']) != 0:
                label_info['gt_poly'] = segms_horizontal_flip(
                    label_info['gt_poly'], height, width)
        if label_info is None:
            return (im, im_info)
        else:
            return (im, im_info, label_info)


class Normalize(DetTransform):
    """对图像进行标准化。

    1.像素值减去min_val
    2.像素值除以(max_val-min_val)
    3.对图像进行减均值除以标准差操作。

    Args:
        mean (list): 图像数据集的均值。默认值[0.5, 0.5, 0.5]。
        std (list): 图像数据集的标准差。默认值[0.5, 0.5, 0.5]。
        min_val (list): 图像数据集的最小值。默认值[0, 0, 0]。
        max_val (list): 图像数据集的最大值。默认值[255.0, 255.0, 255.0]。

    Raises:
        TypeError: 形参数据类型不满足需求。
    """

    def __init__(self,
                 mean=[0.485, 0.456, 0.406],
                 std=[0.229, 0.224, 0.225],
                 min_val=[0, 0, 0],
                 max_val=[255.0, 255.0, 255.0]):
        self.mean = mean
        self.std = std
        self.min_val = min_val
        self.max_val = max_val

        if not (isinstance(self.mean, list) and isinstance(self.std, list)):
            raise TypeError("NormalizeImage: input type is invalid.")

        if not (isinstance(self.min_val, list) and isinstance(self.max_val,
                                                              list)):
            raise ValueError("{}: input type is invalid.".format(self))

        from functools import reduce
        if reduce(lambda x, y: x * y, self.std) == 0:
            raise TypeError('NormalizeImage: std is invalid!')

    def __call__(self, im, im_info=None, label_info=None):
        """
        Args:
            im (numnp.ndarraypy): 图像np.ndarray数据。
            im_info (dict, 可选): 存储与图像相关的信息。
            label_info (dict, 可选): 存储与标注框相关的信息。

        Returns:
            tuple: 当label_info为空时，返回的tuple为(im, im_info)，分别对应图像np.ndarray数据、存储与图像相关信息的字典；
                   当label_info不为空时，返回的tuple为(im, im_info, label_info)，分别对应图像np.ndarray数据、
                   存储与标注框相关信息的字典。
        """
        mean = np.array(self.mean)[np.newaxis, np.newaxis, :]
        std = np.array(self.std)[np.newaxis, np.newaxis, :]
        im = normalize(im, mean, std, self.min_val, self.max_val)
        if label_info is None:
            return (im, im_info)
        else:
            return (im, im_info, label_info)


class RandomDistort(DetTransform):
    """以一定的概率对图像进行随机像素内容变换，模型训练时的数据增强操作

    1. 对变换的操作顺序进行随机化操作。
    2. 按照1中的顺序以一定的概率对图像进行随机像素内容变换。

    【注意】如果输入是uint8/uint16的RGB图像，该数据增强必须在数据增强Normalize之前使用。

    Args:
        brightness_range (float): 明亮度的缩放系数范围。
            从[1-`brightness_range`, 1+`brightness_range`]中随机取值作为明亮度缩放因子`scale`，
            按照公式`image = image * scale`调整图像明亮度。默认值为0.5。
        brightness_prob (float): 随机调整明亮度的概率。默认为0.5。
        contrast_range (float): 对比度的缩放系数范围。
            从[1-`contrast_range`, 1+`contrast_range`]中随机取值作为对比度缩放因子`scale`，
            按照公式`image = image * scale + (image_mean + 0.5) * (1 - scale)`调整图像对比度。默认为0.5。
        contrast_prob (float): 随机调整对比度的概率。默认为0.5。
        saturation_range (float): 饱和度的缩放系数范围。
            从[1-`saturation_range`, 1+`saturation_range`]中随机取值作为饱和度缩放因子`scale`，
            按照公式`image = gray * (1 - scale) + image * scale`，
            其中`gray = R * 299/1000 + G * 587/1000+ B * 114/1000`。默认为0.5。
        saturation_prob (float): 随机调整饱和度的概率。默认为0.5。
        hue_range (int): 调整色相角度的差值取值范围。
            从[-`hue_range`, `hue_range`]中随机取值作为色相角度调整差值`delta`，
            按照公式`hue = hue + delta`调整色相角度 。默认为18，取值范围[0, 360]。
        hue_prob (float): 随机调整色调的概率。默认为0.5。
    """

    def __init__(self,
                 brightness_range=0.5,
                 brightness_prob=0.5,
                 contrast_range=0.5,
                 contrast_prob=0.5,
                 saturation_range=0.5,
                 saturation_prob=0.5,
                 hue_range=18,
                 hue_prob=0.5):
        self.brightness_range = brightness_range
        self.brightness_prob = brightness_prob
        self.contrast_range = contrast_range
        self.contrast_prob = contrast_prob
        self.saturation_range = saturation_range
        self.saturation_prob = saturation_prob
        self.hue_range = hue_range
        self.hue_prob = hue_prob

    def __call__(self, im, im_info=None, label_info=None):
        """
        Args:
            im (np.ndarray): 图像np.ndarray数据。
            im_info (dict, 可选): 存储与图像相关的信息。
            label_info (dict, 可选): 存储与标注框相关的信息。

        Returns:
            tuple: 当label_info为空时，返回的tuple为(im, im_info)，分别对应图像np.ndarray数据、存储与图像相关信息的字典；
                   当label_info不为空时，返回的tuple为(im, im_info, label_info)，分别对应图像np.ndarray数据、
                   存储与标注框相关信息的字典。
        """
        if im.shape[-1] != 3:
            raise Exception(
                "Only the 3-channel RGB image is supported in the RandomDistort operator, but recieved image channel is {}".
                format(im.shape[-1]))

        if self.data_type not in [np.uint8, np.uint16, np.float32]:
            raise Exception(
                "Only the uint8/uint16/float32 RGB image is supported in the RandomDistort operator, but recieved image data type is {}".
                format(self.data_type))

        brightness_lower = 1 - self.brightness_range
        brightness_upper = 1 + self.brightness_range
        contrast_lower = 1 - self.contrast_range
        contrast_upper = 1 + self.contrast_range
        saturation_lower = 1 - self.saturation_range
        saturation_upper = 1 + self.saturation_range
        hue_lower = -self.hue_range
        hue_upper = self.hue_range
        ops = [brightness, contrast, saturation, hue]
        random.shuffle(ops)
        params_dict = {
            'brightness': {
                'brightness_lower': brightness_lower,
                'brightness_upper': brightness_upper,
            },
            'contrast': {
                'contrast_lower': contrast_lower,
                'contrast_upper': contrast_upper,
            },
            'saturation': {
                'saturation_lower': saturation_lower,
                'saturation_upper': saturation_upper,
                'is_rgb': self.to_rgb,
            },
            'hue': {
                'hue_lower': hue_lower,
                'hue_upper': hue_upper,
                'is_rgb': self.to_rgb,
            }
        }
        prob_dict = {
            'brightness': self.brightness_prob,
            'contrast': self.contrast_prob,
            'saturation': self.saturation_prob,
            'hue': self.hue_prob
        }
        for id in range(4):
            params = params_dict[ops[id].__name__]
            prob = prob_dict[ops[id].__name__]
            params['im'] = im

            if np.random.uniform(0, 1) < prob:
                im = ops[id](**params)
        im = im.astype('float32')
        if label_info is None:
            return (im, im_info)
        else:
            return (im, im_info, label_info)


class MixupImage(DetTransform):
    """对图像进行mixup操作,模型训练时的数据增强操作，目前仅YOLOv3模型支持该transform。

    当label_info中不存在mixup字段时，直接返回，否则进行下述操作：
    1. 从随机beta分布中抽取出随机因子factor。
    2.
        - 当factor>=1.0时，去除label_info中的mixup字段，直接返回。
        - 当factor<=0.0时，直接返回label_info中的mixup字段，并在label_info中去除该字段。
        - 其余情况，执行下述操作：
            （1）原图像乘以factor，mixup图像乘以(1-factor)，叠加2个结果。
            （2）拼接原图像标注框和mixup图像标注框。
            （3）拼接原图像标注框类别和mixup图像标注框类别。
            （4）原图像标注框混合得分乘以factor，mixup图像标注框混合得分乘以(1-factor)，叠加2个结果。
    3. 更新im_info中的image_shape信息。

    Args:
        alpha (float): 随机beta分布的下限。默认为1.5。
        beta (float): 随机beta分布的上限。默认为1.5。
        mixup_epoch (int): 在前mixup_epoch轮使用mixup增强操作；当该参数为-1时，该策略不会生效。
            默认为-1。

    Raises:
        ValueError: 数据长度不匹配。
    """

    def __init__(self, alpha=1.5, beta=1.5, mixup_epoch=-1):
        self.alpha = alpha
        self.beta = beta
        if self.alpha <= 0.0:
            raise ValueError("alpha shold be positive in MixupImage")
        if self.beta <= 0.0:
            raise ValueError("beta shold be positive in MixupImage")
        self.mixup_epoch = mixup_epoch

    def _mixup_img(self, img1, img2, factor):
        h = max(img1.shape[0], img2.shape[0])
        w = max(img1.shape[1], img2.shape[1])
        img = np.zeros((h, w, img1.shape[2]), 'float32')
        img[:img1.shape[0], :img1.shape[1], :] = \
            img1.astype('float32') * factor
        img[:img2.shape[0], :img2.shape[1], :] += \
            img2.astype('float32') * (1.0 - factor)
        return img.astype('float32')

    def __call__(self, im, im_info=None, label_info=None):
        """
        Args:
            im (np.ndarray): 图像np.ndarray数据。
            im_info (dict, 可选): 存储与图像相关的信息。
            label_info (dict, 可选): 存储与标注框相关的信息。

        Returns:
            tuple: 当label_info为空时，返回的tuple为(im, im_info)，分别对应图像np.ndarray数据、存储与图像相关信息的字典；
                   当label_info不为空时，返回的tuple为(im, im_info, label_info)，分别对应图像np.ndarray数据、
                   存储与标注框相关信息的字典。
                   其中，im_info更新字段为：
                       - image_shape (np.ndarray): mixup后的图像高、宽二者组成的np.ndarray，形状为(2,)。
                   im_info删除的字段：
                       - mixup (list): 与当前字段进行mixup的图像相关信息。
                   label_info更新字段为：
                       - gt_bbox (np.ndarray): mixup后真实标注框坐标，形状为(n, 4)，
                                          其中n代表真实标注框的个数。
                       - gt_class (np.ndarray): mixup后每个真实标注框对应的类别序号，形状为(n, 1)，
                                           其中n代表真实标注框的个数。
                       - gt_score (np.ndarray): mixup后每个真实标注框对应的混合得分，形状为(n, 1)，
                                           其中n代表真实标注框的个数。

        Raises:
            TypeError: 形参数据类型不满足需求。
        """
        if im_info is None:
            raise TypeError('Cannot do MixupImage! ' +
                            'Becasuse the im_info can not be None!')
        if 'mixup' not in im_info:
            if label_info is None:
                return (im, im_info)
            else:
                return (im, im_info, label_info)
        factor = np.random.beta(self.alpha, self.beta)
        factor = max(0.0, min(1.0, factor))
        if im_info['epoch'] > self.mixup_epoch \
                or factor >= 1.0:
            im_info.pop('mixup')
            if label_info is None:
                return (im, im_info)
            else:
                return (im, im_info, label_info)
        if factor <= 0.0:
            return im_info.pop('mixup')
        im = self._mixup_img(im, im_info['mixup'][0], factor)
        if label_info is None:
            raise TypeError('Cannot do MixupImage! ' +
                            'Becasuse the label_info can not be None!')
        if 'gt_bbox' not in label_info or \
                'gt_class' not in label_info or \
                'gt_score' not in label_info:
            raise TypeError('Cannot do MixupImage! ' + \
                            'Becasuse gt_bbox/gt_class/gt_score is not in label_info!')
        gt_bbox1 = label_info['gt_bbox']
        gt_bbox2 = im_info['mixup'][2]['gt_bbox']
        gt_class1 = label_info['gt_class']
        gt_class2 = im_info['mixup'][2]['gt_class']
        gt_score1 = label_info['gt_score']
        gt_score2 = im_info['mixup'][2]['gt_score']
        if 'gt_poly' in label_info:
            gt_poly1 = label_info['gt_poly']
            gt_poly2 = im_info['mixup'][2]['gt_poly']
        is_crowd1 = label_info['is_crowd']
        is_crowd2 = im_info['mixup'][2]['is_crowd']

        if 0 not in gt_class1 and 0 not in gt_class2:
            gt_bbox = np.concatenate((gt_bbox1, gt_bbox2), axis=0)
            gt_class = np.concatenate((gt_class1, gt_class2), axis=0)
            gt_score = np.concatenate(
                (gt_score1 * factor, gt_score2 * (1. - factor)), axis=0)
            if 'gt_poly' in label_info:
                label_info['gt_poly'] = gt_poly1 + gt_poly2
            is_crowd = np.concatenate((is_crowd1, is_crowd2), axis=0)
        elif 0 in gt_class1:
            gt_bbox = gt_bbox2
            gt_class = gt_class2
            gt_score = gt_score2 * (1. - factor)
            if 'gt_poly' in label_info:
                label_info['gt_poly'] = gt_poly2
            is_crowd = is_crowd2
        else:
            gt_bbox = gt_bbox1
            gt_class = gt_class1
            gt_score = gt_score1 * factor
            if 'gt_poly' in label_info:
                label_info['gt_poly'] = gt_poly1
            is_crowd = is_crowd1
        label_info['gt_bbox'] = gt_bbox
        label_info['gt_score'] = gt_score
        label_info['gt_class'] = gt_class
        label_info['is_crowd'] = is_crowd
        im_info['image_shape'] = np.array([im.shape[0],
                                           im.shape[1]]).astype('int32')
        im_info.pop('mixup')
        if label_info is None:
            return (im, im_info)
        else:
            return (im, im_info, label_info)


class RandomExpand(DetTransform):
    """随机扩张图像，模型训练时的数据增强操作。
    1. 随机选取扩张比例（扩张比例大于1时才进行扩张）。
    2. 计算扩张后图像大小。
    3. 初始化像素值为输入填充值的图像，并将原图像随机粘贴于该图像上。
    4. 根据原图像粘贴位置换算出扩张后真实标注框的位置坐标。
    5. 根据原图像粘贴位置换算出扩张后真实分割区域的位置坐标。
    Args:
        ratio (float): 图像扩张的最大比例。默认为4.0。
        prob (float): 随机扩张的概率。默认为0.5。
        fill_value (list): 扩张图像的初始填充值（0-255）。默认为[123.675, 116.28, 103.53]。
    """

    def __init__(self,
                 ratio=4.,
                 prob=0.5,
                 fill_value=[123.675, 116.28, 103.53]):
        super(RandomExpand, self).__init__()
        assert ratio > 1.01, "expand ratio must be larger than 1.01"
        self.ratio = ratio
        self.prob = prob
        assert isinstance(fill_value, Sequence), \
            "fill value must be sequence"
        if not isinstance(fill_value, tuple):
            fill_value = tuple(fill_value)
        self.fill_value = fill_value

    def __call__(self, im, im_info=None, label_info=None):
        """
        Args:
            im (np.ndarray): 图像np.ndarray数据。
            im_info (dict, 可选): 存储与图像相关的信息。
            label_info (dict, 可选): 存储与标注框相关的信息。
        Returns:
            tuple: 当label_info为空时，返回的tuple为(im, im_info)，分别对应图像np.ndarray数据、存储与图像相关信息的字典；
                   当label_info不为空时，返回的tuple为(im, im_info, label_info)，分别对应图像np.ndarray数据、
                   存储与标注框相关信息的字典。
                   其中，im_info更新字段为：
                       - image_shape (np.ndarray): 扩张后的图像高、宽二者组成的np.ndarray，形状为(2,)。
                   label_info更新字段为：
                       - gt_bbox (np.ndarray): 随机扩张后真实标注框坐标，形状为(n, 4)，
                                          其中n代表真实标注框的个数。
                       - gt_class (np.ndarray): 随机扩张后每个真实标注框对应的类别序号，形状为(n, 1)，
                                           其中n代表真实标注框的个数。
        Raises:
            TypeError: 形参数据类型不满足需求。
        """
        if im_info is None or label_info is None:
            raise TypeError(
                'Cannot do RandomExpand! ' +
                'Becasuse the im_info and label_info can not be None!')
        if 'gt_bbox' not in label_info or \
                'gt_class' not in label_info:
            raise TypeError('Cannot do RandomExpand! ' + \
                            'Becasuse gt_bbox/gt_class is not in label_info!')
        if np.random.uniform(0., 1.) > self.prob:
            return (im, im_info, label_info)

        if 'gt_class' in label_info and 0 in label_info['gt_class']:
            return (im, im_info, label_info)
        image_shape = im_info['image_shape']
        height = int(image_shape[0])
        width = int(image_shape[1])

        expand_ratio = np.random.uniform(1., self.ratio)
        h = int(height * expand_ratio)
        w = int(width * expand_ratio)
        if not h > height or not w > width:
            return (im, im_info, label_info)
        y = np.random.randint(0, h - height)
        x = np.random.randint(0, w - width)
        canvas = np.ones((h, w, 3), dtype=np.float32)
        canvas *= np.array(self.fill_value, dtype=np.float32)
        canvas[y:y + height, x:x + width, :] = im

        im_info['image_shape'] = np.array([h, w]).astype('int32')
        if 'gt_bbox' in label_info and len(label_info['gt_bbox']) > 0:
            label_info['gt_bbox'] += np.array([x, y] * 2, dtype=np.float32)
        if 'gt_poly' in label_info and len(label_info['gt_poly']) > 0:
            label_info['gt_poly'] = expand_segms(label_info['gt_poly'], x, y,
                                                 height, width, expand_ratio)
        return (canvas, im_info, label_info)


class RandomCrop(DetTransform):
    """随机裁剪图像。
    1. 若allow_no_crop为True，则在thresholds加入’no_crop’。
    2. 随机打乱thresholds。
    3. 遍历thresholds中各元素：
        (1) 如果当前thresh为’no_crop’，则返回原始图像和标注信息。
        (2) 随机取出aspect_ratio和scaling中的值并由此计算出候选裁剪区域的高、宽、起始点。
        (3) 计算真实标注框与候选裁剪区域IoU，若全部真实标注框的IoU都小于thresh，则继续第3步。
        (4) 如果cover_all_box为True且存在真实标注框的IoU小于thresh，则继续第3步。
        (5) 筛选出位于候选裁剪区域内的真实标注框，若有效框的个数为0，则继续第3步，否则进行第4步。
    4. 换算有效真值标注框相对候选裁剪区域的位置坐标。
    5. 换算有效分割区域相对候选裁剪区域的位置坐标。

    Args:
        aspect_ratio (list): 裁剪后短边缩放比例的取值范围，以[min, max]形式表示。默认值为[.5, 2.]。
        thresholds (list): 判断裁剪候选区域是否有效所需的IoU阈值取值列表。默认值为[.0, .1, .3, .5, .7, .9]。
        scaling (list): 裁剪面积相对原面积的取值范围，以[min, max]形式表示。默认值为[.3, 1.]。
        num_attempts (int): 在放弃寻找有效裁剪区域前尝试的次数。默认值为50。
        allow_no_crop (bool): 是否允许未进行裁剪。默认值为True。
        cover_all_box (bool): 是否要求所有的真实标注框都必须在裁剪区域内。默认值为False。
    """

    def __init__(self,
                 aspect_ratio=[.5, 2.],
                 thresholds=[.0, .1, .3, .5, .7, .9],
                 scaling=[.3, 1.],
                 num_attempts=50,
                 allow_no_crop=True,
                 cover_all_box=False):
        self.aspect_ratio = aspect_ratio
        self.thresholds = thresholds
        self.scaling = scaling
        self.num_attempts = num_attempts
        self.allow_no_crop = allow_no_crop
        self.cover_all_box = cover_all_box

    def __call__(self, im, im_info=None, label_info=None):
        """
        Args:
            im (np.ndarray): 图像np.ndarray数据。
            im_info (dict, 可选): 存储与图像相关的信息。
            label_info (dict, 可选): 存储与标注框相关的信息。

        Returns:
            tuple: 当label_info为空时，返回的tuple为(im, im_info)，分别对应图像np.ndarray数据、存储与图像相关信息的字典；
                   当label_info不为空时，返回的tuple为(im, im_info, label_info)，分别对应图像np.ndarray数据、
                   存储与标注框相关信息的字典。
                   其中，im_info更新字段为：
                           - image_shape (np.ndarray): 扩裁剪的图像高、宽二者组成的np.ndarray，形状为(2,)。
                       label_info更新字段为：
                           - gt_bbox (np.ndarray): 随机裁剪后真实标注框坐标，形状为(n, 4)，
                                          其中n代表真实标注框的个数。
                           - gt_class (np.ndarray): 随机裁剪后每个真实标注框对应的类别序号，形状为(n, 1)，
                                           其中n代表真实标注框的个数。
                           - gt_score (np.ndarray): 随机裁剪后每个真实标注框对应的混合得分，形状为(n, 1)，
                                           其中n代表真实标注框的个数。

        Raises:
            TypeError: 形参数据类型不满足需求。
        """
        if im_info is None or label_info is None:
            raise TypeError(
                'Cannot do RandomCrop! ' +
                'Becasuse the im_info and label_info can not be None!')
        if 'gt_bbox' not in label_info or \
                'gt_class' not in label_info:
            raise TypeError('Cannot do RandomCrop! ' + \
                            'Becasuse gt_bbox/gt_class is not in label_info!')

        if len(label_info['gt_bbox']) == 0:
            return (im, im_info, label_info)
        if 'gt_class' in label_info and 0 in label_info['gt_class']:
            return (im, im_info, label_info)

        image_shape = im_info['image_shape']
        w = image_shape[1]
        h = image_shape[0]
        gt_bbox = label_info['gt_bbox']
        thresholds = list(self.thresholds)
        if self.allow_no_crop:
            thresholds.append('no_crop')
        np.random.shuffle(thresholds)

        for thresh in thresholds:
            if thresh == 'no_crop':
                return (im, im_info, label_info)

            found = False
            for i in range(self.num_attempts):
                scale = np.random.uniform(*self.scaling)
                min_ar, max_ar = self.aspect_ratio
                aspect_ratio = np.random.uniform(
                    max(min_ar, scale**2), min(max_ar, scale**-2))
                crop_h = int(h * scale / np.sqrt(aspect_ratio))
                crop_w = int(w * scale * np.sqrt(aspect_ratio))
                crop_y = np.random.randint(0, h - crop_h)
                crop_x = np.random.randint(0, w - crop_w)
                crop_box = [crop_x, crop_y, crop_x + crop_w, crop_y + crop_h]
                iou = iou_matrix(
                    gt_bbox, np.array(
                        [crop_box], dtype=np.float32))
                if iou.max() < thresh:
                    continue

                if self.cover_all_box and iou.min() < thresh:
                    continue

                cropped_box, valid_ids = crop_box_with_center_constraint(
                    gt_bbox, np.array(
                        crop_box, dtype=np.float32))
                if valid_ids.size > 0:
                    found = True
                    break

            if found:
                if 'gt_poly' in label_info and len(label_info['gt_poly']) > 0:
                    crop_polys = crop_segms(
                        label_info['gt_poly'],
                        valid_ids,
                        np.array(
                            crop_box, dtype=np.int64),
                        h,
                        w)
                    if [] in crop_polys:
                        delete_id = list()
                        valid_polys = list()
                        for id, crop_poly in enumerate(crop_polys):
                            if crop_poly == []:
                                delete_id.append(id)
                            else:
                                valid_polys.append(crop_poly)
                        valid_ids = np.delete(valid_ids, delete_id)
                        if len(valid_polys) == 0:
                            return (im, im_info, label_info)
                        label_info['gt_poly'] = valid_polys
                    else:
                        label_info['gt_poly'] = crop_polys
                im = crop_image(im, crop_box)
                label_info['gt_bbox'] = np.take(cropped_box, valid_ids, axis=0)
                label_info['gt_class'] = np.take(
                    label_info['gt_class'], valid_ids, axis=0)
                im_info['image_shape'] = np.array(
                    [crop_box[3] - crop_box[1],
                     crop_box[2] - crop_box[0]]).astype('int32')
                if 'gt_score' in label_info:
                    label_info['gt_score'] = np.take(
                        label_info['gt_score'], valid_ids, axis=0)

                if 'is_crowd' in label_info:
                    label_info['is_crowd'] = np.take(
                        label_info['is_crowd'], valid_ids, axis=0)
                return (im, im_info, label_info)

        return (im, im_info, label_info)


class CLAHE(DetTransform):
    """对图像进行对比度增强。
    Args:
        clip_limit (int|float): 颜色对比度的阈值，默认值为2.。
        tile_grid_size (list|tuple): 进行像素均衡化的网格大小。默认值为(8, 8)。
    Raises:
        TypeError: 形参数据类型不满足需求。
    """

    def __init__(self, clip_limit=2., tile_grid_size=(8, 8)):
        self.clip_limit = clip_limit
        self.tile_grid_size = tile_grid_size

    def __call__(self, im, im_info=None, label_info=None):
        """
        Args:
            im (numnp.ndarraypy): 图像np.ndarray数据。
            im_info (dict, 可选): 存储与图像相关的信息。
            label_info (dict, 可选): 存储与标注框相关的信息。

        Returns:
            tuple: 当label_info为空时，返回的tuple为(im, im_info)，分别对应图像np.ndarray数据、存储与图像相关信息的字典；
                   当label_info不为空时，返回的tuple为(im, im_info, label_info)，分别对应图像np.ndarray数据、
                   存储与标注框相关信息的字典。
        """
        if im.shape[-1] != 1:
            raise Exception(
                "Only the one-channel image is supported in the CLAHE transform, but recieved image channel is {}".
                format(im.shape[-1]))
        clahe = cv2.createCLAHE(
            clipLimit=self.clip_limit, tileGridSize=self.tile_grid_size)
        im = clahe.apply(im).astype(im.dtype)

        if label_info is None:
            return (im, im_info)
        else:
            return (im, im_info, label_info)


class ArrangeFasterRCNN(DetTransform):
    """获取FasterRCNN模型训练/验证/预测所需信息。

    Args:
        mode (str): 指定数据用于何种用途，取值范围为['train', 'eval', 'test', 'quant']。

    Raises:
        ValueError: mode的取值不在['train', 'eval', 'test', 'quant']之内。
    """

    def __init__(self, mode=None):
        if mode not in ['train', 'eval', 'test', 'quant']:
            raise ValueError(
                "mode must be in ['train', 'eval', 'test', 'quant']!")
        self.mode = mode

    def __call__(self, im, im_info=None, label_info=None):
        """
        Args:
            im (np.ndarray): 图像np.ndarray数据。
            im_info (dict, 可选): 存储与图像相关的信息。
            label_info (dict, 可选): 存储与标注框相关的信息。

        Returns:
            tuple: 当mode为'train'时，返回(im, im_resize_info, gt_bbox, gt_class, is_crowd)，分别对应
                图像np.ndarray数据、图像相当对于原图的resize信息、真实标注框、真实标注框对应的类别、真实标注框内是否是一组对象；
                当mode为'eval'时，返回(im, im_resize_info, im_id, im_shape, gt_bbox, gt_class, is_difficult)，
                分别对应图像np.ndarray数据、图像相当对于原图的resize信息、图像id、图像大小信息、真实标注框、真实标注框对应的类别、
                真实标注框是否为难识别对象；当mode为'test'或'quant'时，返回(im, im_resize_info, im_shape)，分别对应图像np.ndarray数据、
                图像相当对于原图的resize信息、图像大小信息。

        Raises:
            TypeError: 形参数据类型不满足需求。
            ValueError: 数据长度不匹配。
        """
        im = permute(im, False)
        if self.mode == 'train':
            if im_info is None or label_info is None:
                raise TypeError(
                    'Cannot do ArrangeFasterRCNN! ' +
                    'Becasuse the im_info and label_info can not be None!')
            if len(label_info['gt_bbox']) != len(label_info['gt_class']):
                raise ValueError("gt num mismatch: bbox and class.")
            im_resize_info = im_info['im_resize_info']
            gt_bbox = label_info['gt_bbox']
            gt_class = label_info['gt_class']
            is_crowd = label_info['is_crowd']
            outputs = (im, im_resize_info, gt_bbox, gt_class, is_crowd)
        elif self.mode == 'eval':
            if im_info is None or label_info is None:
                raise TypeError(
                    'Cannot do ArrangeFasterRCNN! ' +
                    'Becasuse the im_info and label_info can not be None!')
            im_resize_info = im_info['im_resize_info']
            im_id = im_info['im_id']
            im_shape = np.array(
                (im_info['image_shape'][0], im_info['image_shape'][1], 1),
                dtype=np.float32)
            gt_bbox = label_info['gt_bbox']
            gt_class = label_info['gt_class']
            is_difficult = label_info['difficult']
            outputs = (im, im_resize_info, im_id, im_shape, gt_bbox, gt_class,
                       is_difficult)
        else:
            if im_info is None:
                raise TypeError('Cannot do ArrangeFasterRCNN! ' +
                                'Becasuse the im_info can not be None!')
            im_resize_info = im_info['im_resize_info']
            im_shape = np.array(
                (im_info['image_shape'][0], im_info['image_shape'][1], 1),
                dtype=np.float32)
            outputs = (im, im_resize_info, im_shape)
        return outputs


class ArrangeMaskRCNN(DetTransform):
    """获取MaskRCNN模型训练/验证/预测所需信息。

    Args:
        mode (str): 指定数据用于何种用途，取值范围为['train', 'eval', 'test', 'quant']。

    Raises:
        ValueError: mode的取值不在['train', 'eval', 'test', 'quant']之内。
    """

    def __init__(self, mode=None):
        if mode not in ['train', 'eval', 'test', 'quant']:
            raise ValueError(
                "mode must be in ['train', 'eval', 'test', 'quant']!")
        self.mode = mode

    def __call__(self, im, im_info=None, label_info=None):
        """
        Args:
            im (np.ndarray): 图像np.ndarray数据。
            im_info (dict, 可选): 存储与图像相关的信息。
            label_info (dict, 可选): 存储与标注框相关的信息。

        Returns:
            tuple: 当mode为'train'时，返回(im, im_resize_info, gt_bbox, gt_class, is_crowd, gt_masks)，分别对应
                图像np.ndarray数据、图像相当对于原图的resize信息、真实标注框、真实标注框对应的类别、真实标注框内是否是一组对象、
                真实分割区域；当mode为'eval'时，返回(im, im_resize_info, im_id, im_shape)，分别对应图像np.ndarray数据、
                图像相当对于原图的resize信息、图像id、图像大小信息；当mode为'test'或'quant'时，返回(im, im_resize_info, im_shape)，
                分别对应图像np.ndarray数据、图像相当对于原图的resize信息、图像大小信息。

        Raises:
            TypeError: 形参数据类型不满足需求。
            ValueError: 数据长度不匹配。
        """
        im = permute(im, False)
        if self.mode == 'train':
            if im_info is None or label_info is None:
                raise TypeError(
                    'Cannot do ArrangeTrainMaskRCNN! ' +
                    'Becasuse the im_info and label_info can not be None!')
            if len(label_info['gt_bbox']) != len(label_info['gt_class']):
                raise ValueError("gt num mismatch: bbox and class.")
            im_resize_info = im_info['im_resize_info']
            gt_bbox = label_info['gt_bbox']
            gt_class = label_info['gt_class']
            is_crowd = label_info['is_crowd']
            assert 'gt_poly' in label_info
            segms = label_info['gt_poly']
            if len(segms) != 0:
                assert len(segms) == is_crowd.shape[0]
            gt_masks = []
            valid = True
            for i in range(len(segms)):
                segm = segms[i]
                gt_segm = []
                if is_crowd[i]:
                    gt_segm.append([[0, 0]])
                else:
                    for poly in segm:
                        if len(poly) == 0:
                            valid = False
                            break
                        gt_segm.append(np.array(poly).reshape(-1, 2))
                if (not valid) or len(gt_segm) == 0:
                    break
                gt_masks.append(gt_segm)
            outputs = (im, im_resize_info, gt_bbox, gt_class, is_crowd,
                       gt_masks)
        else:
            if im_info is None:
                raise TypeError('Cannot do ArrangeMaskRCNN! ' +
                                'Becasuse the im_info can not be None!')
            im_resize_info = im_info['im_resize_info']
            im_shape = np.array(
                (im_info['image_shape'][0], im_info['image_shape'][1], 1),
                dtype=np.float32)
            if self.mode == 'eval':
                im_id = im_info['im_id']
                outputs = (im, im_resize_info, im_id, im_shape)
            else:
                outputs = (im, im_resize_info, im_shape)
        return outputs


class ArrangeYOLOv3(DetTransform):
    """获取YOLOv3模型训练/验证/预测所需信息。

    Args:
        mode (str): 指定数据用于何种用途，取值范围为['train', 'eval', 'test', 'quant']。

    Raises:
        ValueError: mode的取值不在['train', 'eval', 'test', 'quant']之内。
    """

    def __init__(self, mode=None):
        if mode not in ['train', 'eval', 'test', 'quant']:
            raise ValueError(
                "mode must be in ['train', 'eval', 'test', 'quant']!")
        self.mode = mode

    def __call__(self, im, im_info=None, label_info=None):
        """
        Args:
            im (np.ndarray): 图像np.ndarray数据。
            im_info (dict, 可选): 存储与图像相关的信息。
            label_info (dict, 可选): 存储与标注框相关的信息。

        Returns:
            tuple: 当mode为'train'时，返回(im, gt_bbox, gt_class, gt_score, im_shape)，分别对应
                图像np.ndarray数据、真实标注框、真实标注框对应的类别、真实标注框混合得分、图像大小信息；
                当mode为'eval'时，返回(im, im_shape, im_id, gt_bbox, gt_class, difficult)，
                分别对应图像np.ndarray数据、图像大小信息、图像id、真实标注框、真实标注框对应的类别、
                真实标注框是否为难识别对象；当mode为'test'或'quant'时，返回(im, im_shape)，
                分别对应图像np.ndarray数据、图像大小信息。

        Raises:
            TypeError: 形参数据类型不满足需求。
            ValueError: 数据长度不匹配。
        """
        im = permute(im, False)
        if self.mode == 'train':
            if im_info is None or label_info is None:
                raise TypeError(
                    'Cannot do ArrangeYolov3! ' +
                    'Becasuse the im_info and label_info can not be None!')
            im_shape = im_info['image_shape']
            if len(label_info['gt_bbox']) != len(label_info['gt_class']):
                raise ValueError("gt num mismatch: bbox and class.")
            if len(label_info['gt_bbox']) != len(label_info['gt_score']):
                raise ValueError("gt num mismatch: bbox and score.")
            gt_bbox = np.zeros((50, 4), dtype=im.dtype)
            gt_class = np.zeros((50, ), dtype=np.int32)
            gt_score = np.zeros((50, ), dtype=im.dtype)
            gt_num = min(50, len(label_info['gt_bbox']))
            if gt_num > 0:
                label_info['gt_class'][:gt_num, 0] = label_info[
                    'gt_class'][:gt_num, 0] - 1
                if -1 not in label_info['gt_class']:
                    gt_bbox[:gt_num, :] = label_info['gt_bbox'][:gt_num, :]
                    gt_class[:gt_num] = label_info['gt_class'][:gt_num, 0]
                    gt_score[:gt_num] = label_info['gt_score'][:gt_num, 0]
            # parse [x1, y1, x2, y2] to [x, y, w, h]
            gt_bbox[:, 2:4] = gt_bbox[:, 2:4] - gt_bbox[:, :2]
            gt_bbox[:, :2] = gt_bbox[:, :2] + gt_bbox[:, 2:4] / 2.
            outputs = (im, gt_bbox, gt_class, gt_score, im_shape)
        elif self.mode == 'eval':
            if im_info is None or label_info is None:
                raise TypeError(
                    'Cannot do ArrangeYolov3! ' +
                    'Becasuse the im_info and label_info can not be None!')
            im_shape = im_info['image_shape']
            if len(label_info['gt_bbox']) != len(label_info['gt_class']):
                raise ValueError("gt num mismatch: bbox and class.")
            im_id = im_info['im_id']
            gt_bbox = np.zeros((50, 4), dtype=im.dtype)
            gt_class = np.zeros((50, ), dtype=np.int32)
            difficult = np.zeros((50, ), dtype=np.int32)
            gt_num = min(50, len(label_info['gt_bbox']))
            if gt_num > 0:
                label_info['gt_class'][:gt_num, 0] = label_info[
                    'gt_class'][:gt_num, 0] - 1
                gt_bbox[:gt_num, :] = label_info['gt_bbox'][:gt_num, :]
                gt_class[:gt_num] = label_info['gt_class'][:gt_num, 0]
                difficult[:gt_num] = label_info['difficult'][:gt_num, 0]
            outputs = (im, im_shape, im_id, gt_bbox, gt_class, difficult)
        else:
            if im_info is None:
                raise TypeError('Cannot do ArrangeYolov3! ' +
                                'Becasuse the im_info can not be None!')
            im_shape = im_info['image_shape']
            outputs = (im, im_shape)
        return outputs


class ComposedRCNNTransforms(Compose):
    """ RCNN模型(faster-rcnn/mask-rcnn)图像处理流程，具体如下，
        训练阶段：
        1. 随机以0.5的概率将图像水平翻转
        2. 图像归一化
        3. 图像按比例Resize，scale计算方式如下
            scale = min_max_size[0] / short_size_of_image
            if max_size_of_image * scale > min_max_size[1]:
                scale = min_max_size[1] / max_size_of_image
        4. 将3步骤的长宽进行padding，使得长宽为32的倍数
        验证阶段：
        1. 图像归一化
        2. 图像按比例Resize，scale计算方式同上训练阶段
        3. 将2步骤的长宽进行padding，使得长宽为32的倍数

        Args:
            mode(str): 图像处理流程所处阶段，训练/验证/预测，分别对应'train', 'eval', 'test'
            min_max_size(list): 图像在缩放时，最小边和最大边的约束条件
            mean(list): 图像均值
            std(list): 图像方差
            random_horizontal_flip(bool): 是否以0.5的概率使用随机水平翻转增强，该仅在mode为`train`时生效，默认为True
    """

    def __init__(self,
                 mode,
                 min_max_size=[800, 1333],
                 mean=[0.485, 0.456, 0.406],
                 std=[0.229, 0.224, 0.225],
                 random_horizontal_flip=True):
        if mode == 'train':
            # 训练时的transforms，包含数据增强
            transforms = [
                Normalize(
                    mean=mean, std=std), ResizeByShort(
                        short_size=min_max_size[0], max_size=min_max_size[1]),
                Padding(coarsest_stride=32)
            ]
            if random_horizontal_flip:
                transforms.insert(0, RandomHorizontalFlip())
        else:
            # 验证/预测时的transforms
            transforms = [
                Normalize(
                    mean=mean, std=std), ResizeByShort(
                        short_size=min_max_size[0], max_size=min_max_size[1]),
                Padding(coarsest_stride=32)
            ]

        super(ComposedRCNNTransforms, self).__init__(transforms)


class ComposedYOLOv3Transforms(Compose):
    """YOLOv3模型的图像预处理流程，具体如下，
        训练阶段：
        1. 在前mixup_epoch轮迭代中，使用MixupImage策略，见https://paddlex.readthedocs.io/zh_CN/latest/apis/transforms/det_transforms.html#mixupimage
        2. 对图像进行随机扰动，包括亮度，对比度，饱和度和色调
        3. 随机扩充图像，见https://paddlex.readthedocs.io/zh_CN/latest/apis/transforms/det_transforms.html#randomexpand
        4. 随机裁剪图像
        5. 将4步骤的输出图像Resize成shape参数的大小
        6. 随机0.5的概率水平翻转图像
        7. 图像归一化
        验证/预测阶段：
        1. 将图像Resize成shape参数大小
        2. 图像归一化

        Args:
            mode(str): 图像处理流程所处阶段，训练/验证/预测，分别对应'train', 'eval', 'test'
            shape(list): 输入模型中图像的大小，输入模型的图像会被Resize成此大小
            mixup_epoch(int): 模型训练过程中，前mixup_epoch会使用mixup策略, 若设为-1，则表示不使用该策略
            mean(list): 图像均值
            std(list): 图像方差
            random_distort(bool): 数据增强方式，参数仅在mode为`train`时生效，表示是否在训练过程中随机扰动图像，默认为True
            random_expand(bool): 数据增强方式，参数仅在mode为`train`时生效，表示是否在训练过程中随机扩张图像，默认为True
            random_crop(bool): 数据增强方式，参数仅在mode为`train`时生效，表示是否在训练过程中随机裁剪图像，默认为True
            random_horizontal_flip(bool): 数据增强方式，参数仅在mode为`train`时生效，表示是否在训练过程中随机水平翻转图像，默认为True

    """

    def __init__(self,
                 mode,
                 shape=[608, 608],
                 mixup_epoch=250,
                 mean=[0.485, 0.456, 0.406],
                 std=[0.229, 0.224, 0.225],
                 random_distort=True,
                 random_expand=True,
                 random_crop=True,
                 random_horizontal_flip=True):
        width = shape
        if isinstance(shape, list):
            if shape[0] != shape[1]:
                raise Exception(
                    "In YOLOv3 model, width and height should be equal")
            width = shape[0]
        if width % 32 != 0:
            raise Exception(
                "In YOLOv3 model, width and height should be multiple of 32, e.g 224、256、320...."
            )

        if mode == 'train':
            # 训练时的transforms，包含数据增强
            transforms = [
                MixupImage(mixup_epoch=mixup_epoch), Resize(
                    target_size=width, interp='RANDOM'), Normalize(
                        mean=mean, std=std)
            ]
            if random_horizontal_flip:
                transforms.insert(1, RandomHorizontalFlip())
            if random_crop:
                transforms.insert(1, RandomCrop())
            if random_expand:
                transforms.insert(1, RandomExpand())
            if random_distort:
                transforms.insert(1, RandomDistort())
        else:
            # 验证/预测时的transforms
            transforms = [
                Resize(
                    target_size=width, interp='CUBIC'), Normalize(
                        mean=mean, std=std)
            ]
        super(ComposedYOLOv3Transforms, self).__init__(transforms)


class BatchRandomShape(DetTransform):
    """调整图像大小（resize）。

    对batch数据中的每张图像全部resize到random_shapes中任意一个大小。
    注意：当插值方式为“RANDOM”时，则随机选取一种插值方式进行resize。

    Args:
        random_shapes (list): resize大小选择列表。
            默认为[320, 352, 384, 416, 448, 480, 512, 544, 576, 608]。
        interp (str): resize的插值方式，与opencv的插值方式对应，取值范围为
            ['NEAREST', 'LINEAR', 'CUBIC', 'AREA', 'LANCZOS4', 'RANDOM']。默认为"RANDOM"。
    Raises:
        ValueError: 插值方式不在['NEAREST', 'LINEAR', 'CUBIC',
                    'AREA', 'LANCZOS4', 'RANDOM']中。
    """

    # The interpolation mode
    interp_dict = {
        'NEAREST': cv2.INTER_NEAREST,
        'LINEAR': cv2.INTER_LINEAR,
        'CUBIC': cv2.INTER_CUBIC,
        'AREA': cv2.INTER_AREA,
        'LANCZOS4': cv2.INTER_LANCZOS4
    }

    def __init__(
            self,
            random_shapes=[320, 352, 384, 416, 448, 480, 512, 544, 576, 608],
            interp='RANDOM'):
        if not (interp == "RANDOM" or interp in self.interp_dict):
            raise ValueError("interp should be one of {}".format(
                self.interp_dict.keys()))
        self.random_shapes = random_shapes
        self.interp = interp

    def __call__(self, batch_data):
        """
        Args:
            batch_data (list): 由与图像相关的各种信息组成的batch数据。
        Returns:
            list: 由与图像相关的各种信息组成的batch数据。
        """
        shape = np.random.choice(self.random_shapes)

        if self.interp == "RANDOM":
            interp = random.choice(list(self.interp_dict.keys()))
        else:
            interp = self.interp
        for data_id, data in enumerate(batch_data):
            data_list = list(data)
            im = data_list[0]
            im = np.swapaxes(im, 1, 0)
            im = np.swapaxes(im, 1, 2)
            im = resize(im, shape, self.interp_dict[interp])
            im = np.swapaxes(im, 1, 2)
            im = np.swapaxes(im, 1, 0)
            data_list[0] = im
            batch_data[data_id] = tuple(data_list)
        return batch_data


class GenerateYoloTarget(object):
    """生成YOLOv3的ground truth（真实标注框）在不同特征层的位置转换信息。
       该transform只在YOLOv3计算细粒度loss时使用。

       Args:
           anchors (list|tuple): anchor框的宽度和高度。
           anchor_masks (list|tuple): 在计算损失时，使用anchor的mask索引。
           num_classes (int): 类别数。默认为80。
           iou_thresh (float): iou阈值，当anchor和真实标注框的iou大于该阈值时，计入target。默认为1.0。
    """

    def __init__(self,
                 anchors,
                 anchor_masks,
                 downsample_ratios,
                 num_classes=80,
                 iou_thresh=1.):
        super(GenerateYoloTarget, self).__init__()
        self.anchors = anchors
        self.anchor_masks = anchor_masks
        self.downsample_ratios = downsample_ratios
        self.num_classes = num_classes
        self.iou_thresh = iou_thresh

    def __call__(self, batch_data):
        """
        Args:
            batch_data (list): 由与图像相关的各种信息组成的batch数据。
        Returns:
            list: 由与图像相关的各种信息组成的batch数据。
                  其中，每个数据新添加的字段为：
                           - target0 (np.ndarray): YOLOv3的ground truth在特征层0的位置转换信息，
                                   形状为(特征层0的anchor数量, 6+类别数, 特征层0的h, 特征层0的w)。
                           - target1 (np.ndarray): YOLOv3的ground truth在特征层1的位置转换信息，
                                   形状为(特征层1的anchor数量, 6+类别数, 特征层1的h, 特征层1的w)。
                           - ...
                           -targetn (np.ndarray): YOLOv3的ground truth在特征层n的位置转换信息，
                                   形状为(特征层n的anchor数量, 6+类别数, 特征层n的h, 特征层n的w)。
                    n的是大小由anchor_masks的长度决定。
        """
        im = batch_data[0][0]
        h = im.shape[1]
        w = im.shape[2]
        an_hw = np.array(self.anchors) / np.array([[w, h]])
        for data_id, data in enumerate(batch_data):
            gt_bbox = data[1]
            gt_class = data[2]
            gt_score = data[3]
            im_shape = data[4]
            origin_h = float(im_shape[0])
            origin_w = float(im_shape[1])
            data_list = list(data)
            for i, (
                    mask, downsample_ratio
            ) in enumerate(zip(self.anchor_masks, self.downsample_ratios)):
                grid_h = int(h / downsample_ratio)
                grid_w = int(w / downsample_ratio)
                target = np.zeros(
                    (len(mask), 6 + self.num_classes, grid_h, grid_w),
                    dtype=np.float32)
                for b in range(gt_bbox.shape[0]):
                    gx = gt_bbox[b, 0] / float(origin_w)
                    gy = gt_bbox[b, 1] / float(origin_h)
                    gw = gt_bbox[b, 2] / float(origin_w)
                    gh = gt_bbox[b, 3] / float(origin_h)
                    cls = gt_class[b]
                    score = gt_score[b]
                    if gw <= 0. or gh <= 0. or score <= 0.:
                        continue
                    # find best match anchor index
                    best_iou = 0.
                    best_idx = -1
                    for an_idx in range(an_hw.shape[0]):
                        iou = jaccard_overlap(
                            [0., 0., gw, gh],
                            [0., 0., an_hw[an_idx, 0], an_hw[an_idx, 1]])
                        if iou > best_iou:
                            best_iou = iou
                            best_idx = an_idx
                    gi = int(gx * grid_w)
                    gj = int(gy * grid_h)
                    # gtbox should be regresed in this layes if best match
                    # anchor index in anchor mask of this layer
                    if best_idx in mask:
                        best_n = mask.index(best_idx)
                        # x, y, w, h, scale
                        target[best_n, 0, gj, gi] = gx * grid_w - gi
                        target[best_n, 1, gj, gi] = gy * grid_h - gj
                        target[best_n, 2, gj, gi] = np.log(
                            gw * w / self.anchors[best_idx][0])
                        target[best_n, 3, gj, gi] = np.log(
                            gh * h / self.anchors[best_idx][1])
                        target[best_n, 4, gj, gi] = 2.0 - gw * gh
                        # objectness record gt_score
                        target[best_n, 5, gj, gi] = score
                        # classification
                        target[best_n, 6 + cls, gj, gi] = 1.
                    # For non-matched anchors, calculate the target if the iou
                    # between anchor and gt is larger than iou_thresh
                    if self.iou_thresh < 1:
                        for idx, mask_i in enumerate(mask):
                            if mask_i == best_idx: continue
                            iou = jaccard_overlap(
                                [0., 0., gw, gh],
                                [0., 0., an_hw[mask_i, 0], an_hw[mask_i, 1]])
                            if iou > self.iou_thresh:
                                # x, y, w, h, scale
                                target[idx, 0, gj, gi] = gx * grid_w - gi
                                target[idx, 1, gj, gi] = gy * grid_h - gj
                                target[idx, 2, gj, gi] = np.log(
                                    gw * w / self.anchors[mask_i][0])
                                target[idx, 3, gj, gi] = np.log(
                                    gh * h / self.anchors[mask_i][1])
                                target[idx, 4, gj, gi] = 2.0 - gw * gh
                                # objectness record gt_score
                                target[idx, 5, gj, gi] = score
                                # classification
                                target[idx, 6 + cls, gj, gi] = 1.
                data_list.append(target)
            batch_data[data_id] = tuple(data_list)
        return batch_data
