# leavs 公共 APT 软件源

维护交接与排障说明见 [HANDOVER.md](HANDOVER.md)。

统一入口：**https://leavs.github.io/apt/**。这是多个工具共用的公开软件源，源码和构建流程仍放在各自项目仓库。

## 客户端安装

网页提供完整添加软件源步骤和签名指纹。配置一次后，可使用 `sudo apt install <包名>` 安装上架工具，后续使用系统更新升级。

目前已登记 `leavs/Camera` 的 `usb-camera-preview`，支持 Ubuntu 24.04 amd64。索引支持 amd64、arm64 及 all 架构，实际支持以每个软件包为准。

使用原 `https://leavs.github.io/Camera/` 源的用户，可以移除旧源配置后按新网页配置公共源。两者沿用同一签名密钥。

## 发布流程

1. 工具仓库的 Actions 构建 `.deb`，计算 SHA256，并发布到正式 GitHub Release（不是 draft 或 prerelease）。
2. 在本仓库 `packages.json` 中登记公开仓库及允许发布的包名。
3. 本仓库推送、手动触发或每 15 分钟的计划任务，下载各仓库最新正式 Release，校验 SHA256、包名及架构。
4. 为所有工具统一生成 `stable/main` 索引，GPG 签名后部署到 Pages。GitHub 定时任务可能延迟；急需更新时在 Actions 手动运行。

增加工具示例：

```json
{
  "repository": "leavs/another-tool",
  "packages": ["leavs-another-tool"]
}
```

将其加入 `packages.json` 的 `sources` 数组。建议包名加 `leavs-` 前缀。每个 `.deb` 必须附带同名 `.deb.sha256` 文件，格式为 `sha256sum` 的输出。一个 Release 中每个包名/架构组合只能有一个版本；同一包名/架构不能由多个来源重复发布。安装包与仓库中都禁止放入签名私钥。

## 签名和容量

公钥与指纹在 `keys/`。Actions secret `APT_SIGNING_KEY` 保存签名私钥，变量 `APT_SIGNING_FINGERPRINT` 指定指纹。本机备份沿用 `~/.local/share/usb-camera-preview/apt-signing/`。新项目无需持有签名私钥，由此公共仓库统一签名；Camera 原源为了兼容仍保留原签名流程。

Pages 只保留每个工具最新 Release 的包，历史版本保留在各自 GitHub Releases。超过 900 MB 时构建会停止，以预留 Pages 的 1 GB 空间上限；当前托管方案仍受 Pages 每月 100 GB 软带宽限制。规模增长后可迁移对象存储/CDN，并尽量保留软件源地址及密钥。

## 本地构建

需要 Python 3、GitHub CLI、apt-utils、GnuPG，以及签名私钥：

```bash
export GNUPGHOME="$HOME/.local/share/usb-camera-preview/apt-signing"
export APT_SIGNING_FINGERPRINT="$(cat keys/apt-key.fingerprint)"
python3 build_repo.py
```

输出为 `build/site/`，不提交构建产物到 Git。
