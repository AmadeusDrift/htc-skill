# POD 低价商城 Listing Skill

为 Amazon 低价商城的 POD 产品制作标题、五点、产品详情及轮播图，图文确认后制作可替换印花的简单 PSD。

当前版本：**0.1.1 试用版**。本仓库保存 Skill、提示词流程、输入表及辅助脚本；不是已完成的整套批量制作软件。

## 工作流程

1. 人工提供并确认产品资料、参考照片、示例图案和贴图区域。
2. AI 生成标题、五点、产品详情及 3–4 张轮播图。
3. 人工审核图文，必要时修改，确认同一版本后继续。
4. 按定稿效果制作简单 PSD：固定画面＋印花智能对象。
5. 将素材和文案交给独立批量工具及运营上架。

第一张为无额外叠加文字的场景图，后续 2–3 张展示有依据的卖点、结构/尺寸或必要提示。不含 A+，不负责供应商信息采集、自动判断可贴表面、批量套图工具台或店铺发布。

## 安装

需要支持 SKILL.md 的助手；制作真实图片需要图像生成/编辑工具，PSD 脚本需要 Windows 桌面版 Photoshop。Python 3 用于机械检查，不需要新增第三方 Python 包。

私有仓库仅授权用户可访问。可以让 Codex 的 skill-installer 从本仓库根目录安装；也可以将整个仓库检出到个人 skills 下的 `pod-haul-listing` 目录。目标目录已存在时先比较内容，不覆盖本地改动。

Windows PowerShell 示例：

```powershell
git clone https://github.com/AmadeusDrift/pod-haul-listing.git "$env:USERPROFILE\.codex\skills\pod-haul-listing"
```

安装后在下一轮使用 `$pod-haul-listing`。其他环境应放在其实际支持的 skills 目录中；不要假设本机用户名、盘符或 Photoshop 安装路径相同。

## 首次试用

填写 [产品输入表](assets/product-brief.md)，提供真实照片、示例图案及人工确认的贴图位置。

```text
使用 $pod-haul-listing，根据我提供的产品资料、参考图和已确认贴图区域，
先制作标题、五点、产品详情及3–4张轮播图。
我确认图文后，再制作简单PSD。
```

`assets/trial-example.json` 是虚构的机械测试示例，不可当成真实商品资料或上传文件。缺少事实时省略相关主张或列为待确认，不编造尺寸、材质、功能或注意事项。

## 检查与 Photoshop

在仓库根目录执行：

```powershell
python -m unittest discover -s tests -v
python scripts/validate.py assets/trial-example.json
powershell -NoProfile -File scripts/photoshop.ps1 -Mode Probe
```

机械检查成功状态仍是 `MECHANICAL_PASS_REVIEW_REQUIRED`，不表示文案语义、图片效果、权利归属或平台审核已通过。

PSD 的 Build、Inspect 和单张 TrialReplace 用法见 [简单 PSD](references/simple-psd.md)。脚本不实现整套批量替换，不自动处理颜色变体或弧面透视。模板底图不能残留旧印花；新图案应使用统一画布，保持替换效果稳定。

## 已知验证边界

- 已有 7 项 Python 机械检查用例，并检查过 PowerShell/内嵌 JSX 语法。
- 真实商品的完整图文、PSD 制作与试换尚未验收。此前本地 Photoshop COM 探测返回 `0x80080005`；安装 Photoshop 不等于自动化接口已可用。
- 官方依据及适用范围记录在 [文案与官方依据](references/copy-and-policy.md)，页面摘要核对日期为 2026-10-20。首次用于新站点或类目时应重新核对。
- 五点和描述的类目硬上限未知时保留待核对状态，不把编辑目标当官方限制。
- 场景主图是用户指定的低价商城业务要求；当前未独立核实其对所有 Haul 类目的适用性，需按实际商城后台要求复核。

## 文件说明

| 位置 | 用途 |
|---|---|
| `SKILL.md` | 助手入口和阶段约束 |
| `assets/product-brief.md` | 人工产品资料输入表 |
| `references/` | 官方依据、图像提示词、数据格式和简单 PSD 方法 |
| `scripts/validate.py` | 只读检查 Listing JSON |
| `scripts/photoshop.ps1` | Windows Photoshop 单张制作与检查 |
| `tests/` | 机械检查回归用例 |

不提交产品私有资料、运行产物、凭证、PSD 成品或本机缓存。来源与 MIT 许可见 [来源说明](references/provenance.md) 和 [LICENSE](LICENSE)。
