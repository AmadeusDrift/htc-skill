# Photoshop 母稿、画布与验证

本文件提供制作约束与已验证的原生操作方法，不附带某个商品PSD或承诺所有服装曲面均自动通过。需要本机 Photoshop、PowerShell；图像差异检查可使用 Pillow。发现依赖不可用时保留已有成果，准确报告受影响部分。

## 先清洁底图，再映射印花

先按[白胚与视觉质量](visual-quality.md)生成或复用无旧印花残留的清洁场景，完成景深与姿势检查，再映射独立母稿。清洁底图可以是实际黑色等衣色，白胚不是强制白衣。已批准成图只修授权范围；不在已印花背景上再盖新图案冒充可替换样机。

## 结构与保存格式

- 根级隐藏嵌入式智能对象“母稿”；顶层数字场景组1…N，实例名PRINT_1等仅为识别辅助。
- 每个PRINT实例从同一个母稿正常复制。检查实际共享ID，不把独立置入同名图层算作同源。固定场景底图可为嵌入式PNG对象，这不等于母稿也允许PNG容器。
- 母稿的实际内容文件是分层PSD或PSB，带透明背景和可隐藏/删除的示例图层。输入图案可以是PNG，须作为PSD/PSB内的图层置入；新增图层后普通“保存”能更新主样机。
- 若旧母稿打开后是PNG，先保留当前新增图层，不强行关闭或要求用户先丢弃。将内容保存成支持分层的PSD/PSB，安全建立新共享母稿并保持所有实例的变换、蒙版、滤镜及对应关系；不能只改后缀、改显示名称，或修好一个实例而切断其他联动。
- 不能用“新建通过拷贝的智能对象”来复制需要联动的实例。
- 将PNG直接通过“替换内容”换入根级母稿，可能把保存容器重新变成PNG。自动换图优先打开内嵌PSD/PSB，在其中更新图层后保存；若借用其他运行工具，先读实现并确认此点，不盲用旧PNG替换入口。
- 主样机采用嵌入式源时，直接编辑外部备份“共享印花源.psd”不会自动更新主样机；说明中应让用户双击主样机内的母稿缩略图。

### 旧PNG母稿的修复顺序

先记录全部实例的共享ID、完整画布变换、蒙版与滤镜，并保护当前内嵌窗口尚未保存的新增内容。将这些内容另存为同像素、同PPI的分层PSD/PSB副本，原内容未保存成功前不关闭。再在主样机副本中，让共享母稿引用该分层副本；核对所有实例仍共享、变换/滤镜/蒙版未变，随后执行下方完整保存回归。

这是一份修复操作约束，不是自动迁移工具。若替换内容改变了实例映射或共享关系，应依据先前记录修复并验证，不能只修改文件后缀或仅修复一个图位就宣告完成。

## 完整画布定位

母稿像素/PPI取实际文档，不能从商品厘米推断。1000×1250px/300PPI只是一个已用配置，不是所有模板的生产标准。选择并记录canvas/contain、canvas/cover或alpha/contain；保留设计留白通常采用canvas/contain，只有明确需要按非透明边界适配才选择alpha/contain。

透明图层的layer.bounds是可见内容边界，不能当作智能对象完整画布矩形。否则小图案或带留白的PNG会被拉大，所有图位的比例也会偏。下面函数在**尚未做目标映射的正常复制实例**上读取smartObjectMore.transform完整画布，供四角映射使用；它不是对已经透视/变形实例的无损重映射工具。

```javascript
function mapCanvasQuad(layer, quad) {
    if (!quad || quad.length !== 8) throw Error("Expected four corner pairs");
    for (var q = 0; q < quad.length; q++) {
        if (typeof quad[q] !== "number" || !isFinite(quad[q])) throw Error("Invalid corner");
    }
    // 调用前使目标文档处于活动状态；显式选中被映射实例，避免读A变换B。
    app.activeDocument.activeLayer = layer;
    var ref = new ActionReference();
    ref.putIdentifier(charIDToTypeID("Lyr "), layer.id);
    var more = executeActionGet(ref).getObjectValue(stringIDToTypeID("smartObjectMore"));
    var transform = more.getList(stringIDToTypeID("transform"));
    var xs = [], ys = [];
    for (var i = 0; i < 8; i += 2) {
        xs.push(transform.getDouble(i));
        ys.push(transform.getDouble(i + 1));
    }
    var box = [Math.min.apply(null, xs), Math.min.apply(null, ys),
               Math.max.apply(null, xs), Math.max.apply(null, ys)];
    var action = new ActionDescriptor(), target = new ActionReference();
    target.putEnumerated(charIDToTypeID("Lyr "), charIDToTypeID("Ordn"), charIDToTypeID("Trgt"));
    action.putReference(charIDToTypeID("null"), target);
    var rect = new ActionList(), points = new ActionList();
    for (var j = 0; j < 4; j++) rect.putDouble(box[j]);
    for (var k = 0; k < 8; k++) points.putDouble(quad[k]);
    action.putList(stringIDToTypeID("rectangle"), rect);
    action.putList(stringIDToTypeID("quadrilateral"), points);
    executeAction(charIDToTypeID("Trnf"), action, DialogModes.NO);
}
```

该画布定位方法来自实际透明分层母稿的修复经验；技能包不包含原商品产物，历史结果不构成当前模板的验收。新模板仍须检查源画布、映射和可见区域。服装曲面、抬手或坐姿的非平面变形仍需额外处理，不能把四角函数称为通用曲面建模。

底图置入可能有半像素边界或受PPI缩放。根据目标画布显式定位并检查完整边界，不能只因浮点差就断言素材尺寸错误；也不能把错误比例强行拉伸成正确外观。

## 褶皱、遮挡与颜色

用场景本身的布料明暗建立轻微置换，按衣身视角制作变形；图案中轴与衣服中轴、领口、胸线保持合理关系，不能整体旋转模拟褶皱。布纹融合用适量局部光影，不把浅色和彩色印花在黑衣上一律设为MULTIPLY。

保护真实前景与衣服边界：手、书、包带、头发、袖子、衣摆外侧和裤子不得染色。蒙版不能为“技术检查通过”随意切掉图案内容；有真实遮挡时关键文字/主体位置需另检查或调整该场景。满版底部在坐姿场景可能受遮挡，不能承诺任意图案无裁切。

清洁底图先去除旧示例印花，同时保留人物、场景、文案和构图；生成工具误删标题或改脸/手时先修好再建母版。共用材质/版型细节无需为“去旧印花”整件擦白胚。

## 原生流程与隔离

Inspect、manifest、plan、Export在这里是检查、登记、配置与导出的阶段名称，不是本技能自带的可执行命令。使用当前环境的原生脚本或已安装工具实现，分别保存输入配置、检查结果、输出清单与错误报告。若借用通用POD运行工具，先检查其PNG母稿替换和透明边界实现，不能假设已包含本文件的修正。

1. Inspect读取8/7/其他实际图数、共享实例、蒙版、母稿像素/PPI和内容文件格式；manifest保存实际值与哈希，不依赖缺值72PPI兜底。
2. 准备映射/母稿后制作候选；所有可见实例纳入，不用固定五实例替代检查。
3. plan根据声明配置新输出目录；Export在副本工作；交付检查核对图数、来源和哈希。
4. 将母稿设为隐藏的操作应在最后选中图层之后执行：Photoshop脚本选中图层可能使其自动显示。
5. 使用同一进程互斥锁串行运行PS任务，例如Local\Codex-POD-Photoshop。原始文件若有未保存的打开文档，不拿磁盘哈希冒称正在编辑的状态；先保护当前内容，改用明确保存的副本。
6. 保存输入、输出和报告路径；修订使用新文件，不默认覆盖已批准母版。不要结束PS进程、强制关文档、改安全策略、注册表或安装设置以处理COM失败。
7. 用户禁止Computer Use时完全不调用它。COM忙/系统错误有限重试并报告实际状态；权限审核超时不等于操作危险，按工具重试指示和现有授权执行，不能无穷重试或把审批失败说成PS未安装。

## 必须分开记录的验收

### 分层母稿保存回归

在测试副本中打开根级母稿，记录实际PSD/PSB文件身份与原图层数；置入新PNG或增加图层，使用原生document.save()（与Ctrl+S相同保存操作）后返回主样机；再打开母稿，核对格式仍为PSD/PSB、图层保留。

导出所有场景做像素差：所有声明的印花图位应变化；0实例图位必须不变；变化范围须在合法印区/遮挡蒙版内。检查实例ID、数量、PPI未变。没实际按键时不要声称做过Computer Use键盘操作。

### 图案边界与比例

至少使用适合该模板的满画布边框、带透明留白的图案、宽/高比例代表图案。按声明场景全部导出时才统计为完整套数；只测一图不能写成一套。检查重要内容裁切、白边、旧印花残留、所有实例、光影融合和保护区域。导出脚本成功、单元测试成功和视觉通过分别报告。

### 修订与交付

改尺寸图时确认其他图位像素不变，母稿结构/身份不变；PS失败则只能报告单图完成。只有用户批准后冻结视觉与模板哈希。文件、原生保存与像素检查不能代替实物、平台或用户视觉验收。

用户换图方法：打开主PSD → 双击根级“母稿”缩略图 → 放入新印花，隐藏示例层 → Ctrl+S → 关闭母稿标签返回主样机；必要时把主样机另存新版本。保存源图、PSD、图位清单、manifest、报告和预览，按范围交付，不默认压缩。

## 四边白边的诊断与最小修复

先看原始底图是否已经有白边，再查主PSD的底图X/Y坐标、缩放/PPI、变换矩阵和实际覆盖范围，逐边检查上、下、左、右。比如底图向右偏1px，会左边漏底、右边裁1px；应先修坐标，不能默认放大、裁切或把整套图案移动。

比较修复导出的第一/最后行列和源底图相应像素，检查四角、画幅与完整内容；分清画布漏底、抠图白色杂边、印花alpha白晕，按实际原因处理。只在副本修复，保护未保存原文档，核对其他图位及印花映射未受影响。

最终图导出后的写实AI人物标签按[元数据规则](ai-person-metadata.md)独立处理，跨图位不得继承错误人物标签。新导出文件即使像素无改动也要重新读回验证XMP。
