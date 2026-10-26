# POD 商品视觉与智能对象母版

版本 **0.8.3**。用于实物截图／参考资料／印花到商品图文、完整轮播图和可替换PSD；核心是先做好第一套视觉，再冻结母版换印花。不是店铺发布、选品搜索或独立制作工作台。

## 同仓库的四个独立 Listing Skill

原 `pod-haul-listing` 入口保留在仓库根目录。以下四个产品专用 skill 位于 `skills/`，均为 1.0.0，具有独立入口、产品档案、参考图、脚本和许可，可分别安装使用。

| Skill | 产品与默认范围 |
|---|---|
| [pod-canvas-print-listing](skills/pod-canvas-print-listing/SKILL.md) | 卷装无框画芯；60×30、100×38 cm 各一套七图 |
| [pod-heart-ceramic-listing](skills/pod-heart-ceramic-listing/SKILL.md) | 心形陶瓷挂饰；7.4×7×0.3 cm，一套七图 |
| [pod-pvc-scroll-listing](skills/pod-pvc-scroll-listing/SKILL.md) | PVC 挂轴画；20×30、30×45、40×60 cm 共一套八图 |
| [pod-wood-hanger-listing](skills/pod-wood-hanger-listing/SKILL.md) | 实木挂条画；20×30、30×45、40×60 cm 共一套八图 |

这些 skill 源自本地 `pod-haul-listing` 0.9.0 流程，并已包含自己的资源副本，不依赖根目录 skill 的版本或安装。根目录当前仍为远端原有 0.8.3；本次仅新增四个 skill 与安装索引。产品专用规则不继承水晶贴固定 03 的例外。

安装方法与验证范围见 [skills/README.md](skills/README.md)。

## 使用

使用 `$pod-haul-listing`，提供实物截图、用户指定参考、印花与已确认事实。新商品先规划买家、购买理由、场景、通用文案和事实卖点，由图片生成工具完成全部图片文字与排版，PS只制作印花PSD；完成第一套正式七图后审核／按明确委托自行检查，冻结PSD。后续只能替换印花智能对象，不按印花重做场景或PSD。

标题固定为“可变印花词组＋固定产品名称”，五点和产品描述共享；字符限制优先使用适用站点／类目官方数字；官方数值未明确的字段按TXT兜底：标题125、每条五点500、整段描述500字符，均含空格并注明用户兜底来源；已知官方限制不被覆盖。补充附件不覆盖现有事实。

用户说“不要再改”即只输出；“四套”默认四款各七图，共28张，通用图分别补齐。只要总览、指定图位四宫格或打包，直接组合现有成图，不调用imagegen。七图职责固定为场景主图、产品卖点及功能、水晶贴卖点、产品细节、长高厚尺寸、使用场景、手持质感；构图按产品适配。多底色主图同一印花多色展示，其他颜色子体单产品；复杂细节图多宫格逐格配短说明但只占一张。仓库贴标，不增加DIY指引、粘贴示意图或教程视频。已有图片与PSD不动。

入口：[SKILL.md](SKILL.md)。视觉：[gallery-prompts.md](references/gallery-prompts.md)。生产：[production-workflow.md](references/production-workflow.md)。PSD：[simple-psd.md](references/simple-psd.md)。交付：[delivery.md](references/delivery.md)。数据：[data-contract.md](references/data-contract.md)。当前交接：[HANDOFF.md](HANDOFF.md)。

## 03的固定文案与灵活排版

标题为 `UV DTF Transfer`；五点依次为 `3D effect`、`Waterproof`、`Highly adhesive`、`High quality`、`Easy to use`，原文见[固定文案](assets/uv-dtf-copy.json)。这些卖点针对转印贴，不扩张成整个商品的性能承诺。

新制或明确要求优化03时，排版按产品形态、印花焦点与留白自由适配，不固定左右分栏、产品站位或文字范围；标题克制、正文手机可读。仅换印花／仅改文案时保护对应批准构图。仍先生成无印花底板与正式图文，再由PSD贴入印花。哑光／亮面对比页和小窗目前暂停。

尺寸图保留适用的简短标题，三维标尺同时标厘米和英寸，不加重复尺寸汇总或维度英文名；合并预览优先压缩JPG，高清单图保留。

## 文件组织

一个印花一个SKU，SKU目录内放完整七图、印花、完整文案和总览；通用图允许每SKU各存一份。需要替换印花的PSD直接放产品根目录，不设共用模板一级目录。原始资料放工作参考，必要中间产物、清单及路径记录放工作资料；默认不生成压缩包，不额外复制整套交付目录。已有图片、PSD及旧包不迁移、不清理。结构和工具命令见[delivery.md](references/delivery.md)。

## 环境与验证

```powershell
python scripts/check_environment.py
```

入口用标准库定位环境，在 `local/validation-env` 按需隔离安装PyYAML/Pillow，检查PowerShell／Photoshop COM，首次运行PSD技术小样。报告 `local/environment-report.json` 给出实际解释器与shell路径；环境指纹和产物未变则缓存复用。`--check-only` 不安装或生成新PSD，`--full` 强制重测。缓存通过只说明技术链路，不证明真实商品质量。

不修改Windows安全策略／注册表，不用Bypass，不安装大型应用或触碰认证。沙盒COM权限失败走宿主审批；正常桌面Photoshop已经验证可用，不误报为未安装。全程代码／接口，不使用Computer Use。

下面测试用环境报告中的隔离Python运行（Windows通常为 `local/validation-env/Scripts/python.exe`）：

```powershell
python -X utf8 -m unittest discover -s tests -v
python -X utf8 scripts/validate.py assets/trial-example.json
python -X utf8 <skill-creator目录>/scripts/quick_validate.py <本仓库>
```

0.4.0历史49项单元测试覆盖资料验证、环境缓存与文件交付：四套完整图、共用图、指定图位组合、重复产物复用、源路径边界和冻结哈希。单元测试不调用模型／Photoshop；真实P002模板的商品与像素验收另记交接文档。合成例子标为 `example_only`，不是上架资料。

## 当前脚本边界

`photoshop.ps1 Build` 只创建简单矩形智能对象；AI负责原生商品母版的蒙版、前景、透视、必要光影；正式文字和版式全部由图片生成工具完成，PS不改字。`TrialReplace` 可在副本保留已有模板结构，只有经过实际验证的商品／模板范围才报告支持，不宣称通用曲面能力。

`gallery_delivery.py` 只检查、预览与打包已有文件，自动补齐每套共用图；不生成场景、不替换印花、不自动决定图片好看。说明与命令见 [delivery.md](references/delivery.md)。

## 安装与同步

仓库：[AmadeusDrift/pod-haul-listing](https://github.com/AmadeusDrift/pod-haul-listing)（private）。仓库本身可作为技能目录。更新个人已安装副本时先比较并备份，同步技能入口、agents、references、assets、scripts、tests及配套说明／许可；不复制 `.git`、`local`、`runs`、真实商品素材或凭证。仓库提交与本机安装同步分别核对，不把push成功当成安装完成。

真实商品产物放忽略的 `runs/` 或独立产品目录，不提交商品成图、PSD、个人路径、账号信息和缓存。技能明确引用的两张通用构图示例随 `assets/visual-references/` 发布，只作为布局／质感参考。历史政策摘要见 [copy-and-policy.md](references/copy-and-policy.md)，执行真实商品时核实适用站点／类目的当前要求。来源及MIT许可见 [provenance.md](references/provenance.md) 与 [LICENSE](LICENSE)。

## 0.5.0 历史验证

本次修改流程说明、示例和标题拼接校验，运行相关`test_validate.py`共26项通过；虚构七图示例校验无错误，官方五点／描述上限未按具体product type核实的项仍明确警告。未重跑环境／交付测试，未调用图片生成或Photoshop，不把文档更新说成真实商品验收。当前全部测试数量与历史49项不同，具体以本次验证记录为准。

## 0.6.0 历史验证

相关交付测试20项、文案校验26项均通过，共46项；覆盖工作资料中的清单定位、集中预览缓存、路径越界拒绝及原有交付行为。未执行无关环境测试，未调用生成工具／Photoshop，不移动已有商品素材。

## 0.8.3 发布验证

交付21项与文案校验26项，共47项针对性单测通过；固定文案、技能frontmatter／版本、32个本地链接及改动脚本语法检查通过。本轮未生成图片或重跑真实Photoshop成图，已有商品测试范围见HANDOFF。PyYAML未安装，未运行依赖它的quick_validate.py；未安装新依赖。
