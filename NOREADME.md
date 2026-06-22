DeepSeek 专家模式-------------------------------------------------------try1
我（github.com/Emaginations）将要开发一个maibot插件，名字叫做麦麦解析（NCMai），用来解码用户从QQ发送给Maibot的ncm文件。需要提前声明的是：1.本插件、插件产生的文件仅用于技术学习交流，产生的文件请于24h之内删除，不得用于任何商业用途。2.感谢群友termux提供的源代码。

工作流：接收到.ncm格式文件-》建立缓存-》在async函数内解码并发送一句随机表内（含21句正在解码相关的10字内语句含emoji）的消息到对应聊天流-》将解码后的文件缓存-》跟据onebot协议用send_private_msg 发送私聊消息
send_group_msg 发送群消息（或者等我看一下snowluma插件）发回文件-》清理缓存。

现在，请向我普及一下相关的法律知识以及我应该如何改进、选用哪个协议，我将于稍后向你提供所有的插件开发参考文档、解码核心c代码、windows版本的编译器代码、以及我自己的插件示例。

*插件开发参考文档
1.Manifest 系统

每个 MaiBot 插件必须在其根目录下包含一个 _manifest.json 文件，用于声明插件的元信息、版本兼容性、依赖关系和能力需求。Host 侧的 ManifestValidator 会在加载前严格校验此文件。

_manifest.json 与 config.toml 的区别

    _manifest.json：插件元信息（ID、版本、依赖等），由 Host 校验和管理
    config.toml：插件运行时配置（功能开关、参数等），由插件自身读取

两者用途完全不同，不要混淆。
_manifest.json 结构

以下是一个完整的 Manifest 示例：

{
  "manifest_version": 2,
  "id": "com.example.my-plugin",
  "version": "1.0.0",
  "name": "我的插件",
  "description": "一个示例插件",
  "author": {
    "name": "开发者",
    "url": "https://github.com/developer"
  },
  "license": "MIT",
  "urls": {
    "repository": "https://github.com/developer/my-plugin",
    "homepage": "https://example.com",
    "documentation": "https://docs.example.com",
    "issues": "https://github.com/developer/my-plugin/issues"
  },
  "host_application": {
    "min_version": "1.0.0",
    "max_version": "1.99.99"
  },
  "sdk": {
    "min_version": "1.0.0",
    "max_version": "2.99.99"
  },
  "dependencies": [],
  "plugin_type": "tool",
  "display": {
    "icon": {
      "type": "lucide",
      "value": "wrench"
    }
  },
  "capabilities": ["send_message"],
  "i18n": {
    "default_locale": "zh-CN",
    "locales_path": "i18n",
    "supported_locales": ["zh-CN", "en-US"]
  }
}

必填字段

    manifest_version 2 — Manifest 协议版本，当前固定为 2
    id string — 插件唯一标识符，格式为小写字母/数字，以点号或横线分隔（如 com.author.plugin）
    version string — 插件版本号，必须为严格三段式语义版本（如 1.0.0）
    name string — 插件展示名称
    description string — 插件描述
    author object — 插件作者信息，包含 name（作者名）和 url（作者主页，必须为 HTTP/HTTPS URL）
    license string — 插件许可证
    urls object — 插件相关链接集合（见下文）
    host_application object — Host 兼容区间（见下文）
    sdk object — SDK 兼容区间（见下文）
    capabilities string[] — 插件声明的能力请求列表，不允许包含空值
    i18n object — 国际化配置（见下文）

可选字段
plugin_type 插件类型

plugin_type 用于声明插件的主要角色，供 WebUI 展示、筛选和默认图标选择使用。该字段为可选字段，不需要升级 manifest_version；缺省时按 extension 处理。

可选值：

    adapter — 消息平台或协议适配器
    tool — 工具、命令或模型可调用能力
    provider — LLM、TTS、API 等服务提供方
    management — 管理、权限、群管或后台类插件
    data — 统计、记忆、知识库、导入导出等数据类插件
    media — 图片、语音、视频、表情等媒体处理
    game — 游戏或娱乐互动
    integration — 外部平台、搜索、Webhook 等集成
    extension — 通用扩展
    other — 其他

display 展示元信息

display.icon 用于声明插件图标。该字段只影响 WebUI 展示，不参与插件运行时行为。

{
  "display": {
    "icon": {
      "type": "local",
      "value": "assets/icon.png",
      "fallback": "package",
      "background": "#1f2937"
    }
  }
}

    type: lucide、emoji 或 local
    value: 图标值。lucide 使用图标名，emoji 使用单个表情或短文本，local 使用插件目录内相对路径
    fallback: 可选，图标加载失败时使用的 lucide 图标名
    background: 可选，图标背景色，格式为 #RRGGBB

不允许使用在线 URL 作为插件图标。本地图标仅支持 .png、.jpg、.jpeg、.webp、.svg，路径必须位于插件目录内，不能使用绝对路径、.. 或符号链接。
urls 链接集合

    repository · 必填 — 插件仓库地址，必须为 HTTP/HTTPS URL
    homepage · 可选 — 插件主页地址
    documentation · 可选 — 插件文档地址
    issues · 可选 — 插件问题反馈地址

host_application / sdk 版本区间

两者结构相同，为闭区间声明：

{
  "min_version": "1.0.0",
  "max_version": "1.99.99"
}

    min_version：允许的最低版本（闭区间）
    max_version：允许的最高版本（闭区间）
    两者均必须为严格三段式语义版本号（X.Y.Z）
    min_version 不能大于 max_version

Host 在握手阶段会校验当前版本是否落在声明区间内。若不兼容，插件将被阻止加载。
i18n 国际化配置

    default_locale · 必填 — 默认语言代码（如 zh-CN）
    locales_path · 可选 — 语言资源文件目录路径
    supported_locales · 可选 — 支持的语言列表，不可包含空值和重复项。若非空，则 default_locale 必须存在于该列表中

llm_providers LLM Provider 声明

声明插件提供的 LLM Provider 能力，供其他插件通过 ctx.llm 代理调用。

    client_type · 必填 — Provider 唯一标识符，必须与 @LLMProvider 装饰器中声明的值完全一致
    name · 必填 — Provider 展示名称
    description · 可选 — Provider 功能描述
    version · 可选 · 默认 "1.0.0" — Provider 版本号

双重声明要求

llm_providers 字段与 @LLMProvider 装饰器必须同时声明，且 client_type 必须完全匹配。若仅在一处声明，另一处缺失或不一致，插件将被阻止加载。

冲突加载策略

若两个插件声明了相同的 client_type，则两个插件均被禁止加载。请在设计 Provider 时使用唯一的前缀（如 com.example.my-provider）避免冲突。

{
  "llm_providers": [
    {
      "client_type": "my_custom_llm",
      "name": "My Custom LLM",
      "description": "A custom LLM provider",
      "version": "1.0.0"
    }
  ]
}

依赖声明

dependencies 数组支持两种类型的依赖，通过 type 字段区分：
插件级依赖

{
  "type": "plugin",
  "id": "com.example.other-plugin",
  "version_spec": ">=1.0.0,<2.0.0"
}

    id：依赖插件的 ID，遵循与插件 ID 相同的格式规则
    version_spec：版本约束表达式，使用 PEP 440 风格（如 >=1.0.0、~=1.0）
    不允许循环依赖或依赖自身
    不允许重复声明同一个插件依赖

Python 包依赖

{
  "type": "python_package",
  "name": "httpx",
  "version_spec": ">=0.24.0"
}

    name：Python 包名，仅允许字母、数字、点号、下划线和横线
    version_spec：版本约束表达式

依赖解析流程

PluginDependencyPipeline 在 Host 侧统一执行依赖分析：

    扫描：收集所有插件的 _manifest.json
    检测 Host 冲突：若插件的 Python 包依赖与主程序的依赖约束无交集，则阻止加载
    检测插件间冲突：若多个插件对同一 Python 包的版本约束互斥，则全部阻止加载
    自动安装：对可加载插件缺失的 Python 依赖，优先使用 uv pip install，回退到 pip install
    拓扑排序：根据跨 Supervisor 依赖关系决定 Runner 启动顺序，循环依赖将被拒绝

校验规则

Manifest 校验器（ManifestValidator）采用 Pydantic 严格模式，主要校验规则包括：

    禁止多余字段：不允许出现 _manifest.json 未声明的字段
    ID 格式：必须匹配 ^[a-z0-9]+(?:[.-][a-z0-9]+)+$（如 com.example.my-plugin）
    版本号格式：必须为 X.Y.Z 三段式
    URL 格式：必须以 http:// 或 https:// 开头
    不允许自依赖：dependencies 中不能依赖自身
    不允许重复依赖：同一插件/包名只能声明一次
2.生命周期

MaiBot 插件有三个生命周期方法：on_load()、on_unload() 和 on_config_update()。SDK 强制要求所有插件实现这三个方法，否则 Runner 会拒绝加载。
create_plugin() 工厂函数

每个插件的 plugin.py 必须导出一个顶层 create_plugin() 函数，返回插件实例：

from maibot_sdk import MaiBotPlugin


class MyPlugin(MaiBotPlugin):
    async def on_load(self) -> None:
        ...

    async def on_unload(self) -> None:
        ...

    async def on_config_update(self, scope: str, config_data: dict, version: str) -> None:
        ...


def create_plugin():
    return MyPlugin()

Runner 加载插件时：

    导入 plugin.py 模块
    调用 create_plugin() 获取插件实例
    注入 PluginContext（此时 self.ctx 可用）
    调用 on_load()

on_load()

插件加载完成后的回调。Runner 在注入 PluginContext 并完成 capability bootstrap 之后才调用此方法，因此可以在 on_load() 中直接使用 self.ctx 的所有能力代理。

async def on_load(self) -> None:
    """Called after plugin loaded. Initialize resources here.

    Runner has already injected PluginContext before calling this,
    so self.ctx is available.
    """

典型用途：

    初始化插件内部状态
    调用 self.ctx.gateway.update_state() 上报消息网关状态
    调用 self.register_dynamic_api() 注册动态 API 并 await self.sync_dynamic_apis()
    读取配置并初始化资源

示例：

from maibot_sdk import MaiBotPlugin, PluginConfigBase, Field


class MyConfig(PluginConfigBase):
    greeting: str = Field(default="你好！", description="默认问候语")


class MyPlugin(MaiBotPlugin):
    config_model = MyConfig

    async def on_load(self) -> None:
        # self.ctx 已经注入，可以直接使用
        self.ctx.logger.info("插件已加载，当前问候语: %s", self.config.greeting)

        # 可以在这里注册动态 API
        self.register_dynamic_api(
            "my_api",
            self._handle_api,
            description="示例 API",
            version="1",
            public=True,
        )
        await self.sync_dynamic_apis()

    async def _handle_api(self, **kwargs):
        return {"status": "ok"}

on_unload()

插件卸载前的回调。在此方法中释放插件持有的所有资源。

async def on_unload(self) -> None:
    """Called before plugin unloaded. Cleanup resources."""

典型用途：

    关闭网络连接、文件句柄
    上报网关离线状态（self.ctx.gateway.update_state(..., ready=False)）
    注销动态 API
    保存持久化数据

示例：

class MyPlugin(MaiBotPlugin):
    async def on_unload(self) -> None:
        self.ctx.logger.info("插件正在卸载")

        # 上报消息网关离线
        await self.ctx.gateway.update_state(
            gateway_name="my_gateway",
            ready=False,
        )

        # 清空动态 API
        self.clear_dynamic_apis()
        await self.sync_dynamic_apis(offline_reason="插件已卸载")

注意

on_unload() 中仍然可以使用 self.ctx，但应尽快完成清理工作，不要执行耗时操作。
on_config_update()

配置热重载回调。当插件配置或已订阅的全局配置发生变化时，Runner 会调用此方法。

async def on_config_update(
    self,
    scope: str,
    config_data: dict[str, Any],
    version: str,
) -> None:
    """Called when config hot-reloads.

    Args:
        scope: 配置变更范围，取值为 "self"、"bot" 或 "model"。
        config_data: 当前范围对应的最新配置数据。
        version: 配置版本号。
    """

scope 取值

    "self" → CONFIG_RELOAD_SCOPE_SELF — 插件自身配置。插件目录下的 config.toml 变化时始终触发，无需订阅
    "bot" → ON_BOT_CONFIG_RELOAD — 全局 Bot 配置。需要通过 config_reload_subscriptions 订阅
    "model" → ON_MODEL_CONFIG_RELOAD — LLM 模型配置。需要通过 config_reload_subscriptions 订阅

::: important

    scope == "self" 的回调始终触发，不需要额外订阅
    scope == "bot" 和 scope == "model" 只有在 config_reload_subscriptions 中声明后才会触发 :::

示例

from maibot_sdk import MaiBotPlugin, CONFIG_RELOAD_SCOPE_SELF, ON_BOT_CONFIG_RELOAD, ON_MODEL_CONFIG_RELOAD
from typing import ClassVar, Iterable


class MyPlugin(MaiBotPlugin):
    # 订阅 bot 和 model 两种全局配置的热重载
    config_reload_subscriptions: ClassVar[Iterable[str]] = ("bot", "model")

    async def on_load(self) -> None:
        self.ctx.logger.info("插件已加载")

    async def on_unload(self) -> None:
        self.ctx.logger.info("插件已卸载")

    async def on_config_update(self, scope: str, config_data: dict, version: str) -> None:
        if scope == CONFIG_RELOAD_SCOPE_SELF:
            # 插件自身配置变化，self.config 会自动更新
            self.ctx.logger.info("插件配置已更新: version=%s", version)
        elif scope == ON_BOT_CONFIG_RELOAD:
            # 全局 Bot 配置变化
            bot_name = config_data.get("bot_name", "未知")
            self.ctx.logger.info("Bot 配置已更新: bot_name=%s, version=%s", bot_name, version)
        elif scope == ON_MODEL_CONFIG_RELOAD:
            # LLM 模型配置变化
            model_name = config_data.get("model_name", "未知")
            self.ctx.logger.info("模型配置已更新: model=%s, version=%s", model_name, version)

config_reload_subscriptions

类变量，声明插件需要订阅的全局配置热重载范围。仅支持 "bot" 和 "model" 两个值：

from typing import ClassVar, Iterable


class MyPlugin(MaiBotPlugin):
    # 订阅两种全局配置
    config_reload_subscriptions: ClassVar[Iterable[str]] = ("bot", "model")

    # 仅订阅 Bot 配置
    # config_reload_subscriptions: ClassVar[Iterable[str]] = ("bot",)

    # 仅订阅 Model 配置
    # config_reload_subscriptions: ClassVar[Iterable[str]] = ("model",)

    # 不订阅任何全局配置（默认值）
    # config_reload_subscriptions: ClassVar[Iterable[str]] = ()

规则：

    默认值为空元组 ()，即不订阅任何全局配置
    "self" 范围始终触发回调，不需要也不能在此声明
    仅 "bot" 和 "model" 是有效的订阅值
    声明不支持的值会在 get_config_reload_subscriptions() 中抛出 ValueError
    不能直接传入字符串（如 config_reload_subscriptions = "bot"），必须使用可迭代集合

完整生命周期示例

以下是一个包含所有生命周期方法的完整插件示例：

from typing import Any, ClassVar

from maibot_sdk import (
    CONFIG_RELOAD_SCOPE_SELF,
    Command,
    MaiBotPlugin,
    ON_BOT_CONFIG_RELOAD,
    ON_MODEL_CONFIG_RELOAD,
    Tool,
)
from maibot_sdk.types import ToolParameterInfo, ToolParamType


class GreeterPlugin(MaiBotPlugin):
    """问候插件 —— 演示完整的插件生命周期。"""

    # 订阅全局配置热重载
    config_reload_subscriptions: ClassVar[Iterable[str]] = ("bot", "model")

    async def on_load(self) -> None:
        """插件加载时初始化。"""
        self.ctx.logger.info("GreeterPlugin 已加载")
        # self.ctx 在此已经可用，可以直接调用能力代理
        raw_config = self.get_plugin_config_data()
        self.ctx.logger.info("当前配置: %s", raw_config)

    async def on_unload(self) -> None:
        """插件卸载时清理资源。"""
        self.ctx.logger.info("GreeterPlugin 正在卸载")

    async def on_config_update(self, scope: str, config_data: dict[str, Any], version: str) -> None:
        """处理配置热更新。"""
        if scope == CONFIG_RELOAD_SCOPE_SELF:
            self.ctx.logger.info("插件配置已更新: version=%s", version)
        elif scope == ON_BOT_CONFIG_RELOAD:
            self.ctx.logger.info("Bot 配置已更新: version=%s", version)
        elif scope == ON_MODEL_CONFIG_RELOAD:
            self.ctx.logger.info("Model 配置已更新: version=%s", version)

    @Tool(
        "greet",
        brief_description="向用户打招呼",
        detailed_description="参数说明：\n- stream_id：string，必填。当前聊天流 ID。",
        parameters=[
            ToolParameterInfo(
                name="stream_id",
                param_type=ToolParamType.STRING,
                description="当前聊天流 ID",
                required=True,
            ),
        ],
    )
    async def handle_greet(self, stream_id: str, **kwargs):
        await self.ctx.send.text("你好！", stream_id)
        return {"success": True, "message": "已回复"}

    @Command("hello", pattern=r"^/hello")
    async def handle_hello(self, **kwargs):
        await self.ctx.send.text("Hello!", kwargs["stream_id"])
        return True, "Hello!", 2


def create_plugin():
    return GreeterPlugin()
3.配置管理(WebUI构建)

MaiBot 插件支持声明式的配置管理机制，通过 PluginConfigBase 和 Field 定义强类型配置模型，Runner 会自动生成默认配置、补齐缺失字段，并向 WebUI 暴露可渲染的配置 Schema。
配置文件位置

每个插件的配置文件位于插件目录下的 config.toml：

my_plugin/
├── plugin.py          # 插件入口
├── config.toml        # 插件配置（可选）
└── _manifest.json     # 插件元信息

config.toml vs _manifest.json

    config.toml：插件的运行时配置（功能开关、参数等），由插件自身读取
    _manifest.json：插件的元信息（ID、版本、依赖等），由 Host 校验和管理

两者用途完全不同，不要混淆。
PluginConfigBase 配置模型
基本用法

from maibot_sdk import MaiBotPlugin, PluginConfigBase, Field


class MyPluginConfig(PluginConfigBase):
    """插件完整配置"""
    __ui_label__ = "插件配置"

    enabled: bool = Field(default=True, description="是否启用插件")
    greeting: str = Field(default="你好！", description="默认问候语")
    max_retries: int = Field(default=3, description="最大重试次数")


class MyPlugin(MaiBotPlugin):
    config_model = MyPluginConfig

    async def on_load(self) -> None:
        # 通过 self.config 访问强类型配置
        self.ctx.logger.info("当前问候语: %s", self.config.greeting)
        self.ctx.logger.info("最大重试: %d", self.config.max_retries)

嵌套配置

通过嵌套 PluginConfigBase 类实现分组配置：

from maibot_sdk import MaiBotPlugin, PluginConfigBase, Field


class PluginSection(PluginConfigBase):
    """插件基础配置"""
    __ui_label__ = "基础设置"

    enabled: bool = Field(default=True, description="是否启用插件")
    greeting: str = Field(default="你好！", description="默认问候语")


class AdvancedSection(PluginConfigBase):
    """高级配置"""
    __ui_label__ = "高级设置"

    max_retries: int = Field(default=3, description="最大重试次数")
    timeout: float = Field(default=30.0, description="超时时间（秒）")


class MyPluginConfig(PluginConfigBase):
    """插件完整配置"""
    plugin: PluginSection = Field(default_factory=PluginSection)
    advanced: AdvancedSection = Field(default_factory=AdvancedSection)


class MyPlugin(MaiBotPlugin):
    config_model = MyPluginConfig

    async def on_load(self) -> None:
        # 访问嵌套配置
        self.ctx.logger.info("问候语: %s", self.config.plugin.greeting)
        self.ctx.logger.info("超时: %s", self.config.advanced.timeout)

Field 字段

Field 用于声明配置字段的元数据：

from maibot_sdk import Field

Field(
    default=...,          # 默认值
    default_factory=...,   # 默认值工厂函数（用于可变默认值）
    description="...",     # 字段描述（显示在 WebUI 中）
)

    default Any — 字段默认值
    default_factory Callable — 默认值工厂函数，用于 list、dict、嵌套 PluginConfigBase 等可变类型
    description str — 字段描述，WebUI 中显示为表单标签
    json_schema_extra dict — 额外元数据，传递给 WebUI Schema 生成器。常用键: placeholder（输入框占位符文本）、group（UI 分组提示）

ui_label

PluginConfigBase 子类可通过 __ui_label__ 类属性设置在 WebUI 中显示的分组标题：

class PluginSection(PluginConfigBase):
    __ui_label__ = "基础设置"  # WebUI 中显示的标题
    enabled: bool = Field(default=True, description="是否启用插件")

ui_icon

PluginConfigBase 子类可通过 __ui_icon__ 类属性设置在 WebUI 中显示的分组图标，接受 Material Icons 图标名称：

class PluginSection(PluginConfigBase):
    __ui_label__ = "基础设置"
    __ui_icon__ = "settings"  # WebUI 中显示的 Material Icons 图标名
    enabled: bool = Field(default=True, description="是否启用插件")

ui_order

PluginConfigBase 子类可通过 __ui_order__ 类属性设置分组在 WebUI 中的显示顺序，数值越小越靠前：

class PluginSection(PluginConfigBase):
    __ui_label__ = "基础设置"
    __ui_icon__ = "settings"
    __ui_order__ = 0  # WebUI 中分组的排序权重，数字越小越靠前
    enabled: bool = Field(default=True, description="是否启用插件")

json_schema_extra

json_schema_extra 用于传递额外元数据给 WebUI Schema 生成器，常用场景包括：

    placeholder：输入框的占位符提示文本
    group：WebUI 中的配置分组提示

class MyPluginConfig(PluginConfigBase):
    """插件完整配置"""
    greeting: str = Field(
        default="你好！",
        description="默认问候语",
        json_schema_extra={"placeholder": "请输入问候语", "group": "basic"}
    )
    api_key: str = Field(
        default="",
        description="API 密钥",
        json_schema_extra={"placeholder": "请输入 API Key", "group": "advanced"}
    )

访问配置
强类型访问（self.config）

class MyPlugin(MaiBotPlugin):
    config_model = MyPluginConfig

    async def on_load(self) -> None:
        # 强类型访问，有代码补全和类型检查
        greeting = self.config.plugin.greeting
        timeout = self.config.advanced.timeout

注意

    未声明 config_model 时调用 self.config 会抛出 RuntimeError
    配置尚未注入时调用 self.config 也会抛出 RuntimeError

原始字典访问

class MyPlugin(MaiBotPlugin):
    config_model = MyPluginConfig

    async def on_load(self) -> None:
        # 获取原始配置字典
        raw = self.get_plugin_config_data()
        greeting = raw.get("plugin", {}).get("greeting", "默认值")

get_plugin_config_data() 始终可用，返回 dict[str, Any]，无需声明 config_model。
配置热重载

当 config.toml 文件变更时，Runner 会自动触发 on_config_update() 回调：

from maibot_sdk import MaiBotPlugin, CONFIG_RELOAD_SCOPE_SELF

class MyPlugin(MaiBotPlugin):
    config_model = MyPluginConfig

    async def on_config_update(self, scope: str, config_data: dict, version: str) -> None:
        if scope == CONFIG_RELOAD_SCOPE_SELF:
            # self.config 会自动更新为最新值
            self.ctx.logger.info("配置已更新，新问候语: %s", self.config.plugin.greeting)

::: important self.config 在 on_config_update(scope="self") 调用时已自动更新，无需手动重新读取。 :::

更多关于配置热重载的内容，参见 生命周期。
config.toml 格式

配置文件使用 TOML 格式，与 PluginConfigBase 的嵌套结构对应：

[plugin]
config_version = "1.0.0"
enabled = true
greeting = "你好！"

[advanced]
max_retries = 3
timeout = 30.0

config_version

config_version 是一个特殊字段，用于跟踪配置版本。Runner 在合并默认配置时会保留此字段。
默认配置与 Schema 生成
自动补齐

当 config.toml 中缺少某些字段时，Runner 会根据 config_model 的默认值自动补齐：

# 如果 config.toml 只有:
# [plugin]
# enabled = false

# Runner 会自动补齐 greeting 和 advanced 部分的默认值

WebUI Schema

声明 config_model 后，Runner 会自动生成 WebUI 可渲染的配置 Schema：

# 插件类上的方法（通常不需要手动调用）
schema = MyPlugin.build_config_schema(
    plugin_id="com.example.my-plugin",
    plugin_name="我的插件",
    plugin_version="1.0.0",
)

WebUI 会根据 Schema 渲染配置表单，用户可以在浏览器中直接编辑配置。
通过 API 读取配置

除了通过 self.config 和 self.get_plugin_config_data() 外，还可以通过能力代理读取配置：

# 读取插件自身配置
value = await self.ctx.config.get("plugin.greeting")

# 读取其他插件配置
value = await self.ctx.config.get_plugin("com.other.plugin")

# 读取全局 Bot 配置
all_config = await self.ctx.config.get_all()

不使用 config_model

如果插件配置非常简单，可以不声明 config_model，直接使用 ctx.config 和 get_plugin_config_data()：

class SimplePlugin(MaiBotPlugin):
    # 不声明 config_model

    async def on_load(self) -> None:
        # 只能通过原始字典或 ctx.config 读取
        raw = self.get_plugin_config_data()
        name = raw.get("name", "默认名称")

        # self.config 会抛出 RuntimeError
        # 不要调用 self.config

但建议始终使用 config_model，以获得更好的类型安全和 WebUI 集成体验。
4.Tool 组件

@Tool 是 MaiBot 插件系统中最核心的组件类型。它允许插件向 LLM 暴露可调用的工具函数，使 LLM 能够在推理过程中主动调用外部能力——例如搜索知识库、查询数据库、调用外部 API 等。

Tool vs Action

@Action 是旧版装饰器，SDK 内部会自动将其转换为 @Tool 声明。新插件应直接使用 @Tool，不再使用 @Action。详见 Action 组件（Legacy）。
装饰器签名

from maibot_sdk import Tool
from maibot_sdk.types import ToolParameterInfo, ToolParamType

@Tool(
    name: str,                                              # 工具名称（必填）
    description: str = "",                                  # 工具描述，作为备选描述字段
    brief_description: str = "",                            # 简要描述，优先级高于 description
    detailed_description: str = "",                         # 详细描述，可包含参数说明等
    parameters: list[ToolParameterInfo] | dict | None = None,  # 参数定义
    **metadata,                                             # 额外元数据
)

参数说明

    name str — 工具名称，需在插件内唯一。LLM 通过此名称调用工具
    description str — 工具备选描述。当 brief_description 为空时使用此字段
    brief_description str — 工具主描述（优先使用）。传给 LLM 的工具描述摘要，帮助 LLM 判断是否需要调用
    detailed_description str — 详细描述，可包含参数使用说明、注意事项等。SDK 会自动合并参数 Schema 生成完整描述
    parameters list | dict | None — 工具参数定义，支持两种格式（见下文）

描述字段约定：

    description：关于工具的描述，包括使用方法，使用情景，注意事项。当 brief_description 为空时，description 会作为回退描述。
    brief_description：给主程序或小模型快速判断"这个工具是做什么的"的简要描述
    detailed_description：描述参数、必填项、可选项和调用约束的详细描述

参数定义
方式一：结构化参数（推荐）

使用 ToolParameterInfo 列表声明参数，SDK 会自动生成 JSON Schema：

from maibot_sdk import Tool, MaiBotPlugin
from maibot_sdk.types import ToolParameterInfo, ToolParamType

class MyPlugin(MaiBotPlugin):
    @Tool(
        "search",
        brief_description="搜索互联网获取信息",
        detailed_description="使用搜索引擎查找相关信息。参数说明：\n- query：string，必填。搜索关键词。\n- limit：integer，可选。返回结果数量上限。",
        parameters=[
            ToolParameterInfo(
                name="query",
                param_type=ToolParamType.STRING,
                description="搜索关键词",
                required=True,
            ),
            ToolParameterInfo(
                name="limit",
                param_type=ToolParamType.INTEGER,
                description="返回结果数量上限",
                required=False,
                default=5,
            ),
        ],
    )
    async def handle_search(self, query: str, limit: int = 5, **kwargs):
        results = await self._do_search(query, limit)
        return {"results": results}

方式二：dict 参数（兼容旧式声明）

直接传入 JSON Schema 风格的字典：

class MyPlugin(MaiBotPlugin):
    @Tool(
        "search",
        brief_description="搜索互联网获取信息",
        parameters={
            "query": {"type": "string", "description": "搜索关键词"},
            "limit": {"type": "integer", "description": "返回结果数量上限", "default": 5},
        },
    )
    async def handle_search(self, query: str, limit: int = 5, **kwargs):
        results = await self._do_search(query, limit)
        return {"results": results}

ToolParameterInfo 字段

    name str — 参数名称
    param_type ToolParamType — 参数类型枚举
    description str — 参数描述
    required bool · 默认 True — 是否必填
    enum_values list | None — 可选枚举值列表
    default Any — 默认值
    items_schema dict | None — 数组元素 Schema（当 param_type=ARRAY 时使用）
    properties dict | None — 对象属性定义（当 param_type=OBJECT 时使用）
    required_properties list[str] — 对象内部必填字段
    additional_properties bool | dict | None — 是否允许额外字段

ToolParamType 枚举

    STRING → JSON Schema string — 字符串
    INTEGER → JSON Schema integer — 整数
    NUMBER → JSON Schema number — 数字（整数或浮点数）
    FLOAT → JSON Schema number — 浮点数（等价于 NUMBER）
    BOOLEAN → JSON Schema boolean — 布尔值
    ARRAY → JSON Schema array — 数组
    OBJECT → JSON Schema object — 对象

处理函数

Tool 处理函数是插件类上的异步方法，接收与参数名对应的具名参数和 **kwargs：

@Tool("greet", description="向用户打招呼",
      parameters=[
          ToolParameterInfo(name="stream_id", param_type=ToolParamType.STRING,
                          description="当前聊天流 ID", required=True),
      ])
async def handle_greet(self, stream_id: str, **kwargs):
    await self.ctx.send.text("你好！", stream_id)
    return {"success": True, "message": "已回复"}

返回值

Tool 处理函数的返回值会作为工具执行结果返回给 LLM。返回值可以是：

    dict：推荐，LLM 可以理解结构化数据
    str：简单文本结果
    其他可序列化的值

LLM 会根据返回值决定下一步操作（如向用户回复、调用其他工具等）。
返回图片和其他媒体

如果 Tool 需要把图片交给 Maisaka 继续观察或推理，不要把图片 base64 直接塞进 content。推荐返回 dict，将给 LLM 阅读的文字放在 content，将图片本体放在 content_items：

from base64 import b64encode


async def handle_draw(self, prompt: str, **kwargs):
    image_bytes = await self._draw_image(prompt)

    return {
        "success": True,
        "content": "图片已生成，请查看索引对应的图片内容。",
        "content_items": [
            {
                "type": "image",
                "data": b64encode(image_bytes).decode("ascii"),
                "mime_type": "image/png",
                "name": "result.png",
                "description": "根据提示词生成的图片",
            }
        ],
    }

也可以使用 data URL：

return {
    "success": True,
    "content": "图片已生成。",
    "content_items": [
        {
            "type": "image",
            "uri": f"data:image/png;base64,{b64encode(image_bytes).decode('ascii')}",
            "mime_type": "image/png",
            "name": "result.png",
        }
    ],
}

content_items 中常用字段如下：

    type / content_type str — 内容类型。图片使用 image；也支持 audio、resource_link、resource、binary
    data / base64 str — 媒体二进制的 base64 字符串，推荐图片直接使用这个字段
    uri str — 媒体 URI。图片可使用 data:image/...;base64,...
    mime_type str — MIME 类型，例如 image/png、image/jpeg、image/webp
    name str — 文件名或展示名称
    description str — 对媒体内容的简短说明
    metadata dict — 额外元数据

Maisaka 会把这类返回拆成两种上下文消息：第一条仍是纯文本 Tool Result，其中包含类似 tool_result:<tool_call_id>:1 的媒体索引；随后追加一条普通 user message，里面放入同一索引和真实图片组件。这样可以兼容不支持在 tool result 中直接回传图片的模型 API，同时让支持视觉输入的模型按普通图片消息观察图片。

视图逻辑

拆出来的图片在 LLM 输入和 Prompt 预览里会走普通 ImageComponent 的展示逻辑，和真实收到的图片消息基本一致。区别是它的来源会标记为 tool_result_media，消息 ID 是工具媒体索引，不会被当作真实用户发来的平台消息。
kwargs 中常见的额外参数

    stream_id str — 当前聊天流 ID，可用于 ctx.send.text() 等发送消息
    message dict — 触发此工具调用的原始消息

stream_id

stream_id 是 Tool 组件中最重要的参数之一，它标识了当前对话流。使用 ctx.send.text("消息", stream_id) 可以将消息发送到对应的聊天流中。
描述生成规则

SDK 会自动为工具生成完整的描述信息，优先级如下：

    brief_description：优先使用（如果提供）
    description：降级回退（brief_description 为空时使用）
    detailed_description：如果提供了，SDK 会将其与参数 Schema 合并生成完整描述
    自动生成：如果上述字段都未提供，SDK 会使用 "工具 {name}" 作为描述

自动生成的参数说明格式为：

参数说明：
- query：string，必填。搜索关键词
- limit：integer，可选。返回结果数量上限。默认值：5

完整示例

from typing import Any

from maibot_sdk import MaiBotPlugin, Tool
from maibot_sdk.types import ToolParameterInfo, ToolParamType


class SearchPlugin(MaiBotPlugin):
    async def on_load(self) -> None:
        self.ctx.logger.info("搜索插件已加载")

    async def on_unload(self) -> None:
        pass

    async def on_config_update(self, scope: str, config_data: dict, version: str) -> None:
        pass

    @Tool(
        "search_web",
        description="搜索互联网获取信息",
        parameters=[
            ToolParameterInfo(
                name="query",
                param_type=ToolParamType.STRING,
                description="搜索关键词",
                required=True,
            ),
            ToolParameterInfo(
                name="limit",
                param_type=ToolParamType.INTEGER,
                description="返回结果数量上限",
                required=False,
                default=5,
            ),
        ],
    )
    async def search(self, query: str, limit: int = 5, **kwargs):
        """搜索互联网"""
        results = await self._do_search(query, limit)
        return {"results": results, "count": len(results)}

    @Tool(
        "get_weather",
        description="获取指定城市的天气信息",
        parameters=[
            ToolParameterInfo(
                name="city",
                param_type=ToolParamType.STRING,
                description="城市名称",
                required=True,
            ),
        ],
    )
    async def get_weather(self, city: str, **kwargs):
        """查询天气"""
        weather = await self._fetch_weather(city)
        return {"city": city, "weather": weather}

    async def _do_search(self, query: str, limit: int) -> list:
        # 实际搜索逻辑
        return []

    async def _fetch_weather(self, city: str) -> dict:
        # 实际天气查询逻辑
        return {}


def create_plugin():
    return SearchPlugin()
5.Command 组件

@Command 是基于正则匹配的命令组件。当用户发送的消息匹配到某个 Command 的正则模式时，MaiBot 会调度执行对应的 Command 处理函数。
装饰器签名

from maibot_sdk import Command

@Command(
    name: str,                    # 命令名称（必填）
    description: str = "",        # 命令描述
    pattern: str = "",            # 正则匹配模式
    aliases: list[str] | None = None,  # 命令别名列表
    **metadata,                   # 额外元数据
)

参数说明

    name str — 命令名称，需在插件内唯一
    description str — 命令描述
    pattern str — 正则匹配模式字符串。当用户消息匹配此模式时，触发该命令
    aliases list[str] | None — 命令别名列表，提供额外的触发方式

基本用法

from maibot_sdk import MaiBotPlugin, Command


class MyPlugin(MaiBotPlugin):
    @Command("hello", pattern=r"^/hello")
    async def handle_hello(self, **kwargs):
        await self.ctx.send.text("Hello!", kwargs["stream_id"])
        return True, "Hello!", 2

带别名的命令

@Command("greet", pattern=r"^/greet", aliases=["/hi", "/hey"])
async def handle_greet(self, **kwargs):
    await self.ctx.send.text("你好！", kwargs["stream_id"])
    return True, "你好！", 2

使用 /greet、/hi 或 /hey 均可触发此命令。
带正则捕获组的命令

import re

@Command("echo", pattern=r"^/echo\s+(?P<text>.+)$")
async def handle_echo(self, **kwargs):
    matched = kwargs.get("matched_groups", {})
    text = matched.get("text", "").strip()
    stream_id = kwargs["stream_id"]
    await self.ctx.send.text(f"Echo: {text}", stream_id)
    return True, f"Echo: {text}", 1

处理函数参数

Command 处理函数接收 **kwargs，其中包含以下参数：

    stream_id str — 当前聊天流 ID，用于发送消息
    matched_groups dict — 正则命名捕获组的匹配结果
    raw_message str — 用户发送的原始消息文本
    message dict — 完整的消息对象

返回值

Command 处理函数必须返回三元组：

return success, response, weight

    success bool — 命令是否成功执行
    response str — 命令执行结果的文本描述
    weight int — 命令优先级权重，数值越高优先级越高

# 命令成功执行
return True, "操作成功", 2

# 命令执行失败
return False, "参数错误", 1

正则模式编写指南
推荐模式

# 精确匹配 /hello
pattern=r"^/hello$"

# 匹配 /hello 加可选参数
pattern=r"^/hello(?P<name>.+)?$"

# 匹配 /echo 加必填参数
pattern=r"^/echo\s+(?P<text>.+)$"

# 匹配 /set 加键值对
pattern=r"^/set\s+(?P<key>\w+)\s+(?P<value>.+)$"

使用命名捕获组

推荐使用 (?P<name>...) 命名捕获组，可以通过 kwargs["matched_groups"] 按名称访问匹配结果：

@Command("ban", pattern=r"^/ban\s+(?P<user>\w+)(?:\s+(?P<reason>.+))?$")
async def handle_ban(self, **kwargs):
    matched = kwargs.get("matched_groups", {})
    user = matched.get("user", "")
    reason = matched.get("reason", "无原因")
    await self.ctx.send.text(f"已封禁 {user}，原因：{reason}", kwargs["stream_id"])
    return True, f"已封禁 {user}", 2

命令执行流程
插件Runner 子进程Host 主进程用户插件Runner 子进程Host 主进程用户发送消息正则匹配命令invoke_plugin(command)调用 Command 处理函数执行命令逻辑返回 (success, response, weight)返回结果
命令相关 Hook

命令执行前后有内置 Hook 点可供 @HookHandler 订阅：

    chat.command.before_execute：命令执行前触发，可中止或改写参数
    chat.command.after_execute：命令执行后触发，可改写返回结果

完整示例

from maibot_sdk import MaiBotPlugin, Command, Tool
from maibot_sdk.types import ToolParameterInfo, ToolParamType


class AdminPlugin(MaiBotPlugin):
    async def on_load(self) -> None:
        self.ctx.logger.info("管理插件已加载")

    async def on_unload(self) -> None:
        pass

    async def on_config_update(self, scope: str, config_data: dict, version: str) -> None:
        pass

    @Command("status", pattern=r"^/status$")
    async def handle_status(self, **kwargs):
        """查看系统状态"""
        stream_id = kwargs["stream_id"]
        await self.ctx.send.text("系统运行正常 ✅", stream_id)
        return True, "系统运行正常", 1

    @Command("echo", pattern=r"^/echo\s+(?P<text>.+)$")
    async def handle_echo(self, **kwargs):
        """回显消息"""
        matched = kwargs.get("matched_groups", {})
        text = matched.get("text", "").strip()
        stream_id = kwargs["stream_id"]
        await self.ctx.send.text(text, stream_id)
        return True, text, 1

    @Command("help", pattern=r"^/help$", aliases=["/帮助"])
    async def handle_help(self, **kwargs):
        """显示帮助信息"""
        stream_id = kwargs["stream_id"]
        help_text = "可用命令：\n/status - 查看状态\n/echo <text> - 回显消息\n/help - 显示帮助"
        await self.ctx.send.text(help_text, stream_id)
        return True, "帮助信息已发送", 1


def create_plugin():
    return AdminPlugin()
6.Hook 处理器

@HookHandler 是 MaiBot 插件系统中用于订阅命名 Hook 点的组件装饰器。主程序在关键执行点触发命名 Hook，所有订阅该 Hook 的插件处理器按固定规则调度执行，从而实现消息拦截、改写和观察。

WorkflowStep 已移除

SDK 2.0 中 WorkflowStep 已被 @HookHandler 取代。旧代码仍在使用 WorkflowStep 时会在运行时抛出 RuntimeError，这是一个不向后兼容的更改，必须迁移到 @HookHandler。
装饰器签名

from maibot_sdk import HookHandler
from maibot_sdk.types import HookMode, HookOrder, ErrorPolicy

@HookHandler(
    hook: str,                              # 订阅的命名 Hook 名称（必填）
    *,
    name: str = "",                         # 组件名称，留空时使用方法名
    description: str = "",                  # 组件描述
    mode: HookMode = HookMode.BLOCKING,     # 处理模式
    order: HookOrder = HookOrder.NORMAL,    # 同一模式内的顺序槽位
    timeout_ms: int = 0,                    # 处理器超时（毫秒），0 = 使用 Hook 默认值
    error_policy: ErrorPolicy = ErrorPolicy.SKIP,  # 异常处理策略
    **metadata,                             # 额外元数据
)

处理模式
BLOCKING（阻塞模式）

    串行执行，可以修改传入的 kwargs
    返回 modified_kwargs 可以更新后续处理器接收的参数
    返回 action: "abort" 可以终止整个 Hook 调用链
    适合需要拦截或改写消息的场景

OBSERVE（观察模式）

    后台并发执行，只读旁路观察
    不参与主流程控制，返回的 modified_kwargs 和 abort 请求会被忽略
    适合日志记录、数据分析等不影响主流程的场景

class HookMode(str, Enum):
    BLOCKING = "blocking"  # 同步等待，可修改数据
    OBSERVE = "observe"    # 异步观察，不可修改

顺序槽位

同一模式内的处理器按 order 排序执行：

    HookOrder.EARLY — 优先执行，适合前置拦截
    HookOrder.NORMAL — 默认顺序
    HookOrder.LATE — 延后执行，适合补充处理

异常处理策略

当处理器抛出异常时，根据 error_policy 决定后续行为：

    ErrorPolicy.ABORT — 异常时终止当前 Hook 调用
    ErrorPolicy.SKIP — 记录日志，跳过此处理器继续（默认）
    ErrorPolicy.LOG — 记录日志，并继续执行后续 hook

调度顺序

Hook 处理器按以下规则全局排序：

    模式优先：blocking 先于 observe
    顺序槽位：early → normal → late
    来源优先：内置插件先于第三方插件
    插件 ID：按字典序排列
    处理器名称：按字典序排列

基本用法
阻塞模式示例：拦截并修改消息

from maibot_sdk import MaiBotPlugin, HookHandler
from maibot_sdk.types import HookMode, HookOrder, ErrorPolicy


class MyPlugin(MaiBotPlugin):
    async def on_load(self) -> None:
        self.ctx.logger.info("插件已加载")

    async def on_unload(self) -> None:
        self.ctx.logger.info("插件已卸载")

    async def on_config_update(self, scope: str, config_data: dict, version: str) -> None:
        pass

    @HookHandler(
        "chat.receive.before_process",
        name="message_filter",
        description="过滤入站消息",
        mode=HookMode.BLOCKING,
        order=HookOrder.EARLY,
        error_policy=ErrorPolicy.ABORT,
    )
    async def handle_message_filter(self, **kwargs):
        message = kwargs.get("message", {})
        # 过滤逻辑：如果消息包含敏感词，终止处理链
        raw_message = message.get("raw_message", "")
        if "违禁词" in raw_message:
            self.ctx.logger.info("消息被过滤: %s", raw_message)
            return {"action": "abort"}

        # 修改消息内容后继续
        kwargs["message"]["filtered"] = True
        return {"action": "continue", "modified_kwargs": kwargs}

观察模式示例：日志记录

from maibot_sdk import MaiBotPlugin, HookHandler
from maibot_sdk.types import HookMode, HookOrder


class LogPlugin(MaiBotPlugin):
    async def on_load(self) -> None:
        self.ctx.logger.info("日志插件已加载")

    async def on_unload(self) -> None:
        self.ctx.logger.info("日志插件已卸载")

    async def on_config_update(self, scope: str, config_data: dict, version: str) -> None:
        pass

    @HookHandler(
        "chat.receive.after_process",
        name="message_logger",
        description="记录所有入站消息",
        mode=HookMode.OBSERVE,
        order=HookOrder.LATE,
    )
    async def observe_message(self, **kwargs):
        message = kwargs.get("message", {})
        self.ctx.logger.info(
            "观察到消息: user=%s, text=%s",
            message.get("user_id", "unknown"),
            message.get("raw_message", ""),
        )
        # observe 模式返回值会被忽略

阻塞模式示例：修改发送参数

from maibot_sdk import MaiBotPlugin, HookHandler
from maibot_sdk.types import HookMode, HookOrder


class SendInterceptorPlugin(MaiBotPlugin):
    async def on_load(self) -> None:
        self.ctx.logger.info("发送拦截插件已加载")

    async def on_unload(self) -> None:
        self.ctx.logger.info("发送拦截插件已卸载")

    async def on_config_update(self, scope: str, config_data: dict, version: str) -> None:
        pass

    @HookHandler(
        "send_service.before_send",
        name="send_modifier",
        description="修改发送参数",
        mode=HookMode.BLOCKING,
        order=HookOrder.NORMAL,
        timeout_ms=5000,
    )
    async def modify_send_params(self, **kwargs):
        # 禁用打字效果，强制开启发送日志
        kwargs["typing"] = False
        kwargs["show_log"] = True
        return {"action": "continue", "modified_kwargs": kwargs}

内置 Hook 清单

以下为 Host 运行时中心表注册的全部 Hook 点。每个 Hook 注明是否允许 abort（中止调用链）和是否允许改参（修改后续处理器接收的 kwargs）。
聊天消息链

    chat.receive.before_process — 入站消息执行 SessionMessage.process() 前 — 允许 abort ✅ · 允许改参 ✅
    chat.receive.after_process — 入站消息轻量预处理完成后 — 允许 abort ✅ · 允许改参 ✅

命令执行链

    chat.command.before_execute — 命令匹配成功、正式执行前 — 允许 abort ✅ · 允许改参 ✅
    chat.command.after_execute — 命令执行结束后 — 允许 abort ❌ · 允许改参 ✅

表情包链

    emoji.maisaka.before_select — Maisaka 选择表情前 — 允许 abort ✅ · 允许改参 ✅
    emoji.maisaka.after_select — Maisaka 选出表情后 — 允许 abort ✅ · 允许改参 ✅
    emoji.register.after_build_description — 表情包描述生成完成后 — 允许 abort ✅ · 允许改参 ✅
    emoji.register.after_build_emotion — 表情包情绪标签生成完成后 — 允许 abort ✅ · 允许改参 ✅

黑话（Jargon）链

    jargon.query.before_search — Maisaka 黑话查询前 — 允许 abort ✅ · 允许改参 ✅
    jargon.query.after_search — Maisaka 黑话查询完成后 — 允许 abort ✅ · 允许改参 ✅
    jargon.extract.before_persist — 黑话条目写库前 — 允许 abort ✅ · 允许改参 ✅
    jargon.inference.before_finalize — 黑话推断结果写回前 — 允许 abort ✅ · 允许改参 ✅

表达方式（Expression）链

    expression.select.before_select — 表达方式选择前 — 允许 abort ✅ · 允许改参 ✅
    expression.select.after_selection — 表达方式选择完成后 — 允许 abort ✅ · 允许改参 ✅
    expression.learn.after_extract — 表达方式学习解析候选后 — 允许 abort ✅ · 允许改参 ✅
    expression.learn.before_upsert — 表达方式写库前 — 允许 abort ✅ · 允许改参 ✅

发送服务链

    send_service.after_build_message — 出站 SessionMessage 构建完成后 — 允许 abort ✅ · 允许改参 ✅
    send_service.before_send — 调用 Platform IO 发送前 — 允许 abort ✅ · 允许改参 ✅
    send_service.after_send — 发送流程完成后 — 允许 abort ❌ · 允许改参 ❌

Maisaka 规划器链

    maisaka.planner.before_request — Maisaka 规划器请求模型前 — 允许 abort ❌ · 允许改参 ✅
    maisaka.planner.after_response — Maisaka 收到模型响应后 — 允许 abort ❌ · 允许改参 ✅

Maisaka 回复器链

    maisaka.replyer.before_request — Maisaka replyer 请求模型前；可读取或改写本次 reply_tool_args — 允许 abort ❌ · 允许改参 ✅
    maisaka.replyer.before_model_request — Maisaka replyer 构造完最终 messages 后、请求模型前；可改写实际发送给模型的消息列表 — 允许 abort ❌ · 允许改参 ✅
    maisaka.replyer.after_response — Maisaka replyer 收到模型响应后；可改写回复或要求重生成 — 允许 abort ❌ · 允许改参 ✅

reply_tool_args 会在表达方式选择链、maisaka.replyer.before_request 和 maisaka.replyer.after_response 中保持可见。它包含 reply 工具里除 msg_id、set_quote、reference_info 外的额外参数；before_request 返回的 reply_tool_args 修改会继续传递给后续 replyer hook。
在 replyer 请求前切换模型或追加提示词

maisaka.replyer.before_request 是 replyer 真正请求模型前的最后一个可改写点。阻塞模式处理器可以修改以下字段：

    task_name str — 本次 replyer 请求使用的任务名。修改后会用该任务的默认模型池和生成参数。
    model_name str — 本次 replyer 请求指定的具体模型名称，必须存在于 model_config.toml 的 [[models]] 中。指定后只尝试该模型一次，不再按任务模型池轮换。
    extra_prompt str — 追加到本次 replyer prompt 的额外回复要求。
    reference_info str — 本次 reply 工具传入的引用信息，可以被改写。
    reply_tool_args dict — reply 工具额外参数，修改后会传给后续 replyer hook。

model_name 是具体模型名，不是 task 名；如果只想切换到另一个任务的模型池，修改 task_name 即可。如果同时设置 task_name 和 model_name，任务提供温度、token 上限、超时等生成参数，model_name 指定实际调用的模型。

如果需要改写 replyer 真正发给模型的消息列表，请使用 maisaka.replyer.before_model_request。该 Hook 会在 replyer 已经根据当前模型能力构造好 messages 后触发，阻塞模式处理器可以返回新的 messages；适合在 system 后插入一条合成的第一条 user 消息、做临时提示词实验或记录最终请求体。这个 Hook 只改写本次临时 LLM 请求，不会回写聊天历史，也不会影响中期记忆插入。

常见用法是先通过 maisaka.planner.before_request 给内置 reply 工具追加参数 schema，让 planner 可以在调用 reply 工具时填入参数；随后在 maisaka.replyer.before_request 中读取 reply_tool_args 并路由模型：

from maibot_sdk import MaiBotPlugin, HookHandler
from maibot_sdk.types import HookMode


class ThinkingLevelPlugin(MaiBotPlugin):
    @HookHandler("maisaka.planner.before_request", mode=HookMode.BLOCKING)
    async def add_reply_tool_param(self, **kwargs):
        for tool in kwargs.get("tool_definitions", []):
            function = tool.get("function", {})
            if function.get("name") != "reply":
                continue

            parameters = function.setdefault("parameters", {})
            properties = parameters.setdefault("properties", {})
            properties["thinking_level"] = {
                "type": "string",
                "enum": ["normal", "deep"],
                "description": "回复时的思考强度。normal 表示常规回复，deep 表示使用更强模型并更细致分析。",
            }
        return {"action": "continue", "modified_kwargs": kwargs}

    @HookHandler("maisaka.replyer.before_request", mode=HookMode.BLOCKING)
    async def route_replyer_model(self, **kwargs):
        reply_tool_args = kwargs.get("reply_tool_args", {})
        if reply_tool_args.get("thinking_level") == "deep":
            kwargs["model_name"] = "your-deep-model-name"
            kwargs["extra_prompt"] = "请更细致地理解上下文后再回复。"

        return {"action": "continue", "modified_kwargs": kwargs}

只新增或修改 hook 名本身通常不需要改插件 SDK 运行时代码：@HookHandler 接收的是字符串 hook 名，是否可用由 Host 注册的 HookSpec 校验。只有需要 SDK 常量、类型提示、文档或示例同步时，才需要更新 SDK 侧内容。
Host 校验规则

Host 在插件注册阶段会对 @HookHandler 声明进行校验，不合法时插件直接注册失败（而非"加载成功但 Hook 不生效"的半成功状态）。校验规则如下：

    Hook 名称必须已注册：hook 参数必须是上述内置 Hook 清单中已存在的名称。传入未注册的 Hook 名称会导致注册失败。
    mode 必须符合 Hook 的能力约束：Host 会检查 mode 是否与该 Hook 点的能力兼容（例如，仅允许改参的 Hook 不能以不可改参的模式运行）。
    error_policy=ABORT 须 Hook 允许 abort：只有当该 Hook 的"允许 abort"列为"是"时，才能声明 error_policy=ErrorPolicy.ABORT。对于不允许 abort 的 Hook 声明 ABORT 策略将导致注册失败。

运行时 Host 会将这份 Hook 清单公开给 WebUI 后端路由 /plugins/runtime/hooks，便于面板或调试工具直接读取动态中心表。
表达方式选择链

    expression.select.before_select — 表达候选池载入后、默认选择结果生成前；可改写 candidates、max_num 或 abort 跳过本次选择
    expression.select.after_selection — 默认选择结果生成后；可改写 selected_expression_ids 或 selected_expressions

before_select 会收到 chat_id、session_id、chat_info、chat_history、reply_message、reply_tool_args、target_message、reply_reason、max_num、think_level、candidates。reply_tool_args 包含 reply 工具里除 msg_id、set_quote、reference_info 外的额外参数。after_selection 在此基础上额外包含 selected_expression_ids 与 selected_expressions。

@HookHandler("expression.select.after_selection", mode=HookMode.BLOCKING)
async def replace_expression_selection(self, **kwargs):
    strategy = kwargs.get("reply_tool_args", {}).get("expression_strategy")
    candidates = kwargs.get("candidates", [])
    selected_ids = [item["id"] for item in candidates[:1]]
    kwargs["selected_expression_ids"] = selected_ids
    return {"action": "continue", "modified_kwargs": kwargs}

处理器返回值

阻塞模式的处理器可以返回字典来控制后续流程：

    action str — "continue" 继续调用链，"abort" 终止调用链
    modified_kwargs dict — 修改后的参数，将传递给后续处理器

观察模式的处理器返回值会被忽略，不需要返回控制字典。
7.事件处理器

@EventHandler 是用于订阅消息和工作流事件的组件装饰器。与 @HookHandler 的命名 Hook 点机制不同，@EventHandler 基于固定的 EventType 枚举值订阅事件，适合在消息处理流程的特定阶段进行拦截或观察。
装饰器签名

from maibot_sdk import EventHandler
from maibot_sdk.types import EventType

@EventHandler(
    name: str,                                      # 组件名称（必填）
    description: str = "",                          # 组件描述
    event_type: EventType = EventType.ON_MESSAGE,   # 订阅的事件类型
    intercept_message: bool = False,                # 是否阻塞消息链
    weight: int = 0,                                # 权重，越高越先执行
    **metadata,                                     # 额外元数据
)

EventType 事件类型

    UNKNOWN — 未知事件
    ON_START — 插件启动
    ON_STOP — 插件停止
    ON_MESSAGE_PRE_PROCESS — 消息预处理阶段（过滤、拦截的最佳时机）
    ON_MESSAGE — 消息处理阶段
    ON_PLAN — 规划阶段
    POST_LLM — LLM 调用后（响应已生成）
    AFTER_LLM — LLM 调用完成后
    POST_SEND_PRE_PROCESS — 发送预处理阶段
    POST_SEND — 消息发送后
    AFTER_SEND — 消息发送完成后

intercept_message 参数

intercept_message 控制 EventHandler 是否以阻塞方式参与消息处理链：

    False（默认） — 异步 fire-and-forget，不影响消息主流程
    True — 同步阻塞，主程序等待处理器返回后才继续

设为 True 时，处理器可以拦截、修改甚至阻止消息的后续处理。
weight 权重

多个 EventHandler 订阅同一 EventType 时，weight 决定执行顺序：

    值越高越先执行
    默认值为 0
    与旧系统的 weight 语义一致

基本用法
ON_START：插件初始化

from maibot_sdk import MaiBotPlugin, EventHandler
from maibot_sdk.types import EventType


class StartupPlugin(MaiBotPlugin):
    async def on_load(self) -> None:
        self.ctx.logger.info("插件已加载")

    async def on_unload(self) -> None:
        self.ctx.logger.info("插件已卸载")

    async def on_config_update(self, scope: str, config_data: dict, version: str) -> None:
        pass

    @EventHandler(
        "on_startup",
        description="插件启动时初始化资源",
        event_type=EventType.ON_START,
    )
    async def handle_startup(self, **kwargs):
        self.ctx.logger.info("启动事件触发，开始初始化")
        # 在这里执行启动时需要的初始化逻辑

ON_MESSAGE_PRE_PROCESS：消息过滤

from maibot_sdk import MaiBotPlugin, EventHandler
from maibot_sdk.types import EventType


class MessageFilterPlugin(MaiBotPlugin):
    async def on_load(self) -> None:
        self.ctx.logger.info("消息过滤插件已加载")

    async def on_unload(self) -> None:
        self.ctx.logger.info("消息过滤插件已卸载")

    async def on_config_update(self, scope: str, config_data: dict, version: str) -> None:
        pass

    @EventHandler(
        "spam_filter",
        description="过滤垃圾消息",
        event_type=EventType.ON_MESSAGE_PRE_PROCESS,
        intercept_message=True,   # 阻塞模式，可以拦截消息
        weight=100,               # 高权重，优先执行
    )
    async def filter_spam(self, message, **kwargs):
        raw_message = message.get("raw_message", "")
        user_id = message.get("user_info", {}).get("user_id", "")

        # 检测垃圾消息
        if self._is_spam(raw_message, user_id):
            self.ctx.logger.info("拦截垃圾消息: user=%s, text=%s", user_id, raw_message)
            return {"intercepted": True, "reason": "spam"}

        # 放行消息
        return {"intercepted": False}

    def _is_spam(self, text: str, user_id: str) -> bool:
        # 简单的垃圾消息检测逻辑
        spam_keywords = ["广告", "加群", "免费"]
        return any(kw in text for kw in spam_keywords)

ON_MESSAGE：消息观察

from maibot_sdk import MaiBotPlugin, EventHandler
from maibot_sdk.types import EventType


class MessageObserverPlugin(MaiBotPlugin):
    async def on_load(self) -> None:
        self._message_count = 0

    async def on_unload(self) -> None:
        self.ctx.logger.info("总消息数: %d", self._message_count)

    async def on_config_update(self, scope: str, config_data: dict, version: str) -> None:
        pass

    @EventHandler(
        "message_counter",
        description="统计消息数量",
        event_type=EventType.ON_MESSAGE,
    )
    async def count_message(self, message, **kwargs):
        self._message_count += 1
        self.ctx.logger.debug("收到第 %d 条消息", self._message_count)

AFTER_LLM：LLM 响应后处理

from maibot_sdk import MaiBotPlugin, EventHandler
from maibot_sdk.types import EventType


class LLMPostProcessor(MaiBotPlugin):
    async def on_load(self) -> None:
        self.ctx.logger.info("LLM 后处理插件已加载")

    async def on_unload(self) -> None:
        self.ctx.logger.info("LLM 后处理插件已卸载")

    async def on_config_update(self, scope: str, config_data: dict, version: str) -> None:
        pass

    @EventHandler(
        "llm_response_logger",
        description="记录 LLM 响应",
        event_type=EventType.AFTER_LLM,
        weight=50,
    )
    async def log_llm_response(self, **kwargs):
        response = kwargs.get("response", "")
        self.ctx.logger.info("LLM 响应: %s", response[:200])

POST_SEND：发送后回调

from maibot_sdk import MaiBotPlugin, EventHandler
from maibot_sdk.types import EventType


class SendAuditPlugin(MaiBotPlugin):
    async def on_load(self) -> None:
        self.ctx.logger.info("发送审计插件已加载")

    async def on_unload(self) -> None:
        self.ctx.logger.info("发送审计插件已卸载")

    async def on_config_update(self, scope: str, config_data: dict, version: str) -> None:
        pass

    @EventHandler(
        "send_audit",
        description="审计所有发送的消息",
        event_type=EventType.POST_SEND,
    )
    async def audit_send(self, **kwargs):
        message = kwargs.get("message", {})
        self.ctx.logger.info(
            "消息已发送: stream_id=%s",
            message.get("stream_id", "unknown"),
        )

与 HookHandler 的区别

    订阅方式：@EventHandler EventType 枚举值 → @HookHandler 命名 Hook 点字符串
    粒度：@EventHandler 固定事件类型，数量有限 → @HookHandler 自定义 Hook 名称，可无限扩展
    拦截方式：@EventHandler intercept_message=True → @HookHandler mode=HookMode.BLOCKING
    优先级：@EventHandler weight 数值权重 → @HookHandler order 三档枚举 + 全局排序
    异常策略：@EventHandler 无专用参数 → @HookHandler error_policy 控制
    适用场景：@EventHandler 消息流程的固定阶段 → @HookHandler 主程序定义的任意扩展点

一般原则：

    如果需要在消息流程的固定阶段（如收到消息、LLM 返回后）执行逻辑，使用 @EventHandler
    如果需要订阅主程序定义的特定命名 Hook 点（如 heart_fc.heart_flow_cycle_start），使用 @HookHandler
8.API 组件

@API 装饰器用于声明插件间通信的 API 接口。其他插件可以通过 ctx.api.call() 调用这些 API，实现插件间的功能互操作。
装饰器签名

from maibot_sdk import API

@API(
    name: str,                  # API 名称（必填）
    description: str = "",      # API 描述
    version: str = "1",         # API 版本
    public: bool = False,       # 是否允许其他插件调用
    **metadata,                 # 额外元数据
)

参数说明
name

API 的唯一标识名称。同一插件内不能有重复名称的 API。其他插件通过 插件 ID + API 名称 来定位和调用。
public

    False（默认） — 仅插件内部可见，其他插件无法调用
    True — 公开 API，其他插件可通过 ctx.api.call() 调用

version

API 版本号，默认为 "1"。用于 API 版本管理，当需要不兼容更新时可以递增版本号。
静态 API 示例

通过 @API 装饰器在插件类上直接声明 API：

from maibot_sdk import MaiBotPlugin, API


class RenderPlugin(MaiBotPlugin):
    async def on_load(self) -> None:
        self.ctx.logger.info("渲染插件已加载")

    async def on_unload(self) -> None:
        self.ctx.logger.info("渲染插件已卸载")

    async def on_config_update(self, scope: str, config_data: dict, version: str) -> None:
        pass

    @API(
        "render_html",
        description="将 HTML 渲染为图片",
        version="1",
        public=True,
    )
    async def handle_render_html(self, html: str, **kwargs):
        # 调用渲染能力
        result = await self.ctx.render.html2png(html)
        return {"success": True, "image_path": result}

    @API(
        "get_stats",
        description="获取渲染统计信息",
        version="1",
        public=True,
    )
    async def handle_get_stats(self, **kwargs):
        return {
            "total_renders": 42,
            "avg_time_ms": 150,
        }

动态 API 注册

除了使用 @API 装饰器静态声明外，还可以在运行时动态注册和注销 API。动态 API 适合需要根据配置或运行时条件决定是否暴露 API 的场景。
动态 API 方法

    self.register_dynamic_api(name, handler, *, description, version, public, handler_name, **metadata) — 注册动态 API
    self.unregister_dynamic_api(name, *, version="1") — 注销动态 API
    self.clear_dynamic_apis() — 清空所有动态 API
    await self.sync_dynamic_apis(*, offline_reason="动态 API 已下线") — 将动态 API 同步到主程序

动态注册示例

from maibot_sdk import MaiBotPlugin, PluginConfigBase, Field
from typing import Any


class DynamicApiPlugin(MaiBotPlugin):
    class MyConfig(PluginConfigBase):
        enable_translate: bool = Field(default=False, description="是否启用翻译 API")

    config_model = MyConfig

    async def on_load(self) -> None:
        # 根据配置动态注册 API
        if self.config.enable_translate:
            self.register_dynamic_api(
                "translate",
                self._handle_translate,
                description="文本翻译",
                version="1",
                public=True,
                handler_name="handle_translate",
            )

            self.register_dynamic_api(
                "detect_language",
                self._handle_detect_language,
                description="语言检测",
                version="1",
                public=True,
            )

        # 同步动态 API 到主程序
        await self.sync_dynamic_apis()
        self.ctx.logger.info("动态 API 已同步")

    async def on_unload(self) -> None:
        # 清空并同步下线
        self.clear_dynamic_apis()
        await self.sync_dynamic_apis(offline_reason="插件已卸载")

    async def on_config_update(self, scope: str, config_data: dict, version: str) -> None:
        pass

    async def _handle_translate(self, text: str, target_lang: str = "en", **kwargs) -> dict[str, Any]:
        # 翻译逻辑
        return {"translated": f"[translated {text} to {target_lang}]"}

    async def _handle_detect_language(self, text: str, **kwargs) -> dict[str, Any]:
        # 语言检测逻辑
        return {"language": "zh", "confidence": 0.95}

动态注销示例

class ManagedApiPlugin(MaiBotPlugin):
    async def on_load(self) -> None:
        # 批量注册
        for name, handler in [("api_a", self._a), ("api_b", self._b)]:
            self.register_dynamic_api(name, handler, public=True)
        await self.sync_dynamic_apis()

    async def disable_api_b(self) -> None:
        # 注销单个 API
        self.unregister_dynamic_api("api_b")
        await self.sync_dynamic_apis(offline_reason="API B 已禁用")

    async def on_unload(self) -> None:
        self.clear_dynamic_apis()
        await self.sync_dynamic_apis(offline_reason="插件已卸载")

    async def on_config_update(self, scope: str, config_data: dict, version: str) -> None:
        pass

    async def _a(self, **kwargs):
        return {"result": "a"}

    async def _b(self, **kwargs):
        return {"result": "b"}

调用其他插件的 API

通过 self.ctx.api 代理可以查询和调用其他插件公开的 API。
ctx.api 方法

    await self.ctx.api.call(api_name, *, version="", **kwargs) — 调用其他插件的 API
    await self.ctx.api.get(api_name, *, version="") — 获取 API 信息
    await self.ctx.api.list() — 列出所有可用 API
    await self.ctx.api.replace_dynamic_apis(components, offline_reason="...") — 替换动态 API

调用示例

from maibot_sdk import MaiBotPlugin, Tool
from maibot_sdk.types import ToolParameterInfo, ToolParamType


class CallerPlugin(MaiBotPlugin):
    async def on_load(self) -> None:
        # 列出所有可用 API
        apis = await self.ctx.api.list()
        self.ctx.logger.info("可用 API: %s", apis)

    async def on_unload(self) -> None:
        pass

    async def on_config_update(self, scope: str, config_data: dict, version: str) -> None:
        pass

    @Tool(
        "translate_text",
        brief_description="翻译文本",
        detailed_description="参数说明：\n- text：string，必填。待翻译文本。",
        parameters=[
            ToolParameterInfo(
                name="text",
                param_type=ToolParamType.STRING,
                description="待翻译文本",
                required=True,
            ),
        ],
    )
    async def handle_translate(self, text: str, **kwargs):
        # 调用其他插件的翻译 API
        result = await self.ctx.api.call(
            "com.example.translate.translate",
            text=text,
            target_lang="en",
        )
        return result

查询 API 信息

# 获取特定 API 的详细信息
api_info = await self.ctx.api.get("com.example.translate.translate")
self.ctx.logger.info("API 信息: %s", api_info)

API 设计建议
命名规范

    使用小写字母和下划线：render_html、get_stats
    动词开头：get_、render_、detect_、translate_
    避免过于通用的名称，应体现功能含义

版本管理

    初始版本使用 "1"
    不兼容更新时递增版本号
    同名 API 可以同时存在多个版本

参数设计

    API 处理器方法接收 **kwargs，从中提取参数
    必要参数应以位置参数明确声明
    返回值应为可序列化的字典

静态 API 与动态 API 对比

    声明时机：@API 类定义时 → register_dynamic_api() 运行时（通常在 on_load 中）
    条件暴露：@API 不支持 → register_dynamic_api() 可根据配置动态决定
    注销：@API 不支持 → register_dynamic_api() 可通过 unregister 动态注销
    同步：@API 自动 → register_dynamic_api() 需调用 sync_dynamic_apis()
    适用场景：@API 固定不变的 API → register_dynamic_api() 按需启用/禁用的 API
9.消息网关

@MessageGateway 装饰器用于声明消息网关组件，实现 MaiBot 与外部消息平台（如 QQ、Discord 等）的双向消息路由。消息网关是平台适配器的核心组件，负责出站消息发送和入站消息注入。
装饰器签名

from maibot_sdk import MessageGateway

@MessageGateway(
    route_type: str,             # 路由类型：send / receive / duplex（必填）
    *,
    name: str = "",              # 组件名，留空时使用方法名
    description: str = "",       # 组件描述
    platform: str = "",          # 平台名称（如 qq、discord）
    protocol: str = "",          # 协议或接入方言名称
    account_id: str = "",        # 账号 ID / self_id
    scope: str = "",             # 路由作用域
    **metadata,                  # 额外元数据
)

路由类型

    "send" → MessageGatewayRouteType.SEND — 出站：Host → 插件 → 外部平台
    "receive" → MessageGatewayRouteType.RECEIVE — 入站：外部平台 → 插件 → Host
    "duplex" → MessageGatewayRouteType.DUPLEX — 双向：同时支持出站和入站

别名支持

route_type 也接受 "recv" 和 "recive" 作为 "receive" 的别名。
ctx.gateway 能力代理

    await self.ctx.gateway.route_message(gateway_name, message_dict, route_metadata=None, ...) — 注入入站消息到 Host
    await self.ctx.gateway.update_state(gateway_name, ready, platform="", account_id="", scope="", metadata=None) — 上报网关状态

状态管理

    只有 ready=True 的网关才会被主程序选中进行消息路由
    route_type="send" 或 "duplex" 且 ready=True 的网关可被 Platform IO 选中处理出站消息
    route_type="receive" 或 "duplex" 且 ready=True 的网关可通过 ctx.gateway.route_message() 注入入站消息
    插件应在链路可用时上报 ready=True，在断开或卸载时上报 ready=False

完整适配器示例

以下是一个完整的 QQ 平台适配器示例，基于 NapCat 协议实现双向消息路由：

from typing import Any

from maibot_sdk import MaiBotPlugin, MessageGateway


class NapCatGatewayPlugin(MaiBotPlugin):
    async def on_load(self) -> None:
        # 上报网关就绪状态
        await self.ctx.gateway.update_state(
            gateway_name="napcat_gateway",
            ready=True,
            platform="qq",
            account_id="10001",
            scope="primary",
            metadata={"protocol": "napcat"},
        )
        self.ctx.logger.info("NapCat 网关已就绪")

    async def on_unload(self) -> None:
        # 上报网关离线
        await self.ctx.gateway.update_state(
            gateway_name="napcat_gateway",
            ready=False,
        )
        self.ctx.logger.info("NapCat 网关已下线")

    async def on_config_update(self, scope: str, config_data: dict, version: str) -> None:
        pass

    @MessageGateway(
        route_type="duplex",
        name="napcat_gateway",
        platform="qq",
        protocol="napcat",
        account_id="10001",
        scope="primary",
    )
    async def send_to_platform(
        self,
        message: dict[str, Any],
        route: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """出站：将 Host 消息转发到外部平台。"""
        # 将 Host MessageDict 转换为平台格式并发送
        platform_msg = self._convert_to_platform_format(message)
        result = await self._send_to_napcat(platform_msg)
        return {"success": True, "external_message_id": result.get("message_id")}

    async def handle_inbound(self, payload: dict[str, Any]) -> None:
        """入站：将外部平台消息注入 Host。

        此方法由外部平台回调触发（如 WebSocket 推送），
        不是组件装饰器方法，但演示了入站消息的注入流程。
        """
        accepted = await self.ctx.gateway.route_message(
            gateway_name="napcat_gateway",
            message_dict={
                "message_id": payload["message_id"],
                "platform": "qq",
                "message_info": {
                    "user_info": {
                        "user_id": payload["user_id"],
                        "user_nickname": payload["nickname"],
                    },
                    "additional_config": {},
                },
                "raw_message": payload["message"],
            },
            route_metadata={
                "self_id": "10001",
                "connection_id": "primary",
            },
            external_message_id=payload["message_id"],
            dedupe_key=payload["message_id"],
        )
        if not accepted:
            self.ctx.logger.warning(
                "Host 未接收入站消息: %s", payload["message_id"]
            )

    def _convert_to_platform_format(
        self, message: dict[str, Any]
    ) -> dict[str, Any]:
        """将 Host 消息格式转换为平台格式。"""
        return {
            "action": "send_msg",
            "params": {
                "message_type": "group",
                "group_id": message.get("group_id"),
                "message": message.get("raw_message", ""),
            },
        }

    async def _send_to_napcat(
        self, platform_msg: dict[str, Any]
    ) -> dict[str, Any]:
        """发送消息到 NapCat API。"""
        # 实际实现中这里会调用 NapCat 的 HTTP/WebSocket API
        return {"message_id": "platform-msg-1"}


def create_plugin():
    return NapCatGatewayPlugin()

仅入站网关示例

如果只需要向 MaiBot 注入消息（如 Webhook 监听），可以使用 route_type="receive"：

from typing import Any

from maibot_sdk import MaiBotPlugin, MessageGateway


class WebhookReceiverPlugin(MaiBotPlugin):
    async def on_load(self) -> None:
        await self.ctx.gateway.update_state(
            gateway_name="webhook_receiver",
            ready=True,
            platform="webhook",
            scope="default",
        )

    async def on_unload(self) -> None:
        await self.ctx.gateway.update_state(
            gateway_name="webhook_receiver",
            ready=False,
        )

    async def on_config_update(self, scope: str, config_data: dict, version: str) -> None:
        pass

    @MessageGateway(
        route_type="receive",
        name="webhook_receiver",
        platform="webhook",
    )
    async def handle_outbound(self, message: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        """仅入站网关，出站方向不会收到消息。"""
        # receive 类型网关不会被选中处理出站消息
        # 此处理器不会被调用，但必须声明
        return {"success": True}

    async def inject_webhook_message(self, payload: dict[str, Any]) -> None:
        """接收 Webhook 回调并注入消息。"""
        accepted = await self.ctx.gateway.route_message(
            gateway_name="webhook_receiver",
            message_dict={
                "message_id": payload["id"],
                "platform": "webhook",
                "message_info": {
                    "user_info": {
                        "user_id": payload.get("sender", "unknown"),
                        "user_nickname": payload.get("sender_name", "unknown"),
                    },
                    "additional_config": {},
                },
                "raw_message": payload.get("content", ""),
            },
        )
        if accepted:
            self.ctx.logger.info("Webhook 消息已注入")


def create_plugin():
    return WebhookReceiverPlugin()

网关处理器参数

@MessageGateway 装饰的处理器方法接收以下参数：

    self MaiBotPlugin — 插件实例
    message dict[str, Any] — Host 传出的消息字典（出站方向）
    route dict[str, Any] | None — 路由信息
    metadata dict[str, Any] | None — 路由元数据
    **kwargs Any — 其他参数

处理器返回值为 dict[str, Any]，应至少包含 success 字段表示发送是否成功。
important

    插件在 on_load() 中应调用 ctx.gateway.update_state(ready=True) 上报就绪状态
    插件在 on_unload() 中应调用 ctx.gateway.update_state(ready=False) 上报离线状态
    只有 ready=True 的网关才会参与消息路由 :::

平台字段说明

    platform str — 目标平台名称（如 "qq"、"discord"、"webhook"）
    protocol str — 协议或实现名称（如 "napcat"、"go-cqhttp"、"discord.py"）
    account_id str — 机器人账号 ID（如 "10001"、"bot#1234"）
    scope str — 路由作用域（如 "primary"、"default"）

platform、protocol、account_id、scope 也可以在运行时通过 ctx.gateway.update_state() 动态上报，无需在装饰器中固定。
9.LLMProvider 组件

@LLMProvider 用于声明插件提供新的 LLM Provider client_type。主程序会将该 client_type 注册到 LLM 客户端注册表中，因此现有 LLMService 和模型任务配置不需要改调用方式——只要模型配置里的 api_providers[].client_type 指向插件声明的值，请求就会通过插件 Provider 发起。

双重声明必须一致

LLM Provider 必须同时满足两处声明，缺一不可：

    _manifest.json 顶层 llm_providers 中静态声明 client_type
    插件代码中使用 @LLMProvider("同一个 client_type") 修饰处理方法

Runner 会校验 manifest 与装饰器收集结果完全一致。任意一边漏写、拼写不一致或同一插件内重复声明，插件都会拒绝加载。不同插件声明同一个 client_type 时，冲突双方都会被阻止加载。
装饰器签名

from maibot_sdk import LLMProvider

@LLMProvider(
    client_type: str,          # 客户端类型标识（必填）
    *,
    name: str = "",            # Provider 展示名称
    description: str = "",     # Provider 描述
    version: str = "1.0.0",    # Provider 实现版本
    **metadata,                # 额外元数据
)

参数说明

    client_type str · 必填 — 客户端类型标识，对应模型配置中的 api_providers[].client_type。不能为空
    name str · 默认 "" — Provider 展示名称。留空时使用 client_type
    description str · 默认 "" — Provider 描述信息
    version str · 默认 "1.0.0" — Provider 实现版本号
    **metadata Any — 额外元数据键值对

Manifest 声明

_manifest.json 顶层必须包含 llm_providers 数组，与代码中的 @LLMProvider 一一对应：

{
  "llm_providers": [
    {
      "client_type": "example.provider",
      "name": "Example Provider",
      "description": "示例 LLM Provider",
      "version": "1.0.0"
    }
  ]
}

llm_providers 字段说明

    client_type str · 必填 — Provider 客户端类型，必须与模型配置 api_providers[].client_type 一致
    name str · 默认 "" — Provider 展示名称
    description str · 默认 "" — Provider 描述
    version str · 默认 "1.0.0" — Provider 实现版本

DANGER

不要在 manifest 的 llm_providers 中写 handler_name 或 metadata——处理函数由 @LLMProvider 装饰器自动收集，不需要手动指定。
Operation 类型

处理方法通过 operation 参数区分请求类型。三种 operation 分别对应不同的 LLM 能力：

    response — LLM 文本/工具响应。主要请求字段：message_list、tool_options、max_tokens、temperature、response_format、extra_params、model_info、api_provider。返回字段：content / response、reasoning_content、tool_calls、usage
    embedding — 文本向量化。主要请求字段：embedding_input、extra_params、model_info、api_provider。返回字段：embedding
    audio_transcription — 语音识别。主要请求字段：audio_base64、max_tokens、extra_params、model_info、api_provider。返回字段：content

三种 operation 的请求中都会包含以下公共字段：

    model_info dict — 当前请求的模型信息
    api_provider dict — 当前请求的 API Provider 配置
    extra_params dict — 额外参数

请求与返回字段
处理方法参数

    operation str — 请求类型：response、embedding、audio_transcription
    request dict[str, Any] — Host 序列化后的请求内容

返回值字段

返回值必须是可序列化字典。Host 会识别以下字段并恢复为统一响应：

    content / response str — 文本响应或音频转写文本
    reasoning_content / reasoning str — 推理内容
    embedding list[float] — 嵌入向量
    tool_calls list — 工具调用快照
    usage dict — token 使用量字典
    raw_data dict — 原始响应数据

基本用法
方式一：手动分发（简单场景）

在处理方法内通过 if/elif 判断 operation 类型分别处理：

from typing import Any

from maibot_sdk import LLMProvider, MaiBotPlugin


class MyLLMPlugin(MaiBotPlugin):
    async def on_load(self) -> None:
        return None

    async def on_unload(self) -> None:
        return None

    async def on_config_update(self, scope: str, config_data: dict, version: str) -> None:
        pass

    @LLMProvider("my.provider", name="My Provider", description="自定义 LLM Provider")
    async def handle_llm(self, operation: str, request: dict[str, Any]) -> dict[str, Any]:
        if operation == "response":
            return {"content": "你好，我来自插件 Provider"}
        if operation == "embedding":
            return {"embedding": [0.0, 0.1, 0.2]}
        if operation == "audio_transcription":
            return {"content": "音频转写结果"}
        raise ValueError(f"不支持的 LLM Provider 操作类型: {operation}")


def create_plugin():
    return MyLLMPlugin()

方式二：LLMProviderBase 基类（推荐，逻辑较多时）

继承 LLMProviderBase，将分发逻辑交给基类的 dispatch() 方法。子类只需实现关心的 operation 方法，未实现的方法会抛出 NotImplementedError：

from typing import Any

from maibot_sdk import LLMProvider, LLMProviderBase, MaiBotPlugin


class MyProvider(LLMProviderBase):
    """自定义 Provider，只实现 response 能力。"""

    async def get_response(self, request: dict[str, Any]) -> dict[str, Any]:
        # request 包含 message_list、tool_options、model_info 等
        return {"content": "来自 Provider 类的响应"}


class MyLLMPlugin(MaiBotPlugin):
    def __init__(self) -> None:
        super().__init__()
        self.provider = MyProvider()

    async def on_load(self) -> None:
        return None

    async def on_unload(self) -> None:
        return None

    async def on_config_update(self, scope: str, config_data: dict, version: str) -> None:
        pass

    @LLMProvider("my.provider")
    async def handle_llm(self, operation: str, request: dict[str, Any]) -> dict[str, Any]:
        return await self.provider.dispatch(operation, request)


def create_plugin():
    return MyLLMPlugin()

LLMProviderBase 提供以下方法供子类覆写：

    get_response() · operation response — 生成文本或多模态响应（抽象方法，必须实现）
    get_embedding() · operation embedding — 生成文本嵌入（默认抛出 NotImplementedError）
    get_audio_transcriptions() · operation audio_transcription — 生成音频转写（默认抛出 NotImplementedError）

TIP

LLMProviderBase 只是推荐基类，不参与注册。真正的注册入口始终是 @LLMProvider 装饰器。
完整示例

下面是一个完整的最小可用插件，包含 manifest 声明和 Python 代码。

_manifest.json：

{
  "id": "com.example.llm-provider",
  "name": "Example LLM Provider",
  "version": "1.0.0",
  "description": "示例 LLM Provider 插件",
  "author": "example",
  "llm_providers": [
    {
      "client_type": "example.provider",
      "name": "Example Provider",
      "description": "示例 LLM Provider",
      "version": "1.0.0"
    }
  ]
}

main.py：

from typing import Any

from maibot_sdk import LLMProvider, LLMProviderBase, MaiBotPlugin


class ExampleProvider(LLMProviderBase):
    """示例 Provider，实现 response 和 embedding 两种能力。"""

    async def get_response(self, request: dict[str, Any]) -> dict[str, Any]:
        model_info = request.get("model_info", {})
        message_list = request.get("message_list", [])
        # 此处接入实际的 LLM API
        return {
            "content": "来自 example.provider 的响应",
            "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        }

    async def get_embedding(self, request: dict[str, Any]) -> dict[str, Any]:
        embedding_input = request.get("embedding_input", "")
        # 此处接入实际的 Embedding API
        return {"embedding": [0.1, 0.2, 0.3]}


class ExampleLLMPlugin(MaiBotPlugin):
    def __init__(self) -> None:
        super().__init__()
        self.provider = ExampleProvider()

    async def on_load(self) -> None:
        self.ctx.logger.info("Example LLM Provider 插件已加载")

    async def on_unload(self) -> None:
        self.ctx.logger.info("Example LLM Provider 插件已卸载")

    async def on_config_update(self, scope: str, config_data: dict, version: str) -> None:
        pass

    @LLMProvider("example.provider", name="Example Provider", description="示例 LLM Provider")
    async def handle_llm(self, operation: str, request: dict[str, Any]) -> dict[str, Any]:
        return await self.provider.dispatch(operation, request)


def create_plugin():
    return ExampleLLMPlugin()

卸载与回退

当 Provider 插件卸载、禁用或热重载失败时，Host 会注销该插件拥有的 client_type。此后新请求会按主程序的模型回退策略尝试下一个可用模型。

INFO

插件 Provider 暂不支持 Host 侧自定义流式处理器或响应解析器。

*解码核心c代码
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <bcrypt.h>
#ifdef NCMGUI
#include <commdlg.h>
#endif

typedef unsigned char u8;
typedef unsigned int u32;
typedef unsigned long long u64;

#define STATUS_OK(x) ((NTSTATUS)(x) >= 0)

void *memcpy(void *dst, const void *src, size_t n) {
    u8 *d = (u8 *)dst;
    const u8 *s = (const u8 *)src;
    while (n--) *d++ = *s++;
    return dst;
}

static const u8 NCM_MAGIC[8] = { 'C','T','E','N','F','D','A','M' };
static const u8 CORE_KEY[16] = { 'h','z','H','R','A','m','s','o','5','k','I','n','b','a','x','W' };
static const u8 META_KEY[16] = { '#','1','4','l','j','k','_','!','\\',']','&','0','U','<','\'','(' };

static void outa(const char *s) {
    DWORD n = 0, len = 0;
    while (s[len]) len++;
    WriteFile(GetStdHandle(STD_ERROR_HANDLE), s, len, &n, 0);
}

#ifdef NCMGUI
#define LOGA(x) ((void)0)
#else
#define LOGA(x) outa(x)
#endif

static int eq8(const u8 *a, const u8 *b) {
    u32 i;
    for (i = 0; i < 8; i++) if (a[i] != b[i]) return 0;
    return 1;
}

static u32 rd32(const u8 *p) {
    return (u32)p[0] | ((u32)p[1] << 8) | ((u32)p[2] << 16) | ((u32)p[3] << 24);
}

static void xorb(u8 *p, u32 n, u8 v) {
    u32 i;
    for (i = 0; i < n; i++) p[i] ^= v;
}

static void copyb(u8 *d, const u8 *s, u32 n) {
    u32 i;
    for (i = 0; i < n; i++) d[i] = s[i];
}

static u8 *alloc(u32 n) {
    return (u8 *)HeapAlloc(GetProcessHeap(), 0, n ? n : 1);
}

static void freep(void *p) {
    if (p) HeapFree(GetProcessHeap(), 0, p);
}

static int read_all(const WCHAR *path, u8 **data, u32 *size) {
    HANDLE h = CreateFileW(path, GENERIC_READ, FILE_SHARE_READ, 0, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, 0);
    LARGE_INTEGER li;
    DWORD got = 0;
    if (h == INVALID_HANDLE_VALUE) return 0;
    if (!GetFileSizeEx(h, &li) || li.QuadPart <= 0 || li.QuadPart > 0x7fffffff) {
        CloseHandle(h);
        return 0;
    }
    *size = (u32)li.QuadPart;
    *data = alloc(*size);
    if (!*data) {
        CloseHandle(h);
        return 0;
    }
    if (!ReadFile(h, *data, *size, &got, 0) || got != *size) {
        CloseHandle(h);
        freep(*data);
        *data = 0;
        return 0;
    }
    CloseHandle(h);
    return 1;
}

static int write_all(const WCHAR *path, const u8 *data, u32 size) {
    HANDLE h = CreateFileW(path, GENERIC_WRITE, 0, 0, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, 0);
    DWORD done = 0;
    if (h == INVALID_HANDLE_VALUE) return 0;
    while (done < size) {
        DWORD chunk = size - done;
        DWORD wrote = 0;
        if (chunk > 0x100000) chunk = 0x100000;
        if (!WriteFile(h, data + done, chunk, &wrote, 0) || wrote == 0) {
            CloseHandle(h);
            return 0;
        }
        done += wrote;
    }
    CloseHandle(h);
    return 1;
}

static int write_two(const WCHAR *path, const u8 *a, u32 an, const u8 *b, u32 bn) {
    HANDLE h = CreateFileW(path, GENERIC_WRITE, 0, 0, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, 0);
    DWORD w = 0;
    if (h == INVALID_HANDLE_VALUE) return 0;
    if (an && (!WriteFile(h, a, an, &w, 0) || w != an)) { CloseHandle(h); return 0; }
    if (bn && (!WriteFile(h, b, bn, &w, 0) || w != bn)) { CloseHandle(h); return 0; }
    CloseHandle(h);
    return 1;
}

static int aes_ecb_dec(const u8 *in, u32 in_len, const u8 key[16], u8 **out, u32 *out_len) {
    BCRYPT_ALG_HANDLE alg = 0;
    BCRYPT_KEY_HANDLE kh = 0;
    DWORD obj_len = 0, cb = 0, plain_len = 0;
    u8 *obj = 0, *plain = 0;
    int ok = 0;

    if ((in_len & 15) != 0) return 0;
    if (!STATUS_OK(BCryptOpenAlgorithmProvider(&alg, BCRYPT_AES_ALGORITHM, 0, 0))) goto done;
    if (!STATUS_OK(BCryptSetProperty(alg, BCRYPT_CHAINING_MODE, (PUCHAR)BCRYPT_CHAIN_MODE_ECB, sizeof(BCRYPT_CHAIN_MODE_ECB), 0))) goto done;
    if (!STATUS_OK(BCryptGetProperty(alg, BCRYPT_OBJECT_LENGTH, (PUCHAR)&obj_len, sizeof(obj_len), &cb, 0))) goto done;
    obj = alloc(obj_len);
    plain = alloc(in_len);
    if (!obj || !plain) goto done;
    if (!STATUS_OK(BCryptGenerateSymmetricKey(alg, &kh, obj, obj_len, (PUCHAR)key, 16, 0))) goto done;
    if (!STATUS_OK(BCryptDecrypt(kh, (PUCHAR)in, in_len, 0, 0, 0, plain, in_len, &plain_len, 0))) goto done;
    if (plain_len > 0) {
        u8 pad = plain[plain_len - 1];
        if (pad > 0 && pad <= 16 && pad <= plain_len) {
            u32 i, good = 1;
            for (i = plain_len - pad; i < plain_len; i++) {
                if (plain[i] != pad) good = 0;
            }
            if (good) plain_len -= pad;
        }
    }
    *out = plain;
    *out_len = plain_len;
    plain = 0;
    ok = 1;

done:
    if (kh) BCryptDestroyKey(kh);
    if (alg) BCryptCloseAlgorithmProvider(alg, 0);
    freep(obj);
    freep(plain);
    return ok;
}

static void build_keybox(const u8 *key, u32 key_len, u8 box[256]) {
    u32 i, key_offset = 0, last = 0;
    for (i = 0; i < 256; i++) box[i] = (u8)i;
    for (i = 0; i < 256; i++) {
        u8 swap = box[i];
        u32 c = (swap + last + key[key_offset]) & 0xff;
        key_offset++;
        if (key_offset >= key_len) key_offset = 0;
        box[i] = box[c];
        box[c] = swap;
        last = c;
    }
}

static void decrypt_audio(u8 *p, u32 n, const u8 box[256]) {
    u32 i;
    for (i = 0; i < n; i++) {
        u32 j = (i + 1) & 0xff;
        u8 k = box[(box[j] + box[(box[j] + j) & 0xff]) & 0xff];
        p[i] ^= k;
    }
}

static int starts(const u8 *p, u32 n, const char *s) {
    u32 i = 0;
    while (s[i]) {
        if (i >= n || p[i] != (u8)s[i]) return 0;
        i++;
    }
    return 1;
}

#ifdef NCMTAGS
typedef struct TagInfo {
    u8 *title; u32 title_n;
    u8 *artist; u32 artist_n;
    u8 *album; u32 album_n;
    const u8 *cover; u32 cover_n;
} TagInfo;

static int hval(u8 c) {
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return -1;
}

static void put_utf8(u8 *o, u32 *n, u32 cp) {
    if (cp < 0x80) o[(*n)++] = (u8)cp;
    else if (cp < 0x800) {
        o[(*n)++] = (u8)(0xc0 | (cp >> 6));
        o[(*n)++] = (u8)(0x80 | (cp & 0x3f));
    } else {
        o[(*n)++] = (u8)(0xe0 | (cp >> 12));
        o[(*n)++] = (u8)(0x80 | ((cp >> 6) & 0x3f));
        o[(*n)++] = (u8)(0x80 | (cp & 0x3f));
    }
}

static u8 *json_str(const u8 *p, const u8 *end, u32 *out_n) {
    u8 *o;
    u32 n = 0;
    if (p >= end || *p != '"') return 0;
    p++;
    o = alloc((u32)(end - p) + 1);
    if (!o) return 0;
    while (p < end && *p != '"') {
        if (*p == '\\' && p + 1 < end) {
            p++;
            if (*p == 'u' && p + 4 < end) {
                int a = hval(p[1]), b = hval(p[2]), c = hval(p[3]), d = hval(p[4]);
                if (a >= 0 && b >= 0 && c >= 0 && d >= 0) {
                    put_utf8(o, &n, (u32)((a << 12) | (b << 8) | (c << 4) | d));
                    p += 5;
                    continue;
                }
            }
            if (*p == 'n') o[n++] = '\n';
            else if (*p == 't') o[n++] = '\t';
            else o[n++] = *p;
            p++;
        } else {
            o[n++] = *p++;
        }
    }
    o[n] = 0;
    *out_n = n;
    return o;
}

static const u8 *find_key(const u8 *p, const u8 *end, const char *key) {
    u32 k = 0, i;
    while (key[k]) k++;
    for (; p + k + 2 < end; p++) {
        if (*p != '"') continue;
        for (i = 0; i < k && p[1 + i] == (u8)key[i]; i++);
        if (i == k && p[1 + k] == '"') {
            p += k + 2;
            while (p < end && (*p == ' ' || *p == '\t' || *p == '\r' || *p == '\n')) p++;
            if (p < end && *p == ':') return p + 1;
        }
    }
    return 0;
}

static u8 *field_str(const u8 *json, u32 len, const char *key, u32 *out_n) {
    const u8 *p = find_key(json, json + len, key);
    if (!p) return 0;
    while (p < json + len && (*p == ' ' || *p == '\t' || *p == '\r' || *p == '\n')) p++;
    return json_str(p, json + len, out_n);
}

static u8 *artist_str(const u8 *json, u32 len, u32 *out_n) {
    const u8 *p = find_key(json, json + len, "artist");
    const u8 *end = json + len;
    u8 *out;
    u32 n = 0, cap = 256, sn = 0, depth = 0, count = 0;
    if (!p) return 0;
    out = alloc(cap);
    if (!out) return 0;
    for (; p < end; p++) {
        if (*p == '[') depth++;
        else if (*p == ']') {
            if (depth == 0) break;
            depth--;
            if (depth == 0) break;
        } else if (*p == '"' && depth >= 2) {
            u8 *s = json_str(p, end, &sn);
            if (s && sn) {
                if (n + sn + 2 > cap) {
                    freep(s);
                    break;
                }
                if (count++) out[n++] = '/';
                copyb(out + n, s, sn);
                n += sn;
            }
            freep(s);
            while (p < end && *p != '"') p++;
            if (p < end) p++;
            while (p < end && *p != '"') p++;
        }
    }
    if (!n) { freep(out); return 0; }
    out[n] = 0;
    *out_n = n;
    return out;
}

static int b64val(u8 c) {
    if (c >= 'A' && c <= 'Z') return c - 'A';
    if (c >= 'a' && c <= 'z') return c - 'a' + 26;
    if (c >= '0' && c <= '9') return c - '0' + 52;
    if (c == '+') return 62;
    if (c == '/') return 63;
    return -1;
}

static u8 *b64dec(const u8 *in, u32 n, u32 *out_n) {
    u8 *out = alloc((n / 4 + 1) * 3);
    u32 i, o = 0;
    if (!out) return 0;
    for (i = 0; i + 3 < n; i += 4) {
        int a = b64val(in[i]), b = b64val(in[i + 1]);
        int c = in[i + 2] == '=' ? -2 : b64val(in[i + 2]);
        int d = in[i + 3] == '=' ? -2 : b64val(in[i + 3]);
        if (a < 0 || b < 0 || c < -2 || d < -2) break;
        out[o++] = (u8)((a << 2) | (b >> 4));
        if (c >= 0) out[o++] = (u8)((b << 4) | (c >> 2));
        if (d >= 0 && c >= 0) out[o++] = (u8)((c << 6) | d);
    }
    *out_n = o;
    return out;
}

static void parse_meta(u8 *meta, u32 meta_len, TagInfo *t) {
    static const char pref[] = "163 key(Don't modify):";
    u32 pn = sizeof(pref) - 1, dec_n = 0, plain_n = 0;
    u8 *dec = 0, *plain = 0, *json;
    if (meta_len <= pn) return;
    xorb(meta, meta_len, 0x63);
    if (!starts(meta, meta_len, pref)) return;
    dec = b64dec(meta + pn, meta_len - pn, &dec_n);
    if (!dec) return;
    if (aes_ecb_dec(dec, dec_n, META_KEY, &plain, &plain_n) && plain_n > 6) {
        json = plain;
        if (starts(json, plain_n, "music:")) { json += 6; plain_n -= 6; }
        t->title = field_str(json, plain_n, "musicName", &t->title_n);
        t->album = field_str(json, plain_n, "album", &t->album_n);
        t->artist = artist_str(json, plain_n, &t->artist_n);
    }
    freep(plain);
    freep(dec);
}

static void be32(u8 *p, u32 v) {
    p[0] = (u8)(v >> 24); p[1] = (u8)(v >> 16); p[2] = (u8)(v >> 8); p[3] = (u8)v;
}

static void sync32(u8 *p, u32 v) {
    p[0] = (u8)((v >> 21) & 0x7f); p[1] = (u8)((v >> 14) & 0x7f); p[2] = (u8)((v >> 7) & 0x7f); p[3] = (u8)(v & 0x7f);
}

static u32 u16n(const u8 *s, u32 n) {
    u32 i = 0, out = 0;
    while (i < n) {
        u8 c = s[i++];
        if ((c & 0xe0) == 0xc0 && i < n) i++;
        else if ((c & 0xf0) == 0xe0 && i + 1 < n) i += 2;
        out += 2;
    }
    return out;
}

static u32 w16(u8 *o, const u8 *s, u32 n) {
    u32 i = 0, out = 0, cp;
    while (i < n) {
        u8 c = s[i++];
        if ((c & 0xe0) == 0xc0 && i < n) {
            cp = ((u32)(c & 0x1f) << 6) | (s[i++] & 0x3f);
        } else if ((c & 0xf0) == 0xe0 && i + 1 < n) {
            cp = ((u32)(c & 0x0f) << 12) | ((u32)(s[i] & 0x3f) << 6) | (s[i + 1] & 0x3f);
            i += 2;
        } else {
            cp = c;
        }
        o[out++] = (u8)cp;
        o[out++] = (u8)(cp >> 8);
    }
    return out;
}

static u32 frame_text(u8 *o, const char *id, const u8 *s, u32 n) {
    u32 wn;
    if (!s || !n) return 0;
    wn = u16n(s, n);
    o[0] = id[0]; o[1] = id[1]; o[2] = id[2]; o[3] = id[3];
    be32(o + 4, wn + 3);
    o[8] = o[9] = 0;
    o[10] = 1;
    o[11] = 0xff;
    o[12] = 0xfe;
    w16(o + 13, s, n);
    return wn + 13;
}

static u32 frame_apic(u8 *o, const u8 *img, u32 n) {
    const char *mime = (n > 4 && img[0] == 0x89 && img[1] == 'P') ? "image/png" : "image/jpeg";
    u32 ml = 0, i, sz;
    if (!img || !n) return 0;
    while (mime[ml]) ml++;
    sz = 1 + ml + 1 + 1 + 1 + n;
    o[0] = 'A'; o[1] = 'P'; o[2] = 'I'; o[3] = 'C';
    be32(o + 4, sz);
    o[8] = o[9] = 0;
    o[10] = 3;
    for (i = 0; i < ml; i++) o[11 + i] = (u8)mime[i];
    o[11 + ml] = 0;
    o[12 + ml] = 3;
    o[13 + ml] = 0;
    copyb(o + 14 + ml, img, n);
    return sz + 10;
}

static u8 *make_id3(TagInfo *t, u32 *tag_n) {
    u32 cap = 10 + 128 + (t->title_n + t->artist_n + t->album_n) * 2 + t->cover_n;
    u8 *tag = alloc(cap), *p;
    u32 n = 10, fs;
    if (!tag) return 0;
    tag[0] = 'I'; tag[1] = 'D'; tag[2] = '3'; tag[3] = 3; tag[4] = 0; tag[5] = 0;
    n += frame_text(tag + n, "TIT2", t->title, t->title_n);
    n += frame_text(tag + n, "TPE1", t->artist, t->artist_n);
    n += frame_text(tag + n, "TALB", t->album, t->album_n);
    n += frame_apic(tag + n, t->cover, t->cover_n);
    if (n == 10) { freep(tag); return 0; }
    sync32(tag + 6, n - 10);
    *tag_n = n;
    return tag;
}
#endif

static const char *detect_ext(const u8 *p, u32 n) {
    if (n >= 4 && p[0] == 'f' && p[1] == 'L' && p[2] == 'a' && p[3] == 'C') return "flac";
    if (n >= 3 && p[0] == 'I' && p[1] == 'D' && p[2] == '3') return "mp3";
    if (n >= 2 && p[0] == 0xff && (p[1] & 0xe0) == 0xe0) return "mp3";
    if (n >= 8 && p[4] == 'f' && p[5] == 't' && p[6] == 'y' && p[7] == 'p') return "m4a";
    return "bin";
}

static u32 wlen(const WCHAR *s) {
    u32 n = 0;
    while (s[n]) n++;
    return n;
}

static WCHAR *make_out_path(const WCHAR *input, const char *ext) {
    u32 len = wlen(input), i, slash = 0xffffffff, dot = 0xffffffff, base_len, ext_len = 0;
    WCHAR *out;
    while (ext[ext_len]) ext_len++;
    for (i = 0; i < len; i++) {
        if (input[i] == L'\\' || input[i] == L'/') slash = i;
        if (input[i] == L'.') dot = i;
    }
    if (dot == 0xffffffff || (slash != 0xffffffff && dot < slash)) dot = len;
    base_len = dot;
    out = (WCHAR *)HeapAlloc(GetProcessHeap(), 0, (base_len + 1 + ext_len + 1) * sizeof(WCHAR));
    if (!out) return 0;
    for (i = 0; i < base_len; i++) out[i] = input[i];
    out[base_len] = L'.';
    for (i = 0; i < ext_len; i++) out[base_len + 1 + i] = (WCHAR)ext[i];
    out[base_len + 1 + ext_len] = 0;
    return out;
}

static int convert(const WCHAR *in_path, const WCHAR *out_arg) {
    u8 *file = 0, *key_block = 0, *key_plain = 0, *audio = 0;
#ifdef NCMTAGS
    u8 *meta_block = 0, *id3 = 0;
    u32 id3_len = 0;
    TagInfo tags;
#endif
    u32 file_len = 0, pos = 0, key_len = 0, key_plain_len = 0, meta_len = 0, img_len = 0, audio_len = 0;
    u8 keybox[256];
    const char *ext;
    WCHAR *out_path = 0;
    int ok = 0;
#ifdef NCMTAGS
    tags.title = tags.artist = tags.album = 0;
    tags.title_n = tags.artist_n = tags.album_n = 0;
    tags.cover = 0;
    tags.cover_n = 0;
#endif

    if (!read_all(in_path, &file, &file_len)) { LOGA("read failed\n"); goto done; }
    if (file_len < 32 || !eq8(file, NCM_MAGIC)) { LOGA("not ncm\n"); goto done; }
    pos = 10;

    if (pos + 4 > file_len) goto bad;
    key_len = rd32(file + pos); pos += 4;
    if (key_len == 0 || pos + key_len > file_len) goto bad;
    key_block = alloc(key_len);
    if (!key_block) goto done;
    copyb(key_block, file + pos, key_len); pos += key_len;
    xorb(key_block, key_len, 0x64);
    if (!aes_ecb_dec(key_block, key_len, CORE_KEY, &key_plain, &key_plain_len)) goto bad;
    if (key_plain_len <= 17) goto bad;
    build_keybox(key_plain + 17, key_plain_len - 17, keybox);

    if (pos + 4 > file_len) goto bad;
    meta_len = rd32(file + pos); pos += 4;
    if (pos + meta_len > file_len) goto bad;
#ifdef NCMTAGS
    if (meta_len) {
        meta_block = alloc(meta_len);
        if (!meta_block) goto done;
        copyb(meta_block, file + pos, meta_len);
        parse_meta(meta_block, meta_len, &tags);
    }
#endif
    pos += meta_len;

    if (pos + 13 > file_len) goto bad;
    pos += 4;
    pos += 5;
    img_len = rd32(file + pos); pos += 4;
    if (pos + img_len > file_len) goto bad;
#ifdef NCMTAGS
    if (img_len) {
        tags.cover = file + pos;
        tags.cover_n = img_len;
    }
#endif
    pos += img_len;

    audio_len = file_len - pos;
    audio = alloc(audio_len);
    if (!audio) goto done;
    copyb(audio, file + pos, audio_len);
    decrypt_audio(audio, audio_len, keybox);

    ext = detect_ext(audio, audio_len);
    out_path = out_arg ? (WCHAR *)out_arg : make_out_path(in_path, ext);
    if (!out_path) goto done;
#ifdef NCMTAGS
    if (ext[0] == 'm' && ext[1] == 'p' && ext[2] == '3') {
        id3 = make_id3(&tags, &id3_len);
    }
    if (id3) {
        if (!write_two(out_path, id3, id3_len, audio, audio_len)) { LOGA("write failed\n"); goto done; }
    } else
#endif
    if (!write_all(out_path, audio, audio_len)) { LOGA("write failed\n"); goto done; }
    LOGA("ok\n");
    ok = 1;
    goto done;

bad:
    LOGA("bad ncm\n");
done:
    if (!out_arg) freep(out_path);
#ifdef NCMTAGS
    freep(id3);
    freep(tags.title);
    freep(tags.artist);
    freep(tags.album);
    freep(meta_block);
#endif
    freep(audio);
    freep(key_plain);
    freep(key_block);
    freep(file);
    return ok;
}

static WCHAR *skip_ws(WCHAR *p) {
    while (*p == L' ' || *p == L'\t') p++;
    return p;
}

static WCHAR *next_arg(WCHAR **cursor) {
    WCHAR *p = skip_ws(*cursor);
    WCHAR *start;
    if (!*p) return 0;
    if (*p == L'"') {
        p++;
        start = p;
        while (*p && *p != L'"') p++;
        if (*p) *p++ = 0;
    } else {
        start = p;
        while (*p && *p != L' ' && *p != L'\t') p++;
        if (*p) *p++ = 0;
    }
    *cursor = p;
    return start;
}

void mainCRTStartup(void) {
#ifndef NCMGUI
    WCHAR *cmd = GetCommandLineW();
    WCHAR *p = cmd;
    WCHAR *exe, *in, *out;
    int code;
    exe = next_arg(&p);
    (void)exe;
    in = next_arg(&p);
    out = next_arg(&p);
    if (!in) {
        outa("usage: ncmmini.exe input.ncm [output]\n");
        ExitProcess(1);
    }
    code = convert(in, out) ? 0 : 2;
    ExitProcess((UINT)code);
#else
    static OPENFILENAMEW ofn;
    static WCHAR file[32768];
    static WCHAR filter[] = L"NCM\0*.ncm\0\0";
    int ok;

    ofn.lStructSize = sizeof(ofn);
    ofn.hwndOwner = 0;
    ofn.lpstrFilter = filter;
    ofn.lpstrFile = file;
    ofn.nMaxFile = sizeof(file) / sizeof(file[0]);
    ofn.Flags = OFN_FILEMUSTEXIST | OFN_PATHMUSTEXIST | OFN_EXPLORER;
    ofn.lpstrTitle = L"NCM";

    if (!GetOpenFileNameW(&ofn)) {
        ExitProcess(0);
    }

    ok = convert(file, 0);
    MessageBoxW(0,
        ok ? L"OK" : L"FAIL",
        L"NCM",
        ok ? MB_OK | MB_ICONINFORMATION : MB_OK | MB_ICONERROR);
    ExitProcess(ok ? 0 : 2);
#endif
}

*编译器
@echo off
setlocal
set "ROOT=%~dp0"
set "VC=C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars32.bat"
if not exist "%VC%" goto missing
call "%VC%" >nul
cl /nologo /utf-8 /O1 /Os /GS- /Gy /Gw /DNCMGUI /DNCMTAGS /TC "%ROOT%ncmmini.c" /Fo"%ROOT%ncmmini.obj" /Fe"%ROOT%NCMConverter.exe" /link /NODEFAULTLIB /ENTRY:mainCRTStartup /SUBSYSTEM:WINDOWS /OPT:REF /OPT:ICF /MERGE:.rdata=.text kernel32.lib user32.lib comdlg32.lib bcrypt.lib
if errorlevel 1 exit /b 1
del "%ROOT%ncmmini.obj" 2>nul
dir "%ROOT%NCMConverter.exe"
exit /b 0
:missing
echo vcvars32.bat not found
exit /b 1

*我自己的插件示例（Nightmare）
~~~
**现在，请将c源码迁移为python语言，并同步nightmare插件的注释风格生成TryX（1），包含四个必要的插件文件，并先给出免责文案，我去创建项目。