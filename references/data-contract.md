# 数据、审核与交付清单

## 工作资料/listing.json：图文与设计决策

新任务使用 `schema_version="0.4"`，要求视觉策略完整。省略版本只作为旧数据兼容并给出警告，不能称为新设计门槛通过。`validation_stage=product-info` 只检查资料，`gallery` 检查默认七图规划。`scripts/validate.py` 返回 `MECHANICAL_PASS_REVIEW_REQUIRED`，不验证图片美感、真实批准、PSD能力或平台合规。

- `product.id/type/marketplace/language`、`facts[{id,text,confirmed,source}]`：实物与用户确认事实。`print_region.description` 记录视觉位置；人工确认用 `confirmed=true`，明确委托用 `placement_review={status:"delegated",evidence:"用户原话"}`，无须伪造人工确认。`manufacturing_confirmed` 另记实际加工确认，不由视觉委托推定。
- `listing.title/bullets/fact_ids`：标题、恰好五点和事实引用；`description` 默认交付共享产品描述。新任务另填 `title_template={print_phrase,fixed_product_name}`，完整标题必须为两字段去首尾空格后以一个空格连接；固定名称同底板各款一致。旧数据未声明此字段仍可读取，不据此证明已符合新标题标准。中文摘要／参数放 `product.summary_zh` 与事实表。
- `rules.title_max/title_source`：声明使用的限制及依据，未核实平台政策时不得把编辑目标说成官方限制。各`*_max`优先按适用站点／product type官方数值设置；官方未给具体数字或未取得适用数值时按用户TXT兜底：`title_max=125`、`bullet_max=500`（每条）、`description_max=500`（整段），含空格。只对缺失字段兜底，不覆盖已知官方值。另记录`title_source/bullet_source/description_source/limits_checked_at/limit_unit`，兜底来源标记`user_txt_fallback`及原因，不称官方已核实。旧null仍能读取但不再作为新任务默认；本脚本按清单中显式数值校验，不自动判断官方适用范围或把null转换为兜底值。计量为字符时使用本校验器，bytes须另验。`image_policy_status` 仍单独记录。
- `gallery`：默认每套七个图位，共用图计入这七项。每项 `id/role/overlay_text/overlay_text_zh/fact_ids/reuse_scope`。首项 `role=scene`、`overlay_text=[]`。新任务后六项依次为 `benefit/benefit/detail/size/scene/use`，对应产品卖点及完整功能／水晶贴卖点／产品细节／三维尺寸／使用场景／手持质感；两个benefit分别填 `content_focus=product` 和 `content_focus=transfer`。旧角色仍可读取，但不代表新七图内容已核验。
- `gallery_strategy`：新规划填写 `buyer_profile/core_buying_reason/visual_direction`；每图补 `buyer_question/composition/reuse_scope`。校验器检查这些声明完整及中英文条数，不替代视觉审核。
- `images_per_set` 默认7；用户明确改规模时同时填写 `images_per_set_source`。此字段与delivery清单对应，不能为了缺图自行减少规模。
- `gallery[].blank_path/printed_path/psd_path/template_spec`：适用图位双PNG与PSD、源画布、印花区域、蒙版、前景、光影、变形及全部印花对象映射；固定底图已包含图片工具定稿的正式文字，不再声明PS主题文字字段。通用图用 `asset_path`。
- `artwork_library`：原始／修复／规范印花、ID、类型、来源、授权、原生尺寸；随机抽样才记录seed。补绘不称原始像素恢复。
- `tool_contract/template_validation`：实际入口和版本／哈希、规格、日志、画面与像素检查、声明的支持范围，不靠名字声称通过。

新冻结记录示例：

```json
{
  "workflow": {
    "template_state": "frozen",
    "variant_method": "smart-object-only",
    "first_set_review": {
      "status": "delegated",
      "evidence": "用户明确要求本次中间不要暂停",
      "ai_visual_review": true
    },
    "template_hashes": {"01-主图.psd": "记录实际64位SHA256"}
  }
}
```

`approved` 需要对应整套最终图版本和批准依据；`delegated` 表示用户允许不暂停且AI已视觉自查，不等于用户看过。示例中的哈希文字不是可执行数据，必须填真实值。已冻结则必须采用 `smart-object-only`。用户后续批准不得反向伪造之前的审核。

`workflow.stage` 可记录 `design_draft / first_set_ready / frozen / variants_exported / verified_for_declared_templates`；`workflow.template_state` 仅为 `draft` 或 `frozen`。进入冻结及之后阶段必须保留 `template_state=frozen` 并接受审核／哈希／固定换图检查，不能把后期阶段名塞入模板状态绕过验证。失败项另具体标注 `tool_validation_pending`。范围未知不妨碍报告已完成的有限模板导出，但不得声称通用能力或平台验收。

## 工作资料/delivery.json：按SKU读取正式成果

采用[新目录清单示例](../assets/delivery-example.json)，实际保存到产品的工作资料/delivery.json。设`project_root=".."`，所有资源路径相对产品根目录；字段省略时保持旧默认`.`。只允许`.`或`..`，不支持任意祖先路径；资源仍不得逃出选定产品目录。生产不自动迁移任何旧清单。

`preview_cache_dir="工作资料/预览缓存"`使总览机器记录集中到工作资料，而总览.jpg仍放SKU目录；不配置则保留旧旁文件行为。缓存记录以输出绝对路径的哈希命名，输入／顺序／输出都未变化才复用。

`variants[].id`默认是印花SKU编号，`images`显式列该SKU完整七图路径，不以`shared_images`映射代替正式SKU文件；通用图片允许复制到每个SKU。保留旧`shared_images`读取，不默认做去重。PSD仅在产品根目录，`templates[{path,sha256}]`填真实冻结哈希；没有PSD的演示清单空列表不代表PSD验收通过。

`variants[].artwork_path/copy_path/overview_path`记录SKU内印花.png、文案.txt、总览.jpg，额外字段用于生产及交付对应关系；当前inspect仅检查七图和已声明PSD，不自动检查这三个附加文件，完成交付须另对照确认。SKU文案含完整标题、五点及产品描述，不能以“共用文案见别处”代替。

新结构不默认ZIP。当前pack仍只打包清单中的七图，不自动纳入附加文件或PSD；不能把图片包称为全SKU资料包。源PNG／JPEG保留字节和扩展名，不隐式转码。图片质量与真实批准仍需实际审核。

## 新任务的补充生产记录

- `color_variants`：每项包含 `id/artwork_id/base_color/is_primary`；主配色多色组合的每个产品列入01的 `print_instances`（颜色、智能对象名、区域／变换）。一个印花一个SKU，多底色仍归同一SKU；必要的分色导出任务可有不同任务ID但路径都放该SKU颜色子目录，不另建顶层颜色SKU。颜色共用图仅在实物结构与颜色均适用时复用。
- `product.dimensions`：`length/height/thickness`，每项记录 `value/unit/fact_id`，对应05图的三维引线；缺参数不生成虚构数值，不把尺寸验收标通过。
- 03使用 `content_focus=transfer`，5条固定工艺卖点逐条引用确认事实。04用 `detail_panels[{location,description,fact_ids}]` 记录每个宫格的位置与简洁描述；单特写可只一项，最终仍仅04一个文件。
- `gallery[].text_production`：记录图片生成工具与最终图路径；PS仅制作印花PSD。文字、尺寸线和版式问题回图片工具修改，冻结后修订另开版本，不在PS改字。
- 以上补充字段供生产与语义审核，当前校验器仅检查已有字段及显式声明的 `title_template` 拼接；不宣称自动验证三维尺寸、5条工艺卖点、多宫格描述或多对象替换。
- 仓库贴标，不增加第8张DIY图、粘贴示意图或教程视频；不借技能更新修改历史图片／PSD。
