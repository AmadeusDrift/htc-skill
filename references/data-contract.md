# 数据约定

`assets/trial-example.json` 是明确虚构的干跑示例，不是用户商品。真实任务复制结构后替换事实，不沿用示例卖点。`scripts/validate.py` 只读 JSON，不改输入。

## listing.json

- `product.id/type/marketplace/language`：内部编号、类型、站点、语言；无需 ASIN。
- `product.facts`：`id/text/confirmed`；每个事实的确认独立，不用一个总开关代替所有事实核实。
- `product.print_region`：`confirmed/description`；人已确认区域，制作 PSD 前再换算为最终画布像素。
- `rules.title_max`：已选站点/类目的标题上限；`rules.title_source` 记录依据。
- `rules.bullet_max/description_max`：类目硬上限未知则 null；`bullet_target/description_target` 仅为编辑目标。
- `rules.image_policy_status`：`user_requested_pending_verification` 或 `verified_for_category`；后者必须有官方来源/用户提供的后台依据 `image_policy_source`。
- `listing.title/bullets/description/fact_ids`：文案字段及使用的已确认事实；fact_ids 不证明每句语义正确，另行对照审查。
- `gallery`：3 或 4 项，每项含 `id/role/overlay_text/fact_ids`；第一项 scene 且 overlay_text 为 []。素材路径、最终提示词和版本可在每项中增加。

检查输出区分 errors、warnings 和 counts；即便无错误也只给 `MECHANICAL_PASS_REVIEW_REQUIRED`，不表示官方认证、发布许可或图片真实质量已经验证。

## 单张简单 PSD 的 JSON

```json
{
  "base_path": "C:/work/P001-01-clean.png",
  "artwork_path": "C:/work/print-normalized.png",
  "output_path": "C:/work/P001-01.psd",
  "region": {"x": 400, "y": 500, "width": 600, "height": 700}
}
```

路径为存在的本地文件，输出不得已存在。base 必须是无旧印花的完整固定画面，region 为人确认的最终画布矩形，正数宽高且完全在画布内。工具使用 contain 等比完整显示，不拉伸。需要透视/不规则裁切的产品在 Photoshop 小样中另行处理，不假称矩形脚本能自动适配。

## 阶段和下游

图文 draft → 用户确认 exact PNG/文案版本 → PSD → 单张试换 → 交独立工具/运营。不要自动处理1000图或提交商品。交付时记录产品编号、图案编号、图文版本与 PSD 路径，支持下游一一对应。
