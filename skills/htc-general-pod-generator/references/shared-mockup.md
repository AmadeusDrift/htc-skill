# 联动PSD与工作台调用约定

本参考用于新建联动母版和批量换图。先读取本skill的产品规则及assets/workbench-profile.json；各产品的材质、尺寸、图位、印制工艺和不可印区域不因接口统一而改变。已批准的旧单图PSD不自动移动、删除或合并；旧photoshop.ps1、旧listing清单校验器仍只用于它们声明支持的旧模式。

## 阶段与交付边界

1. 资料与文案：Codex按产品skill整理事实、印花、尺寸、Listing和图片正式文案。
2. 视觉与母版：图片工具完成场景及排版；Codex通过原生PS制作印花映射、精细蒙版、透视、曲面及遮挡。一套确定的规格/构图族集中在一份联动PSD；仅当产品可印面、固定场景或映射不兼容时拆分母版；不同源图比例可按母稿选择适配方式。同源多尺寸可在同一尺寸图中保留多个实例，不能因此强拆成多套。
3. 检查与登记：原生Inspect读取场景、母稿像素/PPI、共享实例及蒙版标记，生成template manifest；候选结构通过不等于商品视觉通过。
4. 适配与渲染：按manifest准备批次配置，统一源像素/PPI，替换共享母稿并导出全部声明图位。
5. 验收与交付：检查贴合、覆盖、受保护区域、固定内容、完整图数及哈希。完整Listing仍需原稿、文案、总览等原有交付，不能把PNG渲染批次称为完整Listing。

本轮不创建工作台界面。工作台后续读取产品配置、模板manifest和运行报告，调用同一组工具，不复制或另写换图算法。

## 母版结构

根级隐藏嵌入式智能对象「母稿」；顶层数字场景组1…N，N从该产品/模板声明读取。图数按用户要求、平台、产品需要和模板声明确定。实例由同一母稿正常复制，ID同源；不能把同名独立置入对象当作联动。每个图位声明实例数，固定通用图显式为0。任何图位如含当前SKU印花都必须接入，多件产品逐个记录。

同一PSD当前运行入口处理一个共享印花源；不同正反印花或独立源通道须另做明确的模板/映射方案，不用同一原稿自动覆盖所有面，也不凭空增加背面印花。

孔洞、五金、接缝、夹持边和前景等按实际产品用精细蒙版保护。满版仅覆盖真实可印面，不能为了消除白边盖过制造上的不可印边。固定场景包含已定稿文字与底色，后续不随SKU重生。

内置Build只是已给定底图与平面四角映射/多边形蒙版的制作辅助，不自动识别产品，也不自动生成心形曲线、孔洞、倒角、曲面或复杂遮挡。复杂结构仍由Codex原生制作并实际验收，导出入口会保留已制作的结构。真实替换未验证的产品，不写为已验证模板。

## 印花适配

manifest.profile分别记录canvas像素、ppi、mode、fit、可选target=[左,上,右,下]。母稿先做也可以；后续生成匹配它的套图专用源，不改原稿或母版映射。manifest 必须显式填写并核对实际 PPI，不依赖合同工具缺值时的 72 PPI 回退。

- canvas+cover：完整画面等比铺满；比例不符时居中裁切并记录cropped，避免预留非设计白边。重要文字/主体可能被切时检查具体布局，不能用满版口径随意丢内容。
- canvas+contain：保留完整构图和设计留白；也用于已排好共同画布、需要保留系列相对大小的图案。
- alpha+contain：明确的透明独立图案按全部非透明内容边界等比定位。保留柔边/阴影，不自动把白底删除、不分拆文字或删除孤立内容。复杂背景或杂点先审核，不猜测设计意图。

规范到PSD母稿实际像素及PPI，不能只统一长宽比，也不固定所有模板为72ppi。相同像素不同PPI会影响置入；输入先规范再替换。放大不恢复清晰度，标准套图源不是印刷文件。

印花可以略出血，蒙版贴合真实可印外沿；边缘略弯用实际轮廓，不能内缩做容错。验收同时查不越界、白底是否完整覆盖；孔洞/五金的原色不是白边缺陷。

## 模板manifest

格式为pod-mockup/1，正式结构见template-manifest.schema.json。必须包括template_id、product_type、psd、sha256、mother、scene_ids、profile、expected_instances_by_scene。源尺寸/PPI和各图位实例数来自原生检查；不能从商品厘米数猜测源像素，不能预设某张固定。

quality_status默认candidate，qa_evidence记录实际原生替换、视觉/覆盖、受保护区域及用户审核/委托依据。登记只完成结构记录，不自动升级为视觉已通过。模板内容变化要新版本并更新哈希；不沿用旧验收冒充新版本通过。

```powershell
& <skill>/scripts/run-mockup.ps1 -Mode Inspect -ConfigPath <project>/工作资料/inspect.json
python <skill>/scripts/mockup_contract.py register --inspection <project>/工作资料/inspect-result.json --psd <project>/母版/产品.psd --id product-v1 --product-type 已确认产品类型 --mode canvas --fit cover --manifest <project>/工作资料/template.manifest.json
```

inspect.json为{"template":"模板绝对路径","mother":"母稿","report":"一个新报告路径"}，可加expected_scene_ids校验实际图数。Inspect在副本中读取；自动生产拒绝读取已有未保存编辑的输入文档，先另存版本，避免哈希对应磁盘而实际拿到未保存状态。

## 批次与输出

```powershell
python <skill>/scripts/mockup_contract.py plan --manifest <project>/工作资料/template.manifest.json --input-dir <印花文件夹> --output-root <全新输出目录> --config <project>/工作资料/batch.json
& <skill>/scripts/run-mockup.ps1 -Mode Export -ConfigPath <project>/工作资料/batch.json
```

多模板重复--manifest参数。每张印花保留真实名称作为目录，非法Windows字符规范化，同名/大小写冲突加稳定后缀；不会把原稿改名。读取输入目录当前层支持的图片，不递归猜测子目录用途。

单模板：输出/印花名称/1.png…N.png。多模板：输出/印花名称/模板名称/1.png…N.png。标准化图和layout.json放输出/_work/模板ID/印花ID，不能混入成品目录。外层export-report.json和progress.jsonl记录完整结果，图片清单以report.outputs为准。

PNG/JPG由format选择。批次配置保持独立路径和稳定ID；输出根目录必须是新目录，不自动覆盖或删除。j.scenes可以重出指定图位，但不能把部分导出称作完整一套。未带新schema的既有画芯配置仍可按原目录模式运行，历史文件不迁移。

每份job携带模板SHA256、expected_scene_ids和逐图实例数；图数不匹配或漏换时记录失败，不静默少导。progress.jsonl包含batch_started、artwork_started、image_exported、artwork_failed、batch_finished及已完成/计划图数。失败保留已输出文件和错误，不标成成功；取消时状态cancelled。

## 并发与运行状态

单台PS的活动文档和偏好是共享状态。采用同一运行工具的skill的run-mockup.ps1共用Local\\Codex-POD-Photoshop互斥锁；工作台可并行做资料、校验、配置等准备，但同一PS的Build/Inspect/Export串行执行。默认忙时返回POD_PS_BUSY并失败退出，工作台排队或用LockTimeoutSeconds等待，不并发重复启动PS。

锁保护合作自动入口，不能阻止用户手工操作PS；批量运行期间避免同时手动编辑目标文档或运行绕过队列的脚本。取消标记为output/cancel.request，或配置cancel_file；在图位/印花之间检查，保留已完成文件，不强杀PS。这里提供互斥和进度接口，不声称已实现多台机器调度或PS并行加速。

JSX中的状态和目录分支使用明确if/else。当前PS宿主已实测嵌套条件表达式与Node行为不同，不能仅凭Node单测宣称取消状态或目录布局正确；这些分支须有宿主实际结果。

## 手动入口与验证

scripts/replace-current-template.jsx用于单张预览：返回主PSD选新图，生成换图副本，匹配实际母稿像素/PPI，整体替换，原文档不保存。可通过一次性MOCKUP_CURRENT_JOB提供mode/fit/target/scenes等参数，参数用后清空。它不是文件夹批量导出的界面；正式批量用plan和Export。

检查源规范化、所有共享实例、所有图位的可见印花、完整边界和真实保护区域；文件可读/哈希不变不能代替视觉或孔洞保护验收。

```powershell
python <skill>/scripts/validate-shared-delivery.py --report <输出>/export-report.json --hashes-before <project>/工作资料/hashes-before.json
```

hashes-before.json为[{"Path":"PSD绝对路径","Hash":"SHA256"}]。检查器按报告声明图数检查完整套数、图像和哈希，不强制七张；部分重出、失败及取消不通过完整交付检查。技术模板只能证明运行机制，不外推任意产品或曲面的商品验收。
