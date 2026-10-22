# POD 商品视觉与智能对象母版

版本 **0.4.0**。用于实物截图／参考资料／印花到商品图文、完整轮播图和可替换PSD；核心是先做好第一套视觉，再冻结母版换印花。不是店铺发布、选品搜索或独立制作工作台。

## 使用

使用 `$pod-haul-listing`，提供实物截图、用户指定参考、印花与已确认事实。新商品先规划买家、购买理由、场景、情绪标题、事实卖点和原生排版；完成第一套正式七图后审核／按明确委托自行检查，冻结PSD。后续只能替换智能对象与声明字段，不按印花重做场景或PSD。

用户说“不要再改”即只输出；“四套”默认四款各七图，共28张，通用图分别补齐。只要总览、指定图位四宫格或打包，直接组合现有成图，不调用imagegen。化妆镜七图实例不固定成全品类模板。

入口：[SKILL.md](SKILL.md)。视觉：[gallery-prompts.md](references/gallery-prompts.md)。生产：[production-workflow.md](references/production-workflow.md)。PSD：[simple-psd.md](references/simple-psd.md)。交付：[delivery.md](references/delivery.md)。数据：[data-contract.md](references/data-contract.md)。当前交接：[HANDOFF.md](HANDOFF.md)。

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

当前49项单元测试覆盖资料验证、环境缓存与文件交付：四套完整图、共用图、指定图位组合、重复产物复用、源路径边界和冻结哈希。单元测试不调用模型／Photoshop；真实P002模板的商品与像素验收另记交接文档。合成例子标为 `example_only`，不是上架资料。

## 当前脚本边界

`photoshop.ps1 Build` 只创建简单矩形智能对象；AI负责原生商品母版的蒙版、前景、透视、光影与正式文字。`TrialReplace` 可在副本保留已有模板结构，只有经过实际验证的商品／模板范围才报告支持，不宣称通用曲面能力。

`gallery_delivery.py` 只检查、预览与打包已有文件，自动补齐每套共用图；不生成场景、不替换印花、不自动决定图片好看。说明与命令见 [delivery.md](references/delivery.md)。

## 安装与同步

仓库：[AmadeusDrift/pod-haul-listing](https://github.com/AmadeusDrift/pod-haul-listing)（private）。仓库本身可作为技能目录。更新个人已安装副本时先比较并备份，同步技能入口、agents、references、assets、scripts、tests及配套说明／许可；不复制 `.git`、`local`、`runs`、真实商品素材或凭证。仓库提交与本机安装同步分别核对，不把push成功当成安装完成。

真实产物放忽略的 `runs/` 或独立产品目录，不提交PNG、PSD、个人路径、账号信息和缓存。历史政策摘要见 [copy-and-policy.md](references/copy-and-policy.md)，执行真实商品时核实适用站点／类目的当前要求。来源及MIT许可见 [provenance.md](references/provenance.md) 与 [LICENSE](LICENSE)。
