# 交付、预览与时间

## 先识别用户现在要什么

| 请求 | 最小完成动作 |
|---|---|
| 四套完整轮播图 | 四种图案各七图，共28张；共用图可以是同源，但每套完整 |
| 四个总览 | 每套一张七图总览，直接显示／链接四张，不给四个主图替代 |
| 07号四宫格 | 取四种图案的07成图，直接2×2组合，不调用模型，不重建PSD |
| 批准后直接输出 | 不再调整构图、文字、颜色或印花，仅检查、导出、按需打包 |
| 只换印花 | 校验已冻结母版，用固定智能对象工具替换，不再次调用场景生成 |

默认只准备当前需要的一个总包或指定分包。不要同时重做总包、四分包和多个全材料大包，除非用户确实需要。给可见预览和明确文件链接，说明总数；不要让用户在包含初稿、源图和测试图的目录里找成品。

## 稳定文件结构

```text
product-vN/
  listing.json
  delivery.json
  sources/ artwork/ blank/ templates/ shared/
  variants/A001/01.png ... 07.png
  variants/A002/01.png ... 07.png
  previews/A001-gallery.jpg ...
  previews/07-grid.jpg
  specs/ logs/ qa/
```

共享文件可以由清单映射，打包时完整放入每一套。无须按图案复制PSD：母版共用，PNG分别导出。通用图保留PNG足够，按编辑需求才留PSD。

## 固定交付工具

先按 [data-contract.md](data-contract.md) 保存产品根目录的 `delivery.json`。下面的Python使用环境报告中的隔离解释器（需Pillow），不是硬编码系统路径。

```powershell
python scripts/gallery_delivery.py inspect C:/work/product/delivery.json
python scripts/gallery_delivery.py overview C:/work/product/delivery.json --variant A001 --out C:/work/product/previews/A001-gallery.jpg
python scripts/gallery_delivery.py grid C:/work/product/delivery.json --slot 07 --out C:/work/product/previews/07-grid.jpg
python scripts/gallery_delivery.py pack C:/work/product/delivery.json --out C:/work/product/delivery/complete-sets.zip
```

`pack --variant A001` 只打这一套，`inspect --variant A001` 仅检查这一套；单款检查、打包和总览不被其他款尚未填齐或导出的图位阻断。工具不调用模型、Photoshop或印花替换，不会为总览再做一次设计，便于尽早展示第一套正式成品。

`inspect` 检查每款全图位、文件可读、画布尺寸及已声明的冻结PSD哈希。`grid` 保留源像素排列，四款即2×2。`overview` 生成带图号的缩略总览。预览用 `.inputs.json` 记录有序输入、款式／图位身份与输出哈希；内容和顺序未变才复用。已存在但输入／顺序／输出变化则拒绝覆盖，要求新版本路径；主文件与旁文件均保护清单、源图、模板，已有无主旁文件也不擅自覆盖。

`pack` 保留原文件字节，每款自动包括共用图，ZIP内部统一 `/` 分隔符。校验成员、CRC和源文件哈希；未变的包直接复用，内容不同则拒绝覆盖。它不等于卖点／美感／平台政策审核，也不制造用户批准。正式PSD检查仍按 [simple-psd.md](simple-psd.md)。

## 减少不必要等待

- 母版设计耗时与换图耗时分别说明，进度报告展示已学到的事实，避免一遍遍保证“马上”。
- 首次环境和依赖检查一次，环境指纹及产物未变时复用；不每张图重新启动完整技术小样。
- 用户已有独立清晰印花不重修；已经批准的场景和文字不重做；同一图位合并直接用已导出PNG。
- 底图提示词先为排版留位。不要等生成完再随意贴字；优先展示带正式文字的第一套，避免大量无字中间图引起误解。
- 先自查第一套再冻结，之后只换图；不要导出四套后发现字号和对比度问题再全部返工。
- 批准后避免继续“顺便优化”；检查仅确认版本未被改动。打包不要重复压缩同一大文件群。
