# iOS 云剪贴板快捷指令

对应本仓库 Cloudflare Workers 后端，提供两个 iOS 原生快捷指令：

- **Cloud-Clipboard-Send**：将剪贴板文字、链接或单张图片发送到指定房间，也可从照片或“文件”App 的分享菜单发送一项内容。图片转为 PNG，Live Photo 发送静态画面；其他文件通过 multipart 的 `file` 字段上传。
- **Cloud-Clipboard-Receive**：获取指定房间最新一条内容。文字和图片写入 iPhone 剪贴板；其他文件打开分享菜单，可选“存储到文件”或目标 App。

文字发送成功、文字或图片复制成功时振动一次。大小限制、历史条数和文件过期时间使用你的服务器配置。每次发送一项；这是手动运行的快捷指令，不会持续监听剪贴板。

## 导入

1. 在本仓库 Actions → **Build iOS Shortcuts** 的成功运行中下载 **Cloud-Clipboard-iOS-Shortcuts** artifact，解压。
2. 将两个 `.shortcut` 文件放入 iCloud Drive，在 iPhone 的“文件”App 中点开并添加。`source/` 内的 `.cherri` 和 `.plist` 是源码，不能当作已签名文件直接导入。
3. 两个指令分别填写相同的三项配置：

| 配置 | 填法 |
| --- | --- |
| 部署地址 | `https://clip.example.com` 或完整 Workers 域名，不带网页房间路径、`/api` 或 `#` 后的内容 |
| 房间名 | 与网页使用的房间名完全一致，默认填 `default`，支持中文 |
| 密码 | 项目全局访问密码或此房间密码；未设置则留空。不是 Cloudflare API Token，也不要加 `Bearer ` |

导入后可重命名为“发送到云剪贴板”和“获取云剪贴板”。配置也可以在编辑器顶部的三个“文本”动作中修改。

首次运行允许网络和剪贴板访问。依次验证中文文字、截图、从“文件”App 分享一个 PDF 的发送及接收；网页与手机必须使用同一房间。尚未进行 iPhone 真机验证，也未连接你的实际部署。

## 接口依据

| 用途 | 项目接口 | 请求方式 |
| --- | --- | --- |
| 文字发送 | `POST /text?room=…` | 原始 UTF-8 文字，`Content-Type: text/plain; charset=utf-8` |
| 图片/文件发送 | `POST /upload?room=…` | multipart/form-data，文件字段名 `file`；由系统生成 boundary |
| 最新内容元数据 | `GET /content/latest?room=…&json=1` | 返回 `type`，文字为 `content`，文件为 `uuid`、`name` |
| 文件下载 | `GET /file/{uuid}/{name}?room=…` | 按 UUID 下载原条目，避免接收过程中新的上传改变下载目标 |

所有请求携带 `Authorization: Bearer <密码>`。Cloudflare 后端 `auth.js` 明确兼容直接使用密码，因此不依赖会过期的登录会话 Token。接收文字使用 JSON 内的 `content`，不会附加纯文本下载接口自动补充的换行。

仓库原有 `../cloud-clipboard-shortcuts.zip` 内是 HTTP Shortcuts 的 JSON 配置，并非 Apple `.shortcut` 文件。

## 构建和签名

源码使用 [Cherri 2.3.0](https://github.com/electrikmilk/cherri/releases/tag/v2.3.0)。[工作流](../../.github/workflows/ios-shortcuts.yml) 在 GitHub Actions Linux 运行器编译，通过 Python 补全原生 multipart 文件附件字段（规避编译器对嵌套原始参数的序列化问题），检查 plist、导入配置与 HTTP 请求结构，然后将同一份 plist 交给 [RoutineHub HubSign](https://cherrilang.org/getting-started.html) 完成签名，再验证签名文件的 AEA 容器头。重新构建请使用完整工作流；单独编译发送指令的 `.cherri` 不会包含文件上传字段。artifact 中 `.plist` 是完整可审阅源文件。

HubSign 会收到完整的空配置快捷指令模板。真实地址和密码只在手机导入时填写；不要把配置后的指令提交到公开仓库。工作流不读取部署 Secrets，不触发 Cloudflare 部署。

首次构建由 `codex/ios-shortcuts` 分支的源码推送触发；工作流进入默认分支后也可通过 **Run workflow** 手动运行。签名成功和结构检查不等于 iPhone 真机收发通过。
