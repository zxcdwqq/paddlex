import numpy as np
from PIL import Image

import paddlex as pdx

model_dir = "l8sparcs_remote_model/"
img_file = "dataset/remote_sensing_seg/data/LC80150242014146LGN00_23_data.tif"
label_file = "dataset/remote_sensing_seg/mask/LC80150242014146LGN00_23_mask.png"
color = [255, 255, 255, 0, 0, 0, 255, 255, 0, 255, 0, 0, 150, 150, 150]

# 预测并可视化预测结果
model = pdx.load_model(model_dir)
pred = model.predict(img_file)
#pred = model.overlap_tile_predict(img_file, tile_size=[512, 512], pad_size=[64, 64], batch_size=32)
pdx.seg.visualize(
    img_file, pred, weight=0., save_dir='./output/pred', color=color)

# 可视化标注文件
label = np.asarray(Image.open(label_file))
pred = {'label_map': label}
pdx.seg.visualize(
    img_file, pred, weight=0., save_dir='./output/gt', color=color)
