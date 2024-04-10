# paddlex.det.transforms

对目标检测/实例分割任务的数据进行操作。可以利用[Compose](#compose)类将图像预处理/增强操作进行组合。

## Compose
```python
paddlex.det.transforms.Compose(transforms)
```

根据数据预处理/增强算子对输入数据进行操作。[使用示例](https://github.com/PaddlePaddle/PaddleX/tree/release/1.3/tutorials/train/object_detection/yolov3_mobilenetv1.py#L15)

### 参数
* **transforms** (list): 数据预处理/数据增强列表。

## Normalize
```python
paddlex.det.transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225], min_val=[0., 0., 0.], max_val=[255., 255., 255.])
```

对图像进行标准化。  
1.像素值减去min_val
2.像素值除以(max_val-min_val), 归一化到区间 [0.0, 1.0]。
3.对图像进行减均值除以标准差操作。


### 参数
* **mean** (list): 图像数据集的均值。默认为[0.485, 0.456, 0.406]。长度应与图像通道数量相同。
* **std** (list): 图像数据集的标准差。默认为[0.229, 0.224, 0.225]。长度应与图像通道数量相同。
* **min_val** (list): 图像数据集的最小值。默认值[0, 0, 0]。长度应与图像通道数量相同。
* **max_val** (list): 图像数据集的最大值。默认值[255.0, 255.0, 255.0]。长度应与图像通道数量相同。


## ResizeByShort
```python
paddlex.det.transforms.ResizeByShort(short_size=800, max_size=1333)
```

根据图像的短边调整图像大小（resize）。  
1. 获取图像的长边和短边长度。  
2. 根据短边与short_size的比例，计算长边的目标长度，此时高、宽的resize比例为short_size/原图短边长度。若short_size为数组，则随机从该数组中挑选一个数值作为short_size。
3. 如果max_size>0，调整resize比例：
   如果长边的目标长度>max_size，则高、宽的resize比例为max_size/原图长边长度。
4. 根据调整大小的比例对图像进行resize。

### 参数
* **short_size** (int|list): 短边目标长度。默认为800。当需要做多尺度训练时，可以将`short_size`设置成数组，例如[500, 600, 700, 800]。
* **max_size** (int): 长边目标长度的最大限制。默认为1333。

## Padding
```python
paddlex.det.transforms.Padding(coarsest_stride=1)
```

将图像的长和宽padding至coarsest_stride的倍数。如输入图像为[300, 640], `coarest_stride`为32，则由于300不为32的倍数，因此在图像最右和最下使用0值进行padding，最终输出图像为[320, 640]
1. 如果coarsest_stride为1则直接返回。
2. 计算宽和高与最邻近的coarest_stride倍数差值
3. 根据计算得到的差值，在图像最右和最下进行padding

### 参数
* **coarsest_stride** (int): 填充后的图像长、宽为该参数的倍数，默认为1。

## Resize
```python
paddlex.det.transforms.Resize(target_size=608, interp='LINEAR')
```

调整图像大小（resize）。  
* 当目标大小（target_size）类型为int时，根据插值方式，将图像resize为[target_size, target_size]。  
* 当目标大小（target_size）类型为list或tuple时，根据插值方式，将图像resize为target_size。  
【注意】当插值方式为“RANDOM”时，则随机选取一种插值方式进行resize，作为模型训练时的数据增强操作。

### 参数
* **target_size** (int/list/tuple): 短边目标长度。默认为608。
* **interp** (str): resize的插值方式，与opencv的插值方式对应，取值范围为['NEAREST', 'LINEAR', 'CUBIC', 'AREA', 'LANCZOS4', 'RANDOM']。默认为"LINEAR"。

## RandomHorizontalFlip
```python
paddlex.det.transforms.RandomHorizontalFlip(prob=0.5)
```

以一定的概率对图像进行随机水平翻转，模型训练时的数据增强操作。

### 参数
* **prob** (float): 随机水平翻转的概率。默认为0.5。

## RandomDistort
```python
paddlex.det.transforms.RandomDistort(brightness_range=0.5, brightness_prob=0.5, contrast_range=0.5, contrast_prob=0.5, saturation_range=0.5, saturation_prob=0.5, hue_range=18, hue_prob=0.5)
```

以一定的概率对图像进行随机像素内容变换，模型训练时的数据增强操作。  
1. 对变换的操作顺序进行随机化操作。
2. 按照1中的顺序以一定的概率对图像进行随机像素内容变换。  

【注意】如果输入是uint8/uint16的RGB图像，该数据增强必须在数据增强Normalize之前使用。

### 参数
* **brightness_range** (float): 明亮度的缩放系数范围。从[1-`brightness_range`, 1+`brightness_range`]中随机取值作为明亮度缩放因子`scale`，按照公式`image = image * scale`调整图像明亮度。默认值为0.5。
* **brightness_prob** (float): 随机调整明亮度的概率。默认为0.5。
* **contrast_range** (float): 对比度的缩放系数范围。从[1-`contrast_range`, 1+`contrast_range`]中随机取值作为对比度缩放因子`scale`，按照公式`image = image * scale + (image_mean + 0.5) * (1 - scale)`调整图像对比度。默认为0.5。
* **contrast_prob** (float): 随机调整对比度的概率。默认为0.5。
* **saturation_range** (float): 饱和度的缩放系数范围。从[1-`saturation_range`, 1+`saturation_range`]中随机取值作为饱和度缩放因子`scale`，按照公式`image = gray * (1 - scale) + image * scale`，其中`gray = R * 299/1000 + G * 587/1000+ B * 114/1000`。默认为0.5。
* **saturation_prob** (float): 随机调整饱和度的概率。默认为0.5。
* **hue_range** (int): 调整色相角度的差值取值范围。从[-`hue_range`, `hue_range`]中随机取值作为色相角度调整差值`delta`，按照公式`hue = hue + delta`调整色相角度 。默认为18，取值范围[0, 360]。
* **hue_prob** (float): 随机调整色调的概率。默认为0.5。


## MixupImage
```python
paddlex.det.transforms.MixupImage(alpha=1.5, beta=1.5, mixup_epoch=-1)
```

对图像进行mixup操作，模型训练时的数据增强操作，目前仅YOLOv3模型支持该transform。  
当label_info中不存在mixup字段时，直接返回，否则进行下述操作：
1. 从随机beta分布中抽取出随机因子factor。  
2. 根据不同情况进行处理：
    * 当factor>=1.0时，去除label_info中的mixup字段，直接返回。  
    * 当factor<=0.0时，直接返回label_info中的mixup字段，并在label_info中去除该字段。  
    * 其余情况，执行下述操作：  
    （1）原图像乘以factor，mixup图像乘以(1-factor)，叠加2个结果。  
    （2）拼接原图像标注框和mixup图像标注框。  
    （3）拼接原图像标注框类别和mixup图像标注框类别。  
    （4）原图像标注框混合得分乘以factor，mixup图像标注框混合得分乘以(1-factor)，叠加2个结果。
3. 更新im_info中的augment_shape信息。

### 参数
* **alpha** (float): 随机beta分布的下限。默认为1.5。
* **beta** (float): 随机beta分布的上限。默认为1.5。
* **mixup_epoch** (int): 在前mixup_epoch轮使用mixup增强操作；当该参数为-1时，该策略不会生效。默认为-1。

## RandomExpand
```python
paddlex.det.transforms.RandomExpand(ratio=4., prob=0.5, fill_value=[123.675, 116.28, 103.53])
```

随机扩张图像，模型训练时的数据增强操作。
1. 随机选取扩张比例（扩张比例大于1时才进行扩张）。
2. 计算扩张后图像大小。
3. 初始化像素值为输入填充值的图像，并将原图像随机粘贴于该图像上。
4. 根据原图像粘贴位置换算出扩张后真实标注框的位置坐标。
5. 根据原图像粘贴位置换算出扩张后真实分割区域的位置坐标。

### 参数
* **ratio** (float): 图像扩张的最大比例。默认为4.0。
* **prob** (float): 随机扩张的概率。默认为0.5。
* **fill_value** (list): 扩张图像的初始填充值（0-255）。默认为[123.675, 116.28, 103.53]。  

【注意】该数据增强必须在数据增强Resize、ResizeByShort之前使用。

## RandomCrop
```python
paddlex.det.transforms.RandomCrop(aspect_ratio=[.5, 2.], thresholds=[.0, .1, .3, .5, .7, .9], scaling=[.3, 1.], num_attempts=50, allow_no_crop=True, cover_all_box=False)
```

随机裁剪图像，模型训练时的数据增强操作。  
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

【注意】该数据增强必须在数据增强Resize、ResizeByShort之前使用。

### 参数
* **aspect_ratio** (list): 裁剪后短边缩放比例的取值范围，以[min, max]形式表示。默认值为[.5, 2.]。
* **thresholds** (list): 判断裁剪候选区域是否有效所需的IoU阈值取值列表。默认值为[.0, .1, .3, .5, .7, .9]。
* **scaling** (list): 裁剪面积相对原面积的取值范围，以[min, max]形式表示。默认值为[.3, 1.]。
* **num_attempts** (int): 在放弃寻找有效裁剪区域前尝试的次数。默认值为50。
* **allow_no_crop** (bool): 是否允许未进行裁剪。默认值为True。
* **cover_all_box** (bool): 是否要求所有的真实标注框都必须在裁剪区域内。默认值为False。

## CLAHE
```
paddlex.det.transforms.CLAHE(clip_limit=2., tile_grid_size=(8, 8))
```
对图像进行对比度增强。

【注意】该数据增强只适用于灰度图。

### 参数

* **clip_limit** (int|float): 颜色对比度的阈值，默认值为2.。
* **tile_grid_size** (list|tuple): 进行像素均衡化的网格大小。默认值为(8, 8)。

<!--
## ComposedRCNNTransforms
```python
paddlex.det.transforms.ComposedRCNNTransforms(mode, min_max_size=[224, 224], mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225], random_horizontal_flip=True)
```
目标检测FasterRCNN和实例分割MaskRCNN模型中已经组合好的数据处理流程，开发者可以直接使用ComposedRCNNTransforms，简化手动组合transforms的过程, 该类中已经包含了[RandomHorizontalFlip](#RandomHorizontalFlip)数据增强方式，你仍可以通过[add_augmenters函数接口](#add_augmenters)添加新的数据增强方式。  
ComposedRCNNTransforms共包括以下几个步骤：
> 训练阶段：
> > 1. 随机以0.5的概率将图像水平翻转, 若random_horizontal_flip为False，则跳过此步骤
> > 2. 将图像进行归一化
> > 3. 图像采用[ResizeByShort](#ResizeByShort)方式，根据min_max_size参数，进行缩入
> > 4. 使用[Padding](#Padding)将图像的长和宽分别Padding成32的倍数
> 验证/预测阶段：
> > 1. 将图像进行归一化
> > 2. 图像采用[ResizeByShort](#ResizeByShort)方式，根据min_max_size参数，进行缩入
> > 3. 使用[Padding](#Padding)将图像的长和宽分别Padding成32的倍数

### 参数
* **mode** (str): Transforms所处的阶段，包括`train', 'eval'或'test'
* **min_max_size** (list): 输入模型中图像的最短边长度和最长边长度，参考[ResizeByShort](#ResizeByShort)（与原图大小无关，根据上述几个步骤，会将原图处理成相应大小输入给模型训练)，默认[800, 1333]
* **mean** (list): 图像均值, 默认为[0.485, 0.456, 0.406]。
* **std** (list): 图像方差，默认为[0.229, 0.224, 0.225]。
* **random_horizontal_flip**(bool): 数据增强，是否以0.5的概率使用随机水平翻转增强，仅在mode为'train'时生效，默认为True。底层实现采用[paddlex.det.transforms.RandomHorizontalFlip](#randomhorizontalflip)

### 添加数据增强方式
```python
ComposedRCNNTransforms.add_augmenters(augmenters)
```
> **参数**
> * **augmenters**(list): 数据增强方式列表

#### 使用示例
```
import paddlex as pdx
from paddlex.det import transforms
train_transforms = transforms.ComposedRCNNTransforms(mode='train', min_max_size=[800, 1333])
eval_transforms = transforms.ComposedRCNNTransforms(mode='eval', min_max_size=[800, 1333])

# 添加数据增强
import imgaug.augmenters as iaa
train_transforms.add_augmenters([
			transforms.RandomDistort(),
			iaa.blur.GaussianBlur(sigma=(0.0, 3.0))
])
```
上面代码等价于
```
import paddlex as pdx
from paddlex.det import transforms
train_transforms = transforms.Composed([
		transforms.RandomDistort(),
		iaa.blur.GaussianBlur(sigma=(0.0, 3.0)),
		# 上面两个为通过add_augmenters额外添加的数据增强方式
		transforms.RandomHorizontalFlip(prob=0.5),
		transforms.Normalize(),
        transforms.ResizeByShort(short_size=800, max_size=1333),
        transforms.Padding(coarsest_stride=32)
])
eval_transforms = transforms.Composed([
		transforms.Normalize(),
        transforms.ResizeByShort(short_size=800, max_size=1333),
        transforms.Padding(coarsest_stride=32)
])
```


## ComposedYOLOv3Transforms
```python
paddlex.det.transforms.ComposedYOLOv3Transforms(mode, shape=[608, 608], mixup_epoch=250, mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225], random_distort=True, random_expand=True, random_crop=True, random_horizontal_flip=True)
```
目标检测YOLOv3模型中已经组合好的数据处理流程，开发者可以直接使用ComposedYOLOv3Transforms，简化手动组合transforms的过程, 该类中已经包含了[MixupImage](#MixupImage)、[RandomDistort](#RandomDistort)、[RandomExpand](#RandomExpand)、[RandomCrop](#RandomCrop)、[RandomHorizontalFlip](#RandomHorizontalFlip)5种数据增强方式，你仍可以通过[add_augmenters函数接口](#add_augmenters)添加新的数据增强方式。  
ComposedYOLOv3Transforms共包括以下几个步骤：
> 训练阶段：
> > 1. 在前mixup_epoch轮迭代中，使用MixupImage策略，若mixup_epoch为-1，则跳过此步骤
> > 2. 对图像进行随机扰动，包括亮度，对比度，饱和度和色调，若random_distort为False，则跳过此步骤
> > 3. 随机扩充图像，若random_expand为False， 则跳过此步骤
> > 4. 随机裁剪图像，若random_crop为False， 则跳过此步骤
> > 5. 将4步骤的输出图像Resize成shape参数的大小
> > 6. 随机0.5的概率水平翻转图像，若random_horizontal_flip为False，则跳过此步骤
> > 7. 图像归一化
> 验证/预测阶段：
> > 1. 将图像Resize成shape参数大小
> > 2. 图像归一化

### 参数
* **mode** (str): Transforms所处的阶段，包括`train', 'eval'或'test'
* **shape** (list): 输入模型中图像的大小（与原图大小无关，根据上述几个步骤，会将原图处理成相应大小输入给模型训练)， 默认[608, 608]
* **mixup_epoch**(int): 模型训练过程中，在前mixup_epoch轮迭代中，使用mixup策略，如果为-1，则不使用mixup策略， 默认250。底层实现采用[paddlex.det.transforms.MixupImage](#mixupimage)
* **mean** (list): 图像均值, 默认为[0.485, 0.456, 0.406]。
* **std** (list): 图像方差，默认为[0.229, 0.224, 0.225]。
* **random_distort**(bool): 数据增强，是否在训练过程中随机扰动图像，仅在mode为'train'时生效，默认为True。底层实现采用[paddlex.det.transforms.RandomDistort](#randomdistort)
* **random_expand**(bool): 数据增强，是否在训练过程随机扩张图像，仅在mode为'train'时生效，默认为True。底层实现采用[paddlex.det.transforms.RandomExpand](#randomexpand)
* **random_crop**(bool): 数据增强，是否在训练过程中随机裁剪图像，仅在mode为'train'时生效，默认为True。底层实现采用[paddlex.det.transforms.RandomCrop](#randomcrop)
* **random_horizontal_flip**(bool): 数据增强，是否在训练过程中随机水平翻转图像，仅在mode为'train'时生效，默认为True。底层实现采用[paddlex.det.transforms.RandomHorizontalFlip](#randomhorizontalflip)

### 添加数据增强方式
```python
ComposedYOLOv3Transforms.add_augmenters(augmenters)
```
> **参数**
> * **augmenters**(list): 数据增强方式列表

#### 使用示例
```
import paddlex as pdx
from paddlex.det import transforms
train_transforms = transforms.ComposedYOLOv3Transforms(mode='train', shape=[480, 480])
eval_transforms = transforms.ComposedYOLOv3Transforms(mode='eval', shape=[480, 480])

# 添加数据增强
import imgaug.augmenters as iaa
train_transforms.add_augmenters([
			iaa.blur.GaussianBlur(sigma=(0.0, 3.0))
])
```
上面代码等价于
```
import paddlex as pdx
from paddlex.det import transforms
train_transforms = transforms.Composed([
		iaa.blur.GaussianBlur(sigma=(0.0, 3.0)),
		# 上面为通过add_augmenters额外添加的数据增强方式
        transforms.MixupImage(mixup_epoch=250),
        transforms.RandomDistort(),
        transforms.RandomExpand(),
        transforms.RandomCrop(),
        transforms.Resize(target_size=480, interp='RANDOM'),
        transforms.RandomHorizontalFlip(prob=0.5),
        transforms.Normalize()
])
eval_transforms = transforms.Composed([
        transforms.Resize(target_size=480, interp='CUBIC'),
		transforms.Normalize()
])
```
-->
