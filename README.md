# osu谱面下载器 for AstrBot

自动识别 osu! 谱面链接，从多个镜像站下载 `.osz` 文件并发送到群聊。
## 功能特性

- 🔗 自动识别 `https://osu.ppy.sh/beatmapsets/数字` 链接
- 📥 从以下镜像站下载（按顺序尝试）：
  - osu.direct
  - catboy.best
- 📦 自动发送 `.osz` 文件到群聊
- 🧹 发送后自动清理临时文件
- ⚙️ 可配置最大文件大小（默认 20MB）

## 安装

1. 将插件目录放入 AstrBot 的 `data/plugins/` 文件夹。
2. 重启 AstrBot。
3. （可选）在 WebUI 插件配置中调整 `max_size_mb`。

## 使用方法

在群里发送 `/download <链接>` 或 `/dl <链接>`，机器人会自动下载并发送谱面文件。

示例：
```
/download https://osu.ppy.sh/beatmapsets/2508618
/dl https://osu.ppy.sh/beatmapsets/2508618#mania/5525561
```

## 配置项

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| max_size_mb | int | 20 | 允许下载的最大文件大小（MB），超过则放弃下载 |

## 依赖

- AstrBot 运行环境
- 网络能访问镜像站

## 致谢

- 镜像站 [osu.direct](https://osu.direct) 和 [catboy.best](https://catboy.best) 提供下载服务

## 贡献者

- 原作者：[xianyuOvO](https://github.com/xianyuOvO0)
- 修改：[ZHAO20060708](https://github.com/ZHAO20060708)

