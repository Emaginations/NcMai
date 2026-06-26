"""
麦麦解析 (NCMai) - 解码用户发送的 .ncm 文件并返回原始音频。

⚠️ 免责声明：本插件仅供技术学习交流，请于 24 小时内删除解码生成的文件。
感谢 termux 提供的源代码。

2026-06-22 Try1: 初始版本，将 C 解码核心迁移为纯 Python 实现。
2026-06-22 Try2: 移除直接 OneBot HTTP 调用，改用 MaiBot SDK 发送文件（通过 SnowLuma 网关）。
2026-06-24 Try3: 完善文件发送流程（先上传获取 file_id 再发送），支持 SnowLuma / NapCat 双适配器。
2026-06-24 Try4: 新增 /ncm 命令（单文件测试解码），新增 test 配置节，完善免责声明。提示语日常化。
2026-06-25 Try5: 全面重构 WebUI 配置（下拉选择器），强化日志，测试命令可控，缓存自动清理。
2026-06-26 Try6: 网关改为滑动开关（SnowLuma/NapCat），提示语恢复为可编辑列表；增强用户 ID 提取兼容性；Docker 环境适配。
"""
import asyncio
import os
import random
import time
from typing import Any, Dict, List, Optional

from maibot_sdk import (
    Command,
    Field,
    HookHandler,
    MaiBotPlugin,
    PluginConfigBase,
)
from maibot_sdk.types import HookMode, HookOrder

import aiohttp

# AES 解密库导入（兼容多种安装方式）
from Crypto.Cipher import AES

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

class GatewayConfig(PluginConfigBase):
    __ui_label__ = "网关设置"
    __ui_order__ = 1
    use_snowluma: bool = Field(
        default=True,
        description="是否使用 SnowLuma 适配器（关闭则使用 NapCat）",
        json_schema_extra={
            "label": "适配器",
            "hint": "开启：SnowLuma | 关闭：NapCat",
            "x-widget": "switch",
            "i18n": _schema_i18n(
                label_en="Use SnowLuma",
                label_ja="SnowLuma を使用",
                hint_en="Turn on for SnowLuma, off for NapCat",
                hint_ja="オンでSnowLuma、オフでNapCat"
            ),
            "order": 0,
        },
    )

class DecodeConfig(PluginConfigBase):
    __ui_label__ = "解码设置"
    __ui_order__ = 2
    progress_messages: List[str] = Field(
        default_factory=list,
        description="解码时随机发送的提示语（支持 emoji，长度 2-10 字）",
        json_schema_extra={
            "label": "随机提示语",
            "hint": "每行一条，最多 21 条",
            "i18n": _schema_i18n(label_en="Progress Messages", label_ja="進行状況メッセージ"),
            "order": 0,
        },
    )

class TestConfig(PluginConfigBase):
    __ui_label__ = "测试命令"
    __ui_order__ = 3
    enable_test_command: bool = Field(
        default=True,
        description="是否启用 /ncm 测试命令",
        json_schema_extra={
            "label": "启用 /ncm 命令",
            "i18n": _schema_i18n(label_en="Enable /ncm", label_ja="/ncmを有効化"),
            "order": 0,
        },
    )
    test_user_id: str = Field(
        default="",
        description="测试账号（QQ号），留空则不限制 /ncm 使用者",
        json_schema_extra={
            "label": "测试账号",
            "placeholder": "留空则所有人可用",
            "i18n": _schema_i18n(label_en="Test User ID", label_ja="テストユーザーID"),
            "order": 1,
        },
    )

class NCMaiConfig(PluginConfigBase):
    plugin: PluginSection = Field(default_factory=PluginSection)
    gateway: GatewayConfig = Field(default_factory=GatewayConfig)
    decode: DecodeConfig = Field(default_factory=DecodeConfig)
    test: TestConfig = Field(default_factory=TestConfig)

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
        if AES is None:
            raise RuntimeError(
                "未找到可用的 AES 解密库。请安装 pycryptodome：\n"
                "  pip install pycryptodome"
            )
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
# 文件发送适配器
# ============================================================================
class FileSender:
    """统一文件发送接口，支持 SnowLuma 和 NapCat 两种适配器"""

    def __init__(self, plugin: 'NCMaiPlugin'):
        self.plugin = plugin

    @property
    def adapter(self) -> str:
        return "snowluma" if self.plugin.config.gateway.use_snowluma else "napcat"

    async def upload_group_file(self, group_id: int, file_path: str, name: str) -> Optional[str]:
        abs_path = os.path.abspath(file_path).replace(os.sep, '/')
        self.plugin.ctx.logger.info(f"[麦麦解析] 开始上传群文件: {name} (group_id={group_id}, path={abs_path})")
        try:
            result = await self.plugin.ctx.send.custom(
                custom_type="upload_group_file",
                stream_id="",
                data={
                    "group_id": group_id,
                    "file": f"file:///{abs_path}",
                    "name": name,
                    "folder": "/",
                },
            )
            self.plugin.ctx.logger.info(f"[麦麦解析] upload_group_file 返回: {result}")
            if isinstance(result, dict):
                file_id = result.get("file_id") or result.get("data", {}).get("file_id")
                if file_id:
                    self.plugin.ctx.logger.info(f"[麦麦解析] 群文件上传成功: file_id={file_id}")
                    return file_id
            return None
        except Exception as e:
            self.plugin.ctx.logger.error(f"[麦麦解析] 上传群文件异常: {e}")
            return None

    async def upload_private_file(self, user_id: int, file_path: str, name: str) -> Optional[str]:
        abs_path = os.path.abspath(file_path).replace(os.sep, '/')
        self.plugin.ctx.logger.info(f"[麦麦解析] 开始上传私聊文件: {name} (user_id={user_id}, path={abs_path})")
        try:
            result = await self.plugin.ctx.send.custom(
                custom_type="upload_private_file",
                stream_id="",
                data={
                    "user_id": user_id,
                    "file": f"file:///{abs_path}",
                    "name": name,
                },
            )
            self.plugin.ctx.logger.info(f"[麦麦解析] upload_private_file 返回: {result}")
            if isinstance(result, dict):
                file_id = result.get("file_id") or result.get("data", {}).get("file_id")
                if file_id:
                    self.plugin.ctx.logger.info(f"[麦麦解析] 私聊文件上传成功: file_id={file_id}")
                    return file_id
            return None
        except Exception as e:
            self.plugin.ctx.logger.error(f"[麦麦解析] 上传私聊文件异常: {e}")
            return None

    async def send_group_file(self, stream_id: str, group_id: int, file_id: str) -> bool:
        self.plugin.ctx.logger.info(f"[麦麦解析] 发送群文件消息: file_id={file_id}, group_id={group_id}")
        try:
            result = await self.plugin.ctx.send.custom(
                custom_type="send_group_msg",
                stream_id=stream_id,
                data={
                    "group_id": group_id,
                    "message": [
                        {"type": "file", "data": {"file_id": file_id}}
                    ],
                },
            )
            self.plugin.ctx.logger.info(f"[麦麦解析] 群文件发送结果: {result}")
            return True
        except Exception as e:
            self.plugin.ctx.logger.error(f"[麦麦解析] 群文件发送失败: {e}")
            return False

    async def send_private_file(self, stream_id: str, user_id: int, file_id: str) -> bool:
        self.plugin.ctx.logger.info(f"[麦麦解析] 发送私聊文件消息: file_id={file_id}, user_id={user_id}")
        try:
            result = await self.plugin.ctx.send.custom(
                custom_type="send_private_msg",
                stream_id=stream_id,
                data={
                    "user_id": user_id,
                    "message": [
                        {"type": "file", "data": {"file_id": file_id}}
                    ],
                },
            )
            self.plugin.ctx.logger.info(f"[麦麦解析] 私聊文件发送结果: {result}")
            return True
        except Exception as e:
            self.plugin.ctx.logger.error(f"[麦麦解析] 私聊文件发送失败: {e}")
            return False

# ============================================================================
# 插件主体
# ============================================================================
class NCMaiPlugin(MaiBotPlugin):
    # 测试文件路径（相对插件目录，位于 test_ncm_song 文件夹内）
    TEST_NCM_FILE = os.path.join("test_ncm_song", "伊格赛听 - 逍遥仙.ncm")

    async def on_load(self) -> None:
        self.ctx.logger.info("[麦麦解析] 插件已加载，注意：解码文件请于24小时内删除，仅供学习交流。")
        self._decoder = NCMDecoder()
        self._file_sender = FileSender(self)
        self._http_session: Optional[aiohttp.ClientSession] = None
        # 使用插件目录下的 test_ncm_song 作为缓存和输出目录
        self._cache_dir = os.path.join(self._get_plugin_dir(), "test_ncm_song")
        os.makedirs(self._cache_dir, exist_ok=True)
        self.ctx.logger.info(f"[麦麦解析] 缓存目录: {self._cache_dir}")
        self.ctx.logger.info(f"[麦麦解析] 当前适配器: {self._file_sender.adapter}")

    async def on_unload(self) -> None:
        if self._http_session and not self._http_session.closed:
            await self._http_session.close()
        self._clean_cache()
        self.ctx.logger.info("[麦麦解析] 插件已卸载，缓存已清理。")

    async def on_config_update(self, scope: str, config_data: dict, version: str) -> None:
        if scope == "self":
            self.ctx.logger.info("[麦麦解析] 配置已更新: version=%s", version)
            self._file_sender = FileSender(self)
            self.ctx.logger.info(f"[麦麦解析] 适配器已更新: {self._file_sender.adapter}")

    config_model = NCMaiConfig

    # ===== 辅助方法 =====
    def _get_plugin_dir(self) -> str:
        return os.path.dirname(os.path.abspath(__file__))

    def _get_test_file_path(self) -> str:
        return os.path.join(self._get_plugin_dir(), self.TEST_NCM_FILE)

    def _clean_cache(self):
        """删除缓存目录下的解码文件，但保留测试用的 .ncm 文件"""
        test_file_name = os.path.basename(self.TEST_NCM_FILE)
        if os.path.isdir(self._cache_dir):
            for f in os.listdir(self._cache_dir):
                if f == test_file_name:
                    continue
                fpath = os.path.join(self._cache_dir, f)
                try:
                    if os.path.isfile(fpath):
                        os.remove(fpath)
                        self.ctx.logger.info(f"[麦麦解析] 已清理缓存文件: {f}")
                except Exception as e:
                    self.ctx.logger.warning(f"[麦麦解析] 清理文件失败: {f}, {e}")

    def _get_random_progress_msg(self) -> str:
        msgs = self.config.decode.progress_messages
        if not msgs:
            return "🎵 解码中…"
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

    def _get_user_id(self, message: dict) -> str:
        """
        从消息对象中提取发送者的平台用户 ID（QQ号等）。
        兼容多种消息结构，参考 Nightmare 插件实现。
        """
        message_info = message.get("message_info", {})
        if isinstance(message_info, dict):
            user_info = message_info.get("user_info", {})
            if isinstance(user_info, dict):
                uid = user_info.get("user_id", "")
                if uid: return str(uid)
        user_info = message.get("user_info", {})
        if isinstance(user_info, dict):
            uid = user_info.get("user_id", "")
            if uid: return str(uid)
        sender = message.get("sender", {})
        if isinstance(sender, dict):
            uid = sender.get("user_id", "")
            if uid: return str(uid)
        uid = message.get("user_id", "")
        if uid: return str(uid)
        raw = message.get("raw_message", {})
        if isinstance(raw, dict):
            sender = raw.get("sender", {})
            if isinstance(sender, dict):
                uid = sender.get("user_id", "")
                if uid: return str(uid)
            uid = raw.get("user_id", "")
            if uid: return str(uid)
        return ""

    async def _send_text(self, stream_id: str, text: str):
        if stream_id:
            try:
                await self.ctx.send.text(text, stream_id)
            except Exception as e:
                self.ctx.logger.warning(f"[麦麦解析] 发送文本失败: {e}")
        else:
            self.ctx.logger.info(f"[麦麦解析] 无法发送消息(stream_id 为空): {text}")

    async def _do_decode(self, ncm_data: bytes, source_name: str) -> Optional[bytes]:
        audio_data = self._decoder.decode(ncm_data)
        if audio_data:
            self.ctx.logger.info(f"[麦麦解析] 解码成功: {source_name}, 大小: {len(audio_data)} bytes")
        else:
            self.ctx.logger.warning(f"[麦麦解析] 解码失败: {source_name}")
        return audio_data

    async def _send_decoded_file(
        self,
        stream_id: str,
        file_path: str,
        file_name: str,
        user_id: int,
        group_id: Optional[int] = None,
    ) -> bool:
        self.ctx.logger.info(f"[麦麦解析] 准备发送文件: {file_name}, 目标: user_id={user_id}, group_id={group_id}")
        if group_id:
            file_id = await self._file_sender.upload_group_file(group_id, file_path, file_name)
            if not file_id:
                self.ctx.logger.error("[麦麦解析] 群文件上传失败，未获取到 file_id")
                return False
            self.ctx.logger.info(f"[麦麦解析] 群文件上传成功: file_id={file_id}")
            ok = await self._file_sender.send_group_file(stream_id, group_id, file_id)
        else:
            file_id = await self._file_sender.upload_private_file(user_id, file_path, file_name)
            if not file_id:
                self.ctx.logger.error("[麦麦解析] 私聊文件上传失败，未获取到 file_id")
                return False
            self.ctx.logger.info(f"[麦麦解析] 私聊文件上传成功: file_id={file_id}")
            ok = await self._file_sender.send_private_file(stream_id, user_id, file_id)

        # 无论成功或失败，都清理本次生成的临时文件（保留测试 ncm 文件）
        self._clean_cache()
        return ok

    # ===== Hook：拦截文件消息 =====
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

        # 提取文件信息
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
        self.ctx.logger.info(f"[麦麦解析] 收到文件消息: {file_name}")

        if not file_name.lower().endswith(".ncm"):
            self.ctx.logger.info(f"[麦麦解析] 非 .ncm 文件，忽略: {file_name}")
            return None

        # 提取用户和群信息
        user_id = self._get_user_id(message)
        group_id = None
        group_info = message.get("group_info", {}) or message.get("message_info", {}).get("group_info", {})
        group_id = group_info.get("group_id")

        if not user_id:
            self.ctx.logger.warning("[麦麦解析] 无法获取发送者 ID，放弃处理")
            return None

        stream_id = message.get("stream_id") or message.get("session_id") or ""
        if not stream_id and group_id:
            try:
                stream = await self.ctx.chat.get_stream_by_group_id(str(group_id), platform="qq")
                if isinstance(stream, dict):
                    stream_id = stream.get("stream_id") or stream.get("session_id") or ""
            except Exception:
                pass

        self.ctx.logger.info(
            f"[麦麦解析] 开始处理 .ncm 文件: {file_name}, user_id={user_id}, group_id={group_id}, stream_id={stream_id}"
        )

        file_url = file_info.get("url")
        if not file_url:
            self.ctx.logger.warning("[麦麦解析] 文件缺少下载链接")
            await self._send_text(stream_id, "❌ 无法获取文件下载链接")
            return {"action": "abort"}

        # 发送随机提示语
        progress_msg = self._get_random_progress_msg()
        await self._send_text(stream_id, progress_msg)

        # 下载文件
        if self._http_session is None or self._http_session.closed:
            self._http_session = aiohttp.ClientSession()
        try:
            self.ctx.logger.info(f"[麦麦解析] 开始下载: {file_url}")
            async with self._http_session.get(file_url) as resp:
                if resp.status != 200:
                    await self._send_text(stream_id, "❌ 文件下载失败")
                    return {"action": "abort"}
                ncm_data = await resp.read()
                self.ctx.logger.info(f"[麦麦解析] 下载完成，大小: {len(ncm_data)} bytes")
        except Exception as e:
            self.ctx.logger.error(f"[麦麦解析] 下载异常: {e}")
            await self._send_text(stream_id, "❌ 文件下载出错")
            return {"action": "abort"}

        # 解码
        audio_data = await self._do_decode(ncm_data, file_name)
        if not audio_data:
            await self._send_text(stream_id, "❌ 解码失败，文件可能已损坏或不是标准 .ncm 格式")
            return {"action": "abort"}

        ext = self._detect_extension(audio_data)
        safe_name = os.path.splitext(file_name)[0]
        out_name = f"{safe_name}.{ext}"
        out_path = os.path.join(self._cache_dir, out_name)
        with open(out_path, "wb") as f:
            f.write(audio_data)
        self.ctx.logger.info(f"[麦麦解析] 解码文件已保存: {out_path}")

        send_ok = await self._send_decoded_file(
            stream_id=stream_id,
            file_path=out_path,
            file_name=out_name,
            user_id=int(user_id),
            group_id=int(group_id) if group_id else None,
        )
        if not send_ok:
            await self._send_text(stream_id, "❌ 文件发送失败，请稍后重试")

        return None

    # ===== 命令处理器 =====
    @Command("ncm", description="测试解码指定 .ncm 文件并发送给测试账号", pattern=r"^/ncm$")
    async def handle_ncm_test(self, stream_id: str = "", **kwargs):
        """解码测试文件夹内的单个 .ncm 文件并发送给当前用户（需权限）"""
        config = self.config.test
        if not config.enable_test_command:
            await self._send_text(stream_id, "❌ /ncm 测试命令未启用")
            return True, "命令未启用", 0

        # 获取消息对象
        message = kwargs.get("message", {})

        # 使用增强的 ID 提取方法获取发送者 QQ 号
        sender_id = self._get_user_id(message)

        # 测试账号限制
        if config.test_user_id and sender_id != config.test_user_id:
            self.ctx.logger.info(f"[麦麦解析] /ncm 命令被非测试用户触发: {sender_id}")
            await self._send_text(stream_id, "❌ 你没有权限使用此命令")
            return True, "无权限", 0

        test_file_path = self._get_test_file_path()
        if not os.path.isfile(test_file_path):
            self.ctx.logger.warning(f"[麦麦解析] 测试文件不存在: {test_file_path}")
            await self._send_text(stream_id, "❌ 测试文件不存在，请联系管理员")
            return True, "测试文件不存在", 0

        # 读取并解码
        try:
            with open(test_file_path, "rb") as f:
                ncm_data = f.read()
        except Exception as e:
            self.ctx.logger.error(f"[麦麦解析] 读取测试文件失败: {e}")
            await self._send_text(stream_id, "❌ 读取测试文件失败")
            return True, "读取失败", 0

        audio_data = await self._do_decode(ncm_data, os.path.basename(test_file_path))
        if not audio_data:
            await self._send_text(stream_id, "❌ 解码失败")
            return True, "解码失败", 0

        ext = self._detect_extension(audio_data)
        safe_name = os.path.splitext(os.path.basename(test_file_path))[0]
        out_name = f"{safe_name}.{ext}"
        out_path = os.path.join(self._cache_dir, out_name)
        with open(out_path, "wb") as f:
            f.write(audio_data)

        # 发送给当前用户（私聊或群聊），使用当前消息的 stream_id
        user_id = int(sender_id) if sender_id else 0
        group_id = None
        group_info = message.get("group_info", {}) or message.get("message_info", {}).get("group_info", {})
        if group_info:
            group_id = group_info.get("group_id")

        send_ok = await self._send_decoded_file(
            stream_id=stream_id,
            file_path=out_path,
            file_name=out_name,
            user_id=user_id,
            group_id=int(group_id) if group_id else None,
        )
        if send_ok:
            await self._send_text(stream_id, f"✅ 测试解码完成: {out_name}")
        else:
            await self._send_text(stream_id, "❌ 文件发送失败")

        return True, f"解码完成: {out_name}", 1


def create_plugin():
    return NCMaiPlugin()

# try7