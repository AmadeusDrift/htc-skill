# 文件落位、完整套数与工具

一个产品一个根目录，一个印花一个SKU。心形/两种挂画的SKU内直接放完整七/八张、印花.png、文案.txt、总览.jpg；通用图允许每SKU复制一份。帆布同一印花SKU内设60x30与100x38尺寸子目录，每个子目录有完整七图、该尺寸规范印花.png、完整文案.txt、总览.jpg，不把两个比例交成一套七图，也不拆成两个不同印花SKU。

所有需要换印花的PSD直接放产品根目录，以“规格组-图位.psd”区分，如60x30-01.psd、100x38-01.psd、three-sizes-05.psd；不按SKU复制PSD，不设templates一级目录，不为可编辑文字另建PSD。根目录可有纯材质无印花PSD但不强制制造，数量取决于真实可换区域。

原始资料放工作参考；方案、listing.json、生产记录、校验日志放工作资料；候选底图和必要测试放工作资料/中间产物；预览缓存放工作资料/预览缓存。正式图直接导出到SKU或帆布规格目录，不另复制到delivery/variants/scene-variants。已有图片和PSD不因skill更新自动迁移、删除或返工。

## 清单与检查
产品全局listing.json按[data-contract.md](data-contract.md)管理。每个规格套另建delivery-规格组.json，例如工作资料/delivery-60x30.json；project_root=".."，images_per_set显式7或8，slots列01—07或01—08。多规格同套的挂画只建一份八图清单。每个variant代表同印花SKU在该套的导出任务，images逐项列该SKU内成图路径，templates记录本套实际PSD路径和真实冻结SHA256。

```powershell
python <skill>/scripts/validate_project.py <product>/工作资料/listing.json --stage plan
python <skill>/scripts/validate_project.py <product>/工作资料/listing.json --stage files
python <skill>/scripts/gallery_delivery.py inspect <product>/工作资料/delivery-three-sizes.json
python <skill>/scripts/gallery_delivery.py overview <product>/工作资料/delivery-three-sizes.json --variant A001 --out <product>/A001/总览.jpg
```

validate_project按本skill档案检查尺寸组、图位、印花实例/PSD映射、文案结构及阶段证据；files另检查实际成图、PNG印花、文案、总览、PSD文件头及冻结哈希。其机械通过不证明智能对象类型、替换效果、印花授权、美感或平台合规；真实PS及视觉验收独立完成。

gallery_delivery是原成熟工具的本地独立副本，images_per_set可配置7/8；inspect检查画布像素尺寸、图位映射和所声明PSD哈希，不检查文字可读性或替换效果；完整SKU附加文件由validate_project/files及人工核对。overview可先于files阶段生成，再执行最终完整检查。输入变化拒绝覆盖旧预览时用新版本路径。

## 总览与按需打包
先交可见总览与直达文件链接。只要某图位四宫格时直接组合已导出图；“四款合一”未指图位默认01。grid每格最长边≤1000px，压缩JPG≤2MiB，并检查手机文字。多宫格细节04与交付四宫格是不同用途。

默认不ZIP，仅明确请求才pack。gallery_delivery pack仅打包清单中成图，按7或8动态读取，不自动包含PSD、印花、文案或总览；图片包不称完整资料包。要求全资料包时按实际文件范围另行打包并检查成员/CRC/哈希，不生成解压副本或重复总包分包。
