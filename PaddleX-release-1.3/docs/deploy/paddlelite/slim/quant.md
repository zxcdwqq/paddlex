# 模型量化

为了更好地满足端侧部署场景下低内存带宽、低功耗、低计算资源占用以及低模型存储等需求，PaddleX通过集成PaddleSlim来实现模型量化功能，进一步提升Paddle Lite端侧部署性能。

## 原理介绍
定点量化使用更少的比特数（如8-bit、3-bit、2-bit等）表示神经网络的权重和激活值，从而加速模型推理速度。PaddleX提供了训练后量化技术，其原理可参见[训练后量化原理](https://paddlepaddle.github.io/PaddleSlim/algo/algo.html#id14)，该量化使用KL散度确定量化比例因子，将FP32模型转成INT8模型，且不需要重新训练，可以快速得到量化模型。

## 使用PaddleX量化模型
PaddleX提供了`export_quant_model`接口，让用户以接口的形式对训练后的模型进行量化。点击查看[量化接口使用文档](../../../apis/slim.md)。

## 量化性能对比
模型量化后的性能对比指标请查阅[PaddleSlim模型库](https://paddlepaddle.github.io/PaddleSlim/model_zoo.html)
