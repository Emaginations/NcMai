"""
麦麦解析 (NCMai) - 解码用户发送的 .ncm 文件并返回原始音频。

⚠️ 免责声明：本插件仅供技术学习交流，请于 24 小时内删除解码生成的文件。
感谢群友 termux 提供的源代码。

2026-06-22 Try1: 初始版本，将 C 解码核心迁移为纯 Python 实现。
2026-06-22 Try2: 移除直接 OneBot HTTP 调用，改用 MaiBot SDK 发送文件（通过 SnowLuma 网关）。
"""
import asyncio
import os
import random
import tempfile
import time
from typing import Any, Dict, List, Optional

from Crypto.Cipher import AES
from maibot_sdk import (
    Field,
    HookHandler,
    MaiBotPlugin,
    PluginConfigBase,
)
from maibot_sdk.types import HookMode, HookOrder

import aiohttp

# ============================================================================
# 多语言化（基础）
# ============================================================================
def _schema_i18n(
    *,
    label_en: str,
    label_ja: str = "",
    hint_en: Optional[str] = None,
    hint_ja: Optional[str] = None,
) -> Dict[str, Dict[str, str]]:
    i18n: Dict[str, Dict[str, str]] = {
        "en_US": {"label": label_en},
    }
    if label_ja:
        i18n["ja_JP"] = {"label": label_ja}
    if hint_en:
        i18n["en_US"]["hint"] = hint_en
    if hint_ja and label_ja:
        i18n["ja_JP"]["hint"] = hint_ja
    return i18n

# ============================================================================
# 配置模型
# ============================================================================
class PluginSection(PluginConfigBase):
    __ui_label__ = "插件设置"
    __ui_order__ = 0
    enabled: bool = Field(default=True, description="是否启用插件", json_schema_extra={
        "label": "开关",
        "i18n": _schema_i18n(label_en="Enable", label_ja="有効"),
        "order": 0,
    })
    config_version: str = Field(default="1.0.0", description="配置版本", json_schema_extra={
        "label": "配置版本",
        "i18n": _schema_i18n(label_en="Config Version"),
        "order": 1,
    })

class DecodeConfig(PluginConfigBase):
    __ui_label__ = "解码设置"
    __ui_order__ = 2
    progress_messages: List[str] = Field(default_factory=list, description="解码时随机发送的提示语（支持 emoji）", json_schema_extra={
        "label": "随机提示语",
        "hint": "最多21条，每条不超过10字（含emoji）",
        "i18n": _schema_i18n(label_en="Progress Messages", label_ja="進行状況メッセージ"),
        "order": 0,
    })

class CleanupConfig(PluginConfigBase):
    __ui_label__ = "缓存清理"
    __ui_order__ = 3
    cache_ttl_seconds: int = Field(default=86400, ge=60, description="解码文件的生命周期（秒）", json_schema_extra={
        "label": "缓存有效期（秒）",
        "hint": "默认 86400 秒（24小时）",
        "i18n": _schema_i18n(label_en="Cache TTL (seconds)", label_ja="キャッシュ有効期間（秒）"),
        "order": 0,
    })
    clean_on_request: bool = Field(default=True, description="收到新文件时是否清理过期缓存", json_schema_extra={
        "label": "按需清理",
        "i18n": _schema_i18n(label_en="Clean on Request", label_ja="リクエスト時にクリーン"),
        "order": 1,
    })

class NCMaiConfig(PluginConfigBase):
    plugin: PluginSection = Field(default_factory=PluginSection)
    decode: DecodeConfig = Field(default_factory=DecodeConfig)
    cleanup: CleanupConfig = Field(default_factory=CleanupConfig)

# ============================================================================
# NCM 解码器
# ============================================================================
class NCMDecoder:
    NCM_MAGIC = b"CTENFDAM"
    CORE_KEY = b"hzHRAmso5kInbaxW"
    META_KEY = b"#14ljk_!\\]&0U<\'("

    @staticmethod
    def xor_bytes(data: bytearray, key: int) -> None:
        for i in range(len(data)):
            data[i] ^= key

    @staticmethod
    def aes_ecb_decrypt(data: bytes, key: bytes) -> bytes:
        cipher = AES.new(key, AES.MODE_ECB)
        plain = cipher.decrypt(data)
        pad = plain[-1]
        if 1 <= pad <= 16 and plain[-pad:] == bytes([pad]) * pad:
            return plain[:-pad]
        return plain

    @staticmethod
    def build_keybox(key: bytes) -> bytearray:
        box = bytearray(range(256))
        key_len = len(key)
        key_offset = 0
        last = 0
        for i in range(256):
            swap = box[i]
            c = (swap + last + key[key_offset]) & 0xFF
            key_offset = (key_offset + 1) % key_len
            box[i] = box[c]
            box[c] = swap
            last = c
        return box

    @staticmethod
    def decrypt_audio(data: bytearray, box: bytearray) -> None:
        for i in range(len(data)):
            j = (i + 1) & 0xFF
            k = box[(box[j] + box[(box[j] + j) & 0xFF]) & 0xFF]
            data[i] ^= k

    def decode(self, ncm_data: bytes) -> Optional[bytes]:
        if len(ncm_data) < 32 or ncm_data[:8] != self.NCM_MAGIC:
            return None
        pos = 10
        key_len = int.from_bytes(ncm_data[pos:pos+4], "little")
        pos += 4
        if key_len == 0 or pos + key_len > len(ncm_data):
            return None
        key_block = bytearray(ncm_data[pos:pos+key_len])
        pos += key_len
        self.xor_bytes(key_block, 0x64)
        try:
            key_plain = self.aes_ecb_decrypt(bytes(key_block), self.CORE_KEY)
        except Exception:
            return None
        if len(key_plain) <= 17:
            return None
        keybox = self.build_keybox(key_plain[17:])
        meta_len = int.from_bytes(ncm_data[pos:pos+4], "little")
        pos += 4 + meta_len
        if pos + 13 > len(ncm_data):
            return None
        pos += 4 + 5
        img_len = int.from_bytes(ncm_data[pos:pos+4], "little")
        pos += 4 + img_len
        audio = bytearray(ncm_data[pos:])
        self.decrypt_audio(audio, keybox)
        return bytes(audio)

# ============================================================================
# 插件主体
# ============================================================================
class NCMaiPlugin(MaiBotPlugin):
    async def on_load(self) -> None:
        self.ctx.logger.info("[麦麦解析] 插件已加载，注意：解码文件请于24小时内删除，仅供学习交流。")
        self._decoder = NCMDecoder()
        self._http_session: Optional[aiohttp.ClientSession] = None
        self._cache_dir = tempfile.mkdtemp(prefix="ncmai_cache_")
        self.ctx.logger.info(f"[麦麦解析] 缓存目录: {self._cache_dir}")
        self._last_cleanup = time.time()

    async def on_unload(self) -> None:
        if self._http_session and not self._http_session.closed:
            await self._http_session.close()
        try:
            for f in os.listdir(self._cache_dir):
                os.remove(os.path.join(self._cache_dir, f))
            os.rmdir(self._cache_dir)
        except Exception:
            pass
        self.ctx.logger.info("[麦麦解析] 插件已卸载，缓存已清理。")

    async def on_config_update(self, scope: str, config_data: dict, version: str) -> None:
        if scope == "self":
            self.ctx.logger.info("[麦麦解析] 配置已更新: version=%s", version)

    config_model = NCMaiConfig

    async def _clean_old_cache(self):
        ttl = self.config.cleanup.cache_ttl_seconds
        now = time.time()
        if now - self._last_cleanup < 60:
            return
        self._last_cleanup = now
        try:
            for fname in os.listdir(self._cache_dir):
                fpath = os.path.join(self._cache_dir, fname)
                if os.path.isfile(fpath):
                    if now - os.path.getmtime(fpath) > ttl:
                        os.remove(fpath)
                        self.ctx.logger.info(f"[麦麦解析] 已清理过期缓存: {fname}")
        except Exception as e:
            self.ctx.logger.warning(f"[麦麦解析] 缓存清理异常: {e}")

    def _random_progress_msg(self) -> str:
        msgs = self.config.decode.progress_messages
        if not msgs:
            return "🎵 正在解码..."
        return random.choice(msgs)

    def _detect_extension(self, data: bytes) -> str:
        if data[:4] == b'fLaC':
            return 'flac'
        if data[:3] == b'ID3':
            return 'mp3'
        if len(data) >= 2 and data[0] == 0xFF and (data[1] & 0xE0) == 0xE0:
            return 'mp3'
        if len(data) >= 8 and data[4:8] == b'ftyp':
            return 'm4a'
        return 'bin'

    async def _send_text(self, stream_id: str, text: str):
        if stream_id:
            try:
                await self.ctx.send.text(text, stream_id)
            except Exception as e:
                self.ctx.logger.warning(f"[麦麦解析] 发送文本失败: {e}")
        else:
            self.ctx.logger.info(f"[麦麦解析] 无法发送消息(stream_id 为空): {text}")

    async def _send_file(self, stream_id: str, file_path: str, file_name: str):
        abs_path = os.path.abspath(file_path).replace(os.sep, '/')
        file_uri = f"file:///{abs_path}"
        message_chain = [
            {
                "type": "file",
                "data": {
                    "file": file_uri,
                    "name": file_name,
                },
            }
        ]
        try:
            result = await self.ctx.send.custom(stream_id, message_chain)
            self.ctx.logger.info(f"[麦麦解析] 文件发送结果: {result}")
            return True
        except Exception as e:
            self.ctx.logger.error(f"[麦麦解析] 发送文件失败: {e}")
            return False

    @HookHandler(
        "chat.receive.after_process",
        name="ncmai_file_handler",
        description="检测 .ncm 文件并解码返回",
        mode=HookMode.BLOCKING,
        order=HookOrder.NORMAL,
        timeout_ms=30000,
    )
    async def handle_file(self, message: dict, **kwargs) -> Optional[dict]:
        del kwargs
        if not self.config.plugin.enabled:
            return None

        file_info = None
        for segment in message.get("message", []):
            if isinstance(segment, dict) and segment.get("type") == "file":
                file_info = segment.get("data", {})
                break
        if not file_info:
            file_info = message.get("file")
        if not file_info:
            return None

        file_name = file_info.get("name", "unknown.ncm")
        if not file_name.lower().endswith(".ncm"):
            return None

        user_id = None
        group_id = None
        sender = message.get("sender", {})
        user_id = sender.get("user_id")
        if not user_id:
            user_info = message.get("user_info", {})
            user_id = user_info.get("user_id")
        group_info = message.get("group_info", {}) or message.get("message_info", {}).get("group_info", {})
        group_id = group_info.get("group_id")

        if not user_id:
            self.ctx.logger.warning("[麦麦解析] 无法获取发送者 ID")
            return None

        stream_id = message.get("stream_id") or message.get("session_id") or ""
        if not stream_id and group_id:
            try:
                stream = await self.ctx.chat.get_stream_by_group_id(str(group_id), platform="qq")
                if isinstance(stream, dict):
                    stream_id = stream.get("stream_id") or stream.get("session_id") or ""
            except Exception:
                pass

        file_url = file_info.get("url")
        if not file_url:
            await self._send_text(stream_id, "❌ 无法获取文件下载链接")
            return {"action": "abort"}

        self.ctx.logger.info(f"[麦麦解析] 收到 .ncm 文件: {file_name}, 来自用户 {user_id}")
        progress_msg = self._random_progress_msg()
        await self._send_text(stream_id, progress_msg)

        if self._http_session is None or self._http_session.closed:
            self._http_session = aiohttp.ClientSession()
        try:
            async with self._http_session.get(file_url) as resp:
                if resp.status != 200:
                    await self._send_text(stream_id, "❌ 文件下载失败")
                    return {"action": "abort"}
                ncm_data = await resp.read()
        except Exception as e:
            self.ctx.logger.error(f"[麦麦解析] 下载异常: {e}")
            await self._send_text(stream_id, "❌ 文件下载出错")
            return {"action": "abort"}

        audio_data = self._decoder.decode(ncm_data)
        if not audio_data:
            await self._send_text(stream_id, "❌ 解码失败，文件可能已损坏或不是标准 .ncm 格式")
            return {"action": "abort"}

        ext = self._detect_extension(audio_data)
        safe_name = os.path.splitext(file_name)[0]
        out_name = f"{safe_name}.{ext}"
        out_path = os.path.join(self._cache_dir, out_name)
        with open(out_path, "wb") as f:
            f.write(audio_data)
        self.ctx.logger.info(f"[麦麦解析] 解码成功，文件: {out_name}")

        send_ok = await self._send_file(stream_id, out_path, out_name)
        if not send_ok:
            await self._send_text(stream_id, "❌ 文件发送失败，请稍后重试")

        if self.config.cleanup.clean_on_request:
            await self._clean_old_cache()

        return None


def create_plugin():
    return NCMaiPlugin()

#try2