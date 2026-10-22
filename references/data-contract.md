# 数据、审核与交付清单

## listing.json：图文与设计决策

新任务使用 `schema_version="0.4"`，要求视觉策略完整。省略版本只作为旧数据兼容并给出警告，不能称为新设计门槛通过。`validation_stage=product-info` 只检查资料，`gallery` 检查默认七图规划。`scripts/validate.py` 返回 `MECHANICAL_PASS_REVIEW_REQUIRED`，不验证图片美感、真实批准、PSD能力或平台合规。

- `product.id/type/marketplace/language`、`facts[{id,text,confirmed,source}]`：实物与用户确认事实。`print_region.description` 记录视觉位置；人工确认用 `confirmed=true`，明确委托用 `placement_review={status:"delegated",evidence:"用户原话"}`，无须伪造人工确认。`manufacturing_confirmed` 另记实际加工确认，不由视觉委托推定。
- `listing.title/bullets/fact_ids`：标题、恰好五点和事实引用；`description` 按需。中文摘要／参数放 `product.summary_zh` 与事实表。
- `rules.title_max/title_source`：声明使用的限制及依据，未核实平台政策时不得把编辑目标说成官方限制。`bullet_max/description_max` 未知可为null。`image_policy_status` 仍单独记录。
- `gallery`：默认每套七个图位，共用图计入这七项。每项 `id/role/overlay_text/overlay_text_zh/fact_ids/reuse_scope`。首项 `role=scene`、`overlay_text=[]`。其余可选 benefit/function/detail/size/scene/use/comparison/structure-size/tips，角色和顺序随产品变化。
- `gallery_strategy`：新规划填写 `buyer_profile/core_buying_reason/visual_direction`；每图补 `buyer_question/composition/reuse_scope`。校验器检查这些声明完整及中英文条数，不替代视觉审核。
- `images_per_set` 默认7；用户明确改规模时同时填写 `images_per_set_source`。此字段与delivery清单对应，不能为了缺图自行减少规模。
- `gallery[].blank_path/printed_path/psd_path/template_spec`：适用图位双PNG与PSD、源画布、印花区域、蒙版、前景、光影、变形和主题字段。通用图用 `asset_path`。
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
    "template_hashes": {"templates/product-01.psd": "记录实际64位SHA256"}
  }
}
```

`approved` 需要对应整套最终图版本和批准依据；`delegated` 表示用户允许不暂停且AI已视觉自查，不等于用户看过。示例中的哈希文字不是可执行数据，必须填真实值。已冻结则必须采用 `smart-object-only`。用户后续批准不得反向伪造之前的审核。

`workflow.stage` 可记录 `design_draft / first_set_ready / frozen / variants_exported / verified_for_declared_templates`；`workflow.template_state` 仅为 `draft` 或 `frozen`。进入冻结及之后阶段必须保留 `template_state=frozen` 并接受审核／哈希／固定换图检查，不能把后期阶段名塞入模板状态绕过验证。失败项另具体标注 `tool_validation_pending`。范围未知不妨碍报告已完成的有限模板导出，但不得声称通用能力或平台验收。

## delivery.json：已有文件的快速交付

交付工具只读源图与PSD，不创建模板或替换图案。清单路径相对清单所在的产品目录，禁止逃出该目录；输出另由 `--out` 显式指定。模板哈希是冻结时记录的值，不在交付时把当前文件重新算成“原始基线”。

```json
{
  "product_id": "P002",
  "canvas": [2000, 2000],
  "images_per_set": 7,
  "slots": [{"id": "01", "role": "scene"}, {"id": "02", "role": "benefit"}, {"id": "03", "role": "function"}, {"id": "04", "role": "detail"}, {"id": "05", "role": "size"}, {"id": "06", "role": "scene"}, {"id": "07", "role": "use"}],
  "shared_images": {"03": "shared/03.png", "05": "shared/05.png"},
  "variants": [{"id": "A001", "images": {"01": "variants/A001/01.png", "02": "variants/A001/02.png", "04": "variants/A001/04.png", "06": "variants/A001/06.png", "07": "variants/A001/07.png"}}],
  "templates": []
}
```

把所有实际款式加入 `variants`。`shared_images` 自动补齐每款；也可每款完整列七条。`templates` 可填 `{path,sha256}` 来验证冻结；空列表仅表示没有用本工具核验PSD，不能据此声称模板通过。`images_per_set` 只在用户改变交付规模时更改，默认七。

工具输出只保证文件、尺寸、完整套数和已声明哈希。源PNG／JPEG可用，打包保留原字节及扩展名，不隐式转码。四宫格对现有图位逐像素排布，总览可缩略，但均不改源图；导出素材是否好看仍由视觉检查与用户判断。
