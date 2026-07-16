"""Download osu! beatmap sets through mirror services."""

import asyncio
import os
import re
from pathlib import Path
from uuid import uuid4

import aiohttp

from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.message_components import File, Plain
from astrbot.api.star import Context, Star
from astrbot.core.message.message_event_result import MessageChain
from astrbot.core.utils.astrbot_path import get_astrbot_data_path

DOWNLOAD_REQUEST_RE = re.compile(
    r"^/(?P<cmd>download|dl)\s+https?://osu\.ppy\.sh/beatmapsets/(?P<set_id>\d+)",
    re.IGNORECASE,
)


class OsuDownloader(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.max_size_mb = max(0, int(config.get("max_size_mb", 20)))
        self.max_size_bytes = (
            self.max_size_mb * 1024 * 1024 if self.max_size_mb > 0 else 0
        )
        self.cleanup_delay_seconds = max(
            10, int(config.get("cleanup_delay_seconds", 120))
        )
        self.session: aiohttp.ClientSession | None = None
        self._cleanup_tasks: set[asyncio.Task] = set()

        self.temp_dir = (
            Path(get_astrbot_data_path())
            / "plugin_data"
            / "astrbot_plugin_osu_downloader"
            / "cache"
        )
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        self.mirrors = [
            "https://osu.direct/api/d/{}",
            "https://catboy.best/d/{}",
        ]

    async def initialize(self):
        self.session = aiohttp.ClientSession()
        logger.info("osu谱面下载器已启动")

    async def terminate(self):
        if self.session:
            await self.session.close()
        tasks = list(self._cleanup_tasks)
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def download_osz(self, set_id: int, retries: int = 2) -> Path | None:
        """从镜像站下载，返回本地绝对路径"""
        if self.session is None:
            raise RuntimeError("下载会话尚未初始化")

        local_path = self.temp_dir / f"beatmapset_{set_id}_{uuid4().hex[:12]}.osz"
        timeout = aiohttp.ClientTimeout(total=120, connect=30)

        for url_template in self.mirrors:
            download_url = url_template.format(set_id)
            for attempt in range(retries + 1):
                try:
                    async with self.session.get(
                        download_url,
                        timeout=timeout,
                        allow_redirects=True,
                    ) as resp:
                        if resp.status != 200:
                            logger.warning(
                                f"{download_url} 返回 {resp.status} "
                                f"(尝试 {attempt + 1}/{retries + 1})"
                            )
                            continue

                        content_type = resp.headers.get("Content-Type", "")
                        if "text/html" in content_type:
                            logger.warning(f"{download_url} 返回 HTML，可能谱面不存在")
                            break

                        total_size = int(resp.headers.get("content-length", 0) or 0)
                        if self.max_size_bytes and total_size > self.max_size_bytes:
                            logger.warning(
                                f"文件过大 ({total_size / 1024 / 1024:.1f} MB > "
                                f"{self.max_size_mb} MB)"
                            )
                            continue

                        # 写入文件
                        with local_path.open("wb") as f:
                            downloaded = 0
                            while True:
                                chunk = await resp.content.read(8192)
                                if not chunk:
                                    break
                                downloaded += len(chunk)
                                if self.max_size_bytes and downloaded > self.max_size_bytes:
                                    raise ValueError(
                                        f"文件超过 {self.max_size_mb} MB 下载限制"
                                    )
                                f.write(chunk)
                            f.flush()
                            os.fsync(f.fileno())

                        # 验证文件大小
                        if not local_path.exists():
                            logger.error(f"文件写入后不存在: {local_path}")
                            continue
                        actual_size = local_path.stat().st_size
                        if total_size > 0 and actual_size != total_size:
                            logger.warning(
                                f"大小不匹配：预期 {total_size}，实际 {actual_size}，删除重试"
                            )
                            local_path.unlink(missing_ok=True)
                            continue

                        logger.info(f"从 {download_url} 下载成功，路径 {local_path}，大小 {actual_size}")
                        return local_path

                except asyncio.TimeoutError:
                    logger.warning(
                        f"下载超时 {download_url} "
                        f"(尝试 {attempt + 1}/{retries + 1})"
                    )
                    local_path.unlink(missing_ok=True)
                except ValueError as e:
                    logger.warning(f"下载已中止 {download_url}: {e}")
                    local_path.unlink(missing_ok=True)
                    break
                except Exception as e:
                    logger.error(
                        f"下载异常 {download_url}: {e} "
                        f"(尝试 {attempt + 1}/{retries + 1})"
                    )
                    local_path.unlink(missing_ok=True)
        return None

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def on_download_command(self, event: AstrMessageEvent):
        """统一处理 /download 与 /dl 指令，格式：/download <osu谱面链接> 或 /dl <osu谱面链接>"""

        raw_text = str(
            getattr(getattr(event, "message_obj", None), "message_str", "") or ""
        )
        matched = DOWNLOAD_REQUEST_RE.match(raw_text)
        if not matched:
            return

        set_id = int(matched.group("set_id"))

        await event.send(MessageChain([Plain(f"正在下载谱面集 {set_id}，请稍候。")]))

        file_path = await self.download_osz(set_id)
        if not file_path or not file_path.exists():
            await event.send(MessageChain([Plain("下载失败：谱面可能不存在，或镜像站暂时不可用。")]))
            return

        try:
            file_name = file_path.name
            if file_path.exists():
                await event.send(MessageChain([File(name=file_name, file=str(file_path))]))
                await event.send(MessageChain([Plain(f"已发送 {file_name}。")]))
            else:
                await event.send(MessageChain([Plain("文件不存在，下载可能尚未完成。")]))
        except Exception as e:
            logger.exception("发送谱面文件失败")
            await event.send(MessageChain([Plain(f"发送文件失败：{e}")]))

        finally:
            task = asyncio.create_task(self._cleanup_later(file_path))
            self._cleanup_tasks.add(task)
            task.add_done_callback(self._cleanup_tasks.discard)

    async def _cleanup_later(self, file_path: Path) -> None:
        try:
            await asyncio.sleep(self.cleanup_delay_seconds)
        finally:
            file_path.unlink(missing_ok=True)
