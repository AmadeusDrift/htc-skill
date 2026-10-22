# 简单 PSD：重点是可换印花

## 最小结构

- `FIXED_SCENE`：定稿场景、产品和固定文案合成的画面，印花区域已去除旧图案。
- `PRINT_ARTWORK`：嵌入式印花智能对象，固定位置、大小；需要时仅加简单裁切蒙版。

不要求分别制作背景、产品、光影、纹理层。不提供整套批量替换工具台。若斜面/弧面必须做透视，在单个智能对象上设置一次并试换验证；当前矩形构建脚本本身不自动透视。

PNG 是效果参考，不是可逆的分层来源。不要在有旧印花的固定底图上叠新图（透明部分会露旧图）。产品文字和不可覆盖部分以人工标注为准。

## Windows Photoshop 脚本

无需新增 Python 库或 MCP。PowerShell 通过 Photoshop COM 运行 JSX，Photoshop 自己保存原生 PSD。先探测，不用 computer use 模拟点击。

```powershell
powershell -NoProfile -File scripts/photoshop.ps1 -Mode Probe
powershell -NoProfile -File scripts/photoshop.ps1 -Mode Build -SpecPath C:/work/psd-spec.json
powershell -NoProfile -File scripts/photoshop.ps1 -Mode Inspect -DocumentPath C:/work/P001-01.psd
```

`Build` 新开自己的文档，添加固定画面和智能对象，按 region 完整等比放入，保存新 PSD；不覆盖已有文件。`Inspect` 只读打开副本并报告图层，随后关闭自己的文档。不关闭用户文档、不永久修改 Photoshop 偏好；程序临时改动在 finally 恢复。

试换验证使用 `-Mode TrialReplace -SpecPath C:/work/trial-spec.json`：

```json
{
  "template_path": "C:/work/P001-01.psd",
  "artwork_path": "C:/work/another-normalized.png",
  "preview_path": "C:/work/P001-01-trial.png"
}
```

只是单张技术试换：不改模板，不保存替换后的 PSD，仅导出新预览并关闭副本。图案需要先规范为相同画布尺寸与留白；脚本要求候选图像素尺寸与原智能对象源尺寸一致，不把不同尺寸硬塞进去。预览已存在则停止。

## 验收

重新打开 PSD，检查 `PRINT_ARTWORK` 确实为智能对象。用不同配色/内容的同尺寸图案试换，核对位置、比例、清理后的区域、旧印花残留、文字与 PNG 导出。不只凭图层名宣称可替换。

无 Photoshop 或 COM 失败时报告原始类别和已完成部分，不安装第三方 MCP或升级软件来绕过。技术示意样例通过只能证明脚本链路，真实产品仍需单独检查。
