# Photoshop 母版与固定替换

## 结构由真实画面决定

- `FIXED_SCENE`：最初生成／准备的无印花实物和场景。正式叠加文字保留独立原生文字层。
- `PRINT_ARTWORK`：嵌入式智能对象，统一源画布；在母版阶段设定位置、必要的摄影透视／曲面变形和区域蒙版。
- 前景层或遮挡蒙版：用于真正跨入印花面的手指、挂带、五金等。没有交叉时不强行添加，记录依据。
- `SURFACE_LIGHTING` 或等效处理：保留真实光影，不引入首款图案。透明印花要能露出原产品底色。
- 主题文字：独立可编辑层；工具若只支持印花替换，就使用共用文案，或明确扩展支持后再变更主题字段。

不要求拆分全部背景；纯通用图不必制造无用印花层。初期编辑同一母版属于设计，后续按图案重做母版属于错误路径。先完成正式排版和第一套视觉审核，再冻结SHA256。

## 当前固定脚本能力

使用环境报告中的PowerShell。下面的 `pwsh` 仅为命令示例，不硬编码用户机器路径。

```powershell
pwsh -NoProfile -File scripts/photoshop.ps1 -Mode Probe
pwsh -NoProfile -File scripts/photoshop.ps1 -Mode Build -SpecPath build.json
pwsh -NoProfile -File scripts/photoshop.ps1 -Mode Inspect -DocumentPath template.psd
pwsh -NoProfile -File scripts/photoshop.ps1 -Mode TrialReplace -SpecPath replace.json
```

`Build` 仅创建无印花底图加矩形位置的智能对象，不会自动识别产品区域、创建蒙版、遮挡、透视或文字版式。复杂模板由AI通过当前受支持的原生Photoshop代码／接口构建并真实检查；不是让用户指出所有问题。不要把两层技术小样当完整产品模板。

`Inspect` 检查顶层 `PRINT_ARTWORK` 的智能对象类型、图层名与边界；它自身不完整检查蒙版／变形／字体，必要时另做原生只读检查，保存证据。

`TrialReplace` 在副本中用 `placedLayerReplaceContents` 替换已有智能对象，导出PNG后关闭副本，不保存模板。母版已有的蒙版、透视和前景可保留，实际可用范围由真实模板测试决定；不要因为Build仅矩形就把所有已验证商品模板一律说成不可用。也不能把单模板替换说成通用图库／随机抽样工具。

替换输入：

```json
{
  "template_path": "C:/work/templates/product-01.psd",
  "artwork_path": "C:/work/artwork/A002-normalized.png",
  "preview_path": "C:/work/variants/A002/01.png"
}
```

候选图必须与智能对象源画布相同尺寸。图案在同尺寸源画布内等比排布；文字／透明款留安全边距，满覆盖规则单独声明，摄影平面的变换固定在母版上。1600×1600 是本次P002的已验证选择，不强制所有产品同尺寸。

脚本有输入和输出存在性检查，不覆盖已有输出，不关闭用户文档，不永久修改偏好。可由宿主按保存的规格顺序调用同一固定入口；调度清单不替代替换实现，不得临时重写换图算法来伪装固定工具验收。

## 权限与故障

沙盒内COM曾报 `0x80080005 CO_E_SERVER_EXEC_FAILURE`，正常桌面权限可连接Photoshop 26.0.0。用宿主审批机制处理，不解释成未安装；冷启动保留合理等待，不并发重复启动。旧Windows PowerShell可能因执行策略拒绝脚本，使用报告里已经可执行的PowerShell 7；不改执行策略、不用Bypass、不改注册表、不安装大型应用绕过。

仅关闭本次打开的工作副本，偏好在finally恢复；先从文档跟踪列表移除自己即将关闭的对象，再关闭，避免访问失效的Photoshop宿主对象。不要用恢复偏好的异常掩盖原始错误。保留原始错误和当前成果。

## 验收范围

按 [production-workflow.md](production-workflow.md) 记录真实蒙版、满覆盖、透明、比例、遮挡和重复导出，冻结前后哈希不变。对视觉、工具和平台分别给结论；机械通过不表示图片能卖货。P002的具体经验只放交接记录，不能把其圆形蒙版和视角泛化到其他商品。
