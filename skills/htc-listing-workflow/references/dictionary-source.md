# 词库快照与更新

来源：用户授权只读访问的 https://htcerp.app （Cloudflare Worker `xuanpin`），2026-11-07 提取的 `packages/title-audit/dictionary.json`；扫描核心参考 `US-v0.3-r6`。仅包含词库数据，不包含部署代码、凭据、账户业务数据或生产审查任务。

快照含 32,248 条 `terms` 商标名称/编号记录及 2,418 条 `ip` 品牌/IP名称别名记录。后者不是 2,418 个独立品牌。D1 运营新增词条当次为0；不能误把这看成整库为空。补充词库来自用户的 amazon-title-scanner.zip（389条）。真实条数与哈希以 `assets/dictionary_manifest.json` 为准。

默认使用快照离线运行，不为每批复制整个词库。联网同步是可选维护操作，不是处理每批图片的前提；不可用时明确记录使用的快照，不静默换成小词表或宣称已查最新状态。

更新流程：

1. 通过可用 Cloudflare 连接只读确认域名对应服务，读取指定词库/内置 source map 的 JSON 数据及专门的运营词条；先发现账户/资源，不硬编码凭据。不触发生产 title audit jobs、不改数据库。
2. 只提取 `dictionary.json` 数据，禁止执行整个下载的 Worker 代码。可把返回的 multipart 保存到安全工作区，运行 `scripts/import_dictionary.py --multipart worker.txt --output-directory staging-assets` 提取并校验结构。或先读取 dict JSON 用同脚本 `--dictionary` 检查。词库替换在新目录通过测试后进行，不把新规则直接灌入在途批次。
3. 对比条数、版本、哈希及新增/移除，跑 scanner 回归样例。词库结构变化、关键测试失败或来源不明则保留旧快照，报告差异。
4. 运营自定义词和新平台误识别案例优先保留来源、原因和适用品类。维护本地规则不等同获准写回 ERP；线上修改需用户明确要求。

此技能不是商标实时法律状态查询工具。
