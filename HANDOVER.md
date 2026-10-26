# 公共 APT 软件源交接

更新日期：2026-10-26。完整项目背景见 Camera 仓库的 `HANDOVER.md`：https://github.com/leavs/Camera/blob/main/HANDOVER.md 。

## 当前状态

- 仓库：https://github.com/leavs/apt （Public，`main`）。
- Pages：https://leavs.github.io/apt/ ，多个工具共用。
- 本地：`/home/ubuntu/Workspace/Codex/apt`。
- 已登记项目：`leavs/Camera`，包名 `usb-camera-preview`。
- 最近验证的线上包：`1.0.1+git2`，Ubuntu 24.04 amd64。
- 云端构建与部署成功；线上公钥、APT 签名、索引、下载及校验和已验证。
- 当前设备尚未把该源写入系统 APT，只做过隔离的临时 APT 验证。

## 文件与工作流

| 文件 | 作用 |
| --- | --- |
| `packages.json` | 允许收录的公开仓库与包名 |
| `build_repo.py` | 下载 Release、校验、生成全部架构索引、签名与首页 |
| `index.html` | 公共首页及客户端安装步骤模板 |
| `keys/apt-key.gpg` / `keys/apt-key.fingerprint` | 公开签名公钥及指纹 |
| `.github/workflows/publish.yml` | 定时、推送、手动触发的统一发布 |

流程每小时第 7、22、37、52 分钟运行；计划任务可能延迟，也可手动触发。读取每个登记仓库的最新正式 GitHub Release，下载 `.deb` 与同名 `.deb.sha256`。检查摘要、包名、架构、重复包后，生成 `stable/main` 的 amd64、arm64 索引（`all` 包计入两个索引），签名并原子部署 Pages。某个来源失败会停止新部署，已上线快照仍可使用。

索引支持某架构不表示每个工具都提供该架构的包。当前 Camera 仅提供 Ubuntu 24.04 amd64 包。

## 增加新工具

1. 在工具自己的公开仓库用 Actions 构建 DEB 并发布正式 Release。不要使用 draft 或 prerelease。
2. 每个 `.deb` 必须提供同名 `.deb.sha256`，内容为 `sha256sum` 输出。包名推荐 `leavs-<工具名>`。
3. 同一 Release 中每个包名/架构组合只能有一个版本；跨仓库不能重复提供同一包名/架构。
4. 将 `{"repository": "leavs/新仓库", "packages": ["leavs-新包名"]}` 加入 `packages.json` 的 `sources`。
5. 提交推送后观察本仓库 Actions，或在来源新 Release 完成后手动运行。
6. 用隔离 APT 配置验证签名、候选版本及实际下载，再测试目标发行版安装启动。

新工具不需要持有软件源私钥，也无需跨仓库写权限。本仓库默认 `GITHUB_TOKEN` 只读，用于读取公开项目 Release。源码仍放在工具各自仓库。

## 签名与密钥

主密钥指纹：`AFA7 A554 83A3 A25D 6B1C EF37 9307 7871 3952 5089`，沿用 Camera 密钥，UID 中仍有 Camera 字样。

- Actions secret：`APT_SIGNING_KEY`。
- Actions variable：`APT_SIGNING_FINGERPRINT`。
- 本机私钥备份：`~/.local/share/usb-camera-preview/apt-signing/`，权限 700，需安全备份。
- 私钥导入 runner 临时目录，签名完成后清理；Git 和 Pages 仅含公钥。
- Camera 的旧 Pages 源继续兼容，因此其仓库也保留原签名凭据。
- 更换密钥须协调两个仓库的 Secrets、公钥、指纹及客户端配置。

## 本地运行与排障

```bash
cd /home/ubuntu/Workspace/Codex/apt
export GNUPGHOME="$HOME/.local/share/usb-camera-preview/apt-signing"
export APT_SIGNING_FINGERPRINT="$(cat keys/apt-key.fingerprint)"
python3 build_repo.py
gh run list --repo leavs/apt --limit 3
```

需要 Python 3、gh 已登录、apt-utils、GnuPG；产物位于被 Git 忽略的 `build/site/`。不要把签名私钥或下载产物提交到仓库。

客户端完整配置在首页和 README；使用 `signed-by=/etc/apt/keyrings/leavs-tools.gpg` 限定此源的签名密钥。原 Camera 源可移除后迁移到公共源，密钥指纹保持一致。

常见失败：来源尚无正式 Release；缺少校验文件或摘要错误；出现未登记包；Secrets/变量遗漏；密钥与提交的公钥不一致；Pages 的 `github-pages` 环境未允许 `main`。查看 Actions 具体失败步骤后修复。

## 容量与后续维护

Pages 的 1 GB 站点上限和 100 GB/月软带宽并非 Free 专属。当前仅收录各工具最新 Release，包合计大于 900 MB 时停止构建；历史版本仍在项目 Releases。规模增长可迁移对象存储/CDN。不要把安装包直接提交到 Git 历史中。

构建依赖及 action 版本尚未完全固定，可能看到 Node.js 弃用提示；最近运行正常。后续可升级相关 actions 并重新验证发布。

交接说明提交包含 `[skip ci]`，不会额外触发 push 构建；定时任务照常运行。
