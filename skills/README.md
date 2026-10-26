# 产品专用 Listing Skills

四个 skill 同仓库维护、分别安装；每个目录包含完整资源，执行时按相应 `SKILL.md` 使用。根目录的 `pod-haul-listing` 仍是原有独立入口。

## 安装

克隆本私有仓库需要具有读取权限的 GitHub 账号。安装工具如支持 GitHub 子目录，选择 `skills/<skill-name>`；不要把整个 `skills/` 当成一个 skill。

手动安装时，将需要的完整目录复制到自己的 Codex skills 目录，例如：

```text
<Codex skills 目录>/pod-canvas-print-listing/SKILL.md
<Codex skills 目录>/pod-heart-ceramic-listing/SKILL.md
<Codex skills 目录>/pod-pvc-scroll-listing/SKILL.md
<Codex skills 目录>/pod-wood-hanger-listing/SKILL.md
```

已有同名安装时先比较、备份，再有选择地同步，避免直接覆盖本地修改。安装完成后在 Codex 中使用对应 `$skill-name`。本次上传不改动个人已安装副本。

## 资源与来源

每个 skill 的 `assets/references/` 保留其明确引用的产品与尺寸参考图，属于运行所需资源。未包含实际商品成图、生产 PSD、缓存或本机运行环境。脚本来自本地 `pod-haul-listing` 0.9.0 的独立副本，来源与脚本哈希见各自 `references/provenance.json`；上传时仅将其中的个人绝对路径替换为仓库来源地址，其余源文件按哈希核对。

各 skill 的 `LICENSE` 随目录保留；第三方供应商参考图的权利归原权利人，不因代码许可而获得额外转授权。

## 验证边界

可在安装有 Pillow 的 Python 环境中，进入任一 skill 目录执行：

```powershell
python -X utf8 -m unittest discover -s tests -v
python -X utf8 scripts/validate_project.py assets/project-example.json --stage plan
```

单元测试和示例计划只验证程序行为与声明结构，不代表实际商品图片、Photoshop 替换效果或平台上架审核通过。商品执行仍须遵守各 skill 的独立产品规则。

2026-10-26 上传验证：四份 skill 格式检查、四份示例计划及各 21 项交付测试（共 84 项）通过；86 个源文件核对完成，除来源路径匿名化外均与本机安装副本哈希一致，50 个内部相对链接有效，JSON 与 Python 语法检查通过。测试临时目录设在工作区，以避开沙盒系统临时目录的权限限制。未调用图片生成或真实 Photoshop 生产。
