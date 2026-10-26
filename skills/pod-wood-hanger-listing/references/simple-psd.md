# 可替换印花PSD与固定工具

## 母版结构与边界
- FIXED_SCENE：已完成正式文字、排版和场景的底图；仅可印区无旧图案。
- PRINT_ARTWORK或带唯一后缀的顶层嵌入式智能对象：每个实际可见印花面均有映射。
- 可编辑精细路径/蒙版：按真实内沿裁切；保护孔洞、挂绳、挂轴、倒角和前景。
- 必要前景与SURFACE_LIGHTING：保持真实遮挡、材质、纹理、阴影和反光，不夹带首款图案。

母版适配以产品档案为准。源图按有效可见内容等比规范，不把任意原图直接塞进智能对象。full_bleed允许适量出血，由蒙版裁切；cutout保留透明与设计留白。不拉伸、不静默切掉文字或重要主体，不用透明画布安全边造成非设计白圈。真实不可印边界不能冒充缺陷而强行覆盖。每个源画布尺寸、有效边界、变换与保护区分别记录。

canvas两个横版比例分别建母版；陶瓷保护心形内沿与孔位；挂画保护上下轴与夹持区。每个图位内重复商品、多个尺寸和细节特写均同步换图。纯通用无当前SKU印花的图不建无用智能对象，03与08没有固定素材豁免。

## 本地工具
使用环境报告中的PowerShell执行以下入口，路径仅为格式示例：
```powershell
pwsh -NoProfile -File <skill>/scripts/photoshop.ps1 -Mode Probe
pwsh -NoProfile -File <skill>/scripts/photoshop.ps1 -Mode Build -SpecPath <product>/工作资料/build.json
pwsh -NoProfile -File <skill>/scripts/photoshop.ps1 -Mode Inspect -DocumentPath <product>/60x30-01.psd
pwsh -NoProfile -File <skill>/scripts/photoshop.ps1 -Mode TrialReplace -SpecPath <product>/工作资料/replace.json
```

Build仅创建矩形技术基础，不自动制作真实产品蒙版、透视、弯曲、遮挡或排版。复杂母版应通过受支持的Photoshop代码/原生接口构建，实际视觉检查；不能拿Build两层小样交商品模板。Inspect检查顶层智能对象名称、类型和边界，不自动证明蒙版或透视正确。

TrialReplace打开工作副本，调用placedLayerReplaceContents，导出PNG后关闭副本，不保存原母版；不覆盖已有输出、不关闭用户文档、不永久改偏好。输入规范源图须与声明源画布一致。多对象提供完整且唯一的顶层print_layer_names；不自动递归嵌套对象，不把第一个替换成功当整图成功。

```json
{
  "template_path": "C:/work/product/three-sizes-05.psd",
  "artwork_path": "C:/work/product/A001/印花.png",
  "preview_path": "C:/work/product/A001/05-尺寸.png",
  "print_layer_names": ["PRINT_ARTWORK_SMALL", "PRINT_ARTWORK_MEDIUM", "PRINT_ARTWORK_LARGE"]
}
```

源图先归一到共同源画布，三规格各自的摄影变换固化在PSD。若画面需要不同源图/正反面，须使用真实支持的固定入口逐项替换并验证，不能声称此同源列表会自动处理不同图案。只为当前声明对象和范围报告可用性。

## 环境
交付前可运行本skill的check_environment.py，使用产品工作目录存环境与测试产物：
```powershell
python <skill>/scripts/check_environment.py --env-dir <product>/工作资料/local/validation-env --output-dir <product>/工作资料/中间产物/environment-smoke
```
脚本会检查依赖、Photoshop连接，缺包时可建隔离环境并按原工具约束安装；有匹配成功缓存时复用，不每张重跑。只读依赖检查可加--check-only，但它仍会探测PS、写报告且不自动运行新小样。已有环境可直接指定，不修改原skill环境。

COM权限或0x80080005按宿主审批机制处理，不直接解释为未安装；不改执行策略、注册表、不用Bypass、不安装大型应用或触碰认证。只关闭本次工作副本；保留原始错误与已有成果。
