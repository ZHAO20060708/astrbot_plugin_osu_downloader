"""
osu谱面下载器
- 临时文件存放于 /AstrBot/data/plugin_data/astrbot_plugin_osu_downloader/cache/
- 优先 sayobot，osu.direct，备用 catboy.best
- 增加文件存在性验证
"""

import re
import os
import aiohttp
import asyncio
from typing import Optional

from astrbot.api import star, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.core.message.message_event_result import MessageChain
from astrbot.api.message_components import Plain, File


class OsuDownloader(star.Star):
    def __init__(self, context, config):
        super().__init__(context)
        self.config = config
        self.max_size_mb = config.get("max_size_mb", 20)
        self.max_size_bytes = self.max_size_mb * 1024 * 1024
        self.session = None

        # 动态获取数据目录
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
        self.temp_dir = os.path.join(data_dir, "plugin_data", "astrbot_plugin_osu_downloader", "cache")
        os.makedirs(self.temp_dir, exist_ok=True)

        self.mirrors = [
            "https://txy1.sayobot.cn/beatmaps/download/full/{}",
            "https://osu.direct/api/d/{}",
            "https://catboy.best/d/{}",
        ]

    async def initialize(self):
        self.session = aiohttp.ClientSession()
        logger.info("osu谱面下载器已启动")

    async def terminate(self):
        if self.session:
            await self.session.close()

    async def download_osz(self, set_id: int, retries: int = 2) -> Optional[str]:
        """从镜像站下载，返回本地绝对路径"""
        local_path = os.path.join(self.temp_dir, f"beatmapset_{set_id}.osz")
        timeout = aiohttp.ClientTimeout(total=120, connect=30)

        for url_template in self.mirrors:
            download_url = url_template.format(set_id)
            for attempt in range(retries + 1):
                try:
                    async with self.session.get(download_url, timeout=timeout, allow_redirects=True) as resp:
                        if resp.status != 200:
                            logger.warning(f"{download_url} 返回 {resp.status} (尝试 {attempt+1}/{retries+1})")
                            continue

                        content_type = resp.headers.get('Content-Type', '')
                        if 'text/html' in content_type:
                            logger.warning(f"{download_url} 返回 HTML，可能谱面不存在")
                            break

                        total_size = int(resp.headers.get('content-length', 0))
                        if total_size > self.max_size_bytes:
                            logger.warning(f"文件过大 ({total_size/1024/1024:.1f}MB > {self.max_size_mb}MB)")
                            continue

                        # 写入文件
                        with open(local_path, 'wb') as f:
                            downloaded = 0
                            while True:
                                chunk = await resp.content.read(8192)
                                if not chunk:
                                    break
                                f.write(chunk)
                                downloaded += len(chunk)
                            f.flush()
                            os.fsync(f.fileno())

                        # 验证文件大小
                        if not os.path.exists(local_path):
                            logger.error(f"文件写入后不存在: {local_path}")
                            continue
                        actual_size = os.path.getsize(local_path)
                        if actual_size != total_size:
                            logger.warning(f"大小不匹配：预期 {total_size}，实际 {actual_size}，删除重试")
                            os.remove(local_path)
                            continue

                        logger.info(f"从 {download_url} 下载成功，路径 {local_path}，大小 {actual_size}")
                        return local_path

                except asyncio.TimeoutError:
                    logger.warning(f"下载超时 {download_url} (尝试 {attempt+1}/{retries+1})")
                except Exception as e:
                    logger.error(f"下载异常 {download_url}: {e} (尝试 {attempt+1}/{retries+1})")
        return None

    @filter.regex(r"https?://osu\.ppy\.sh/beatmapsets/(\d+)")
    async def on_osu_link(self, event: AstrMessageEvent):
        """识别 osu! 谱面链接并自动下载 .osz 文件"""
        match = re.search(r"https?://osu\.ppy\.sh/beatmapsets/(\d+)", event.message_str)
        if not match:
            return
        set_id = int(match.group(1))

        await event.send(MessageChain([Plain(f"🎵 正在下载谱面 {set_id} 喵~")]))

        file_path = await self.download_osz(set_id)
        if not file_path or not os.path.exists(file_path):
            await event.send(MessageChain([Plain("❌ 下载失败喵~，谱面可能不存在或网络出现问题")]))
            return

        try:
            file_name = os.path.basename(file_path)
            if os.path.exists(file_path):
                await event.send(MessageChain([File(name=file_name, file=file_path)]))
                await event.send(MessageChain([Plain(f"✅ 已发送 {file_name} 喵~")]))
            else:
                await event.send(MessageChain([Plain("❌ 文件不存在，可能下载未完成喵~")]))
        except Exception as e:
            logger.error(f"发送文件失败: {e}")
            await event.send(MessageChain([Plain(f"❌ 发送文件失败喵~")]))

        #下载完成后删除临时文件
        finally:
            if os.path.exists(file_path):
                 os.remove(file_path)


def get_star(context, config):
    return OsuDownloader(context, config)
