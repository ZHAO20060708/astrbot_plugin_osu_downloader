# osu! 谱面下载器

`astrbot_plugin_osu_downloader` 是一个面向 AstrBot OneBot 平台的 osu! 谱面集下载插件。用户提交 osu! BeatmapSet 链接后，插件会依次尝试镜像站并发送对应的 `.osz` 文件。

本仓库基于 [xianyuOvO0/astrbot_plugin_osu_downloader](https://github.com/xianyuOvO0/astrbot_plugin_osu_downloader) 维护，并由 [ZHAO20060708](https://github.com/ZHAO20060708) 持续修正命令处理、下载源和文件生命周期。

## 功能

- 支持 `/download` 和 `/dl` 命令。
- 识别 `osu.ppy.sh/beatmapsets/<id>` 链接。
- 依次尝试 `osu.direct` 与 `catboy.best` 镜像。
- 在响应缺少 `Content-Length` 时仍可正确完成下载。
- 在流式下载过程中执行文件大小限制。
- 为并发请求使用独立临时文件，避免相互覆盖。
- 文件发送后延迟清理，避免消息平台尚未读取时提前删除。

## 环境要求

- AstrBot `>=4.13.0,<5`
- OneBot v11（`aiocqhttp`）平台适配器
- 可访问至少一个已配置的镜像站

Python 依赖见 [`requirements.txt`](requirements.txt)，AstrBot 会在加载插件时自动安装。

## 安装

在 AstrBot WebUI 中使用以下 GitHub 地址安装：

```text
https://github.com/ZHAO20060708/astrbot_plugin_osu_downloader
```

也可以手动克隆到插件目录：

```bash
cd AstrBot/data/plugins
git clone https://github.com/ZHAO20060708/astrbot_plugin_osu_downloader.git
```

安装完成后重载插件或重启 AstrBot。

## 使用

```text
/download https://osu.ppy.sh/beatmapsets/2508618
/dl https://osu.ppy.sh/beatmapsets/2508618#mania/5525561
```

命令需要包含完整的 BeatmapSet 链接。链接中的模式和难度片段不会影响下载结果，插件始终下载整个谱面集。

## 配置

| 配置项 | 默认值 | 说明 |
| --- | ---: | --- |
| `max_size_mb` | `20` | 最大下载文件大小；`0` 表示不限制 |
| `cleanup_delay_seconds` | `120` | 文件发送后延迟清理的秒数 |

临时文件位于：

```text
data/plugin_data/astrbot_plugin_osu_downloader/cache/
```

## 下载源与免责声明

插件当前使用以下第三方镜像：

1. [osu.direct](https://osu.direct)
2. [catboy.best](https://catboy.best)

镜像站的可用性、速率限制和内容完整性不受本项目控制。下载和使用谱面时请遵守 osu! 官方规则及相关内容许可。

## 许可证与维护者

- 原作者：[xianyuOvO](https://github.com/xianyuOvO0)
- 修改与维护：[ZHAO20060708](https://github.com/ZHAO20060708)

使用、修改和分发时请遵守本仓库的 [`LICENSE`](LICENSE)。
