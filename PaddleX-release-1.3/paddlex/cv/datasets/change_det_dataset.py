# Copyright (c) 2020 PaddlePaddle Authors. All Rights Reserved.
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

from __future__ import absolute_import
import os.path as osp
import random
import copy
import numpy as np
import paddlex.utils.logging as logging
from paddlex.cv.transforms import seg_transforms
from paddlex.utils import path_normalization
from .dataset import Dataset
from .dataset import get_encoding


class ChangeDetDataset(Dataset):
    """读取用于完成地块检测的语义分割任务数据集，并对样本进行相应的处理。

    Args:
        data_dir (str): 数据集所在的目录路径。
        file_list (str): 描述数据集图片1文件、图片2文件和对应标注文件的文件路径（文本内每行路径为相对data_dir的相对路）。
        label_list (str): 描述数据集包含的类别信息文件路径。默认值为None。
        transforms (list): 数据集中每个样本的预处理/增强算子。
        num_workers (int): 数据集中样本在预处理过程中的线程或进程数。默认为'auto'。
        buffer_size (int): 数据集中样本在预处理过程中队列的缓存长度，以样本数为单位。默认为100。
        parallel_method (str): 数据集中样本在预处理过程中并行处理的方式，支持'thread'
            线程和'process'进程两种方式。默认为'process'（Windows和Mac下会强制使用thread，该参数无效）。
        shuffle (bool): 是否需要对数据集中样本打乱顺序。默认为False。
    """

    def __init__(self,
                 data_dir,
                 file_list,
                 label_list=None,
                 transforms=None,
                 num_workers='auto',
                 buffer_size=100,
                 parallel_method='process',
                 shuffle=False):
        super(ChangeDetDataset, self).__init__(
            transforms=transforms,
            num_workers=num_workers,
            buffer_size=buffer_size,
            parallel_method=parallel_method,
            shuffle=shuffle)
        self.file_list = list()
        self.labels = list()
        self._epoch = 0

        if label_list is not None:
            with open(label_list, encoding=get_encoding(label_list)) as f:
                for line in f:
                    item = line.strip()
                    self.labels.append(item)
        with open(file_list, encoding=get_encoding(file_list)) as f:
            for line in f:
                items = line.strip().split()
                if len(items) > 3:
                    raise Exception(
                        "A space is defined as the separator, but it exists in image or label name {}."
                        .format(line))
                items[0] = path_normalization(items[0])
                items[1] = path_normalization(items[1])
                items[2] = path_normalization(items[2])
                full_path_im1 = osp.join(data_dir, items[0])
                full_path_im2 = osp.join(data_dir, items[1])
                full_path_label = osp.join(data_dir, items[2])
                if not osp.exists(full_path_im1):
                    raise IOError('The image file {} is not exist!'.format(
                        full_path_im1))
                if not osp.exists(full_path_im2):
                    raise IOError('The image file {} is not exist!'.format(
                        full_path_im2))
                if not osp.exists(full_path_label):
                    raise IOError('The image file {} is not exist!'.format(
                        full_path_label))
                self.file_list.append(
                    [full_path_im1, full_path_im2, full_path_label])
        self.num_samples = len(self.file_list)
        logging.info("{} samples in file {}".format(
            len(self.file_list), file_list))

    def iterator(self):
        self._epoch += 1
        self._pos = 0
        files = copy.deepcopy(self.file_list)
        if self.shuffle:
            random.shuffle(files)
        files = files[:self.num_samples]
        self.num_samples = len(files)
        for f in files:
            label_path = f[2]
            image1 = seg_transforms.Compose.read_img(f[0])
            image2 = seg_transforms.Compose.read_img(f[1])
            image = np.concatenate((image1, image2), axis=-1)
            sample = [image, None, label_path]
            yield sample
