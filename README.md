# UCAS选课监控助手

## 脚本说明
脚本将使用用户提供的用户名与密码登录到SEP平台，在教务选课系统中获取当前学期的所有课程，并开始监控用户所需课程是否尚有名额余量。

## 使用方法
```shell
python main.py 用户名 密码 课程编号1 课程编号2 ...
```
例：
```shell
python main.py zhangsan66@mails.ucas.ac.cn zs_Password 010108MGX006H 030100M07001H-01 0402Z1MGX001H
```

## OCR识别
该项目基于[ddddocr](https://github.com/sml2h3/ddddocr)与[dddd_trainer](https://github.com/sml2h3/dddd_trainer)，并提供已经训练好的OCR模型，参数文件（`jwxk_1.0_505_45500_2023-07-04-10-08-55.onnx`）与字符集配置文件（`charsets_jwxk.json`）位于`ocr`文件夹中。该模型参与训练的样本大小为3000，测试集大小为625，准确率为100%。需要注意的是，实际参与训练与测试的样本均经过如下`transform`函数的变换，函数签名中的`img`为使用[Pillow](https://pypi.org/project/Pillow)库读取的图片，`binary_threshold`为灰度图二值化阈值（实际使用中保持默认值即可）。但由于时间关系，脚本并未集成验证码的自动计算与提交。欢迎提issue与PR。
```python
from PIL import Image

def transform(img: Image.Image, binary_threshold: int = 85) -> Image.Image:
    img = img.convert("L")
    img = img.point(lambda v: 255 if v > binary_threshold else 0)
    try:
        affine = Image.Transform.AFFINE
    except AttributeError:
        affine = Image.AFFINE
    img = img.transform((128, 48), affine, [1, 0.5, 0, 0, 1, 0])
    return img
```