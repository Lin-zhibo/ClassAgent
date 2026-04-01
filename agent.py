"""为 main.py 提供 LLM 对话客户端。"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterable

from dotenv import load_dotenv
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam


def get_project_root(current_file: Path | None = None) -> Path:
    """
    功能:
        获取项目根目录路径，默认定位到当前文件所在目录。
    参数:
        current_file: 当前文件路径；不传时使用本文件路径定位项目根目录。
    返回值:
        Path: 项目根目录的路径对象。
    """
    if current_file is None:
        current_file = Path(__file__).resolve()
    return current_file.parent


def load_model_config(config_path: Path | None = None) -> dict[str, str]:
    """
    功能:
        从 JSON 配置文件中读取模型名称和基础 URL，并做必要的字段校验。
    参数:
        config_path: 配置文件路径；不传时默认读取 config/models.json。
    返回值:
        dict[str, str]: 包含 MODEL_NAME 与 URL 两个字段的配置字典。
    """
    if config_path is None:
        config_path = get_project_root() / "config" / "models.json"

    if not config_path.exists():
        raise FileNotFoundError(f"未找到模型配置文件: {config_path}")

    with config_path.open("r", encoding="utf-8") as config_file:
        config_data = json.load(config_file)

    model_name = str(config_data.get("MODEL_NAME", "")).strip()
    base_url = str(config_data.get("URL", "")).strip()

    if not model_name:
        raise ValueError("配置项 MODEL_NAME 不能为空。")
    if not base_url:
        raise ValueError("配置项 URL 不能为空。")

    return {"MODEL_NAME": model_name, "URL": base_url}


def load_api_key(env_path: Path | None = None, key_names: Iterable[str] | None = None) -> str:
    """
    功能:
        从 .env 文件和系统环境变量中读取可用的 API Key。
    参数:
        env_path: .env 文件路径；不传时默认读取 config/.env。
        key_names: 允许读取的键名列表；不传时使用内置的常见键名顺序。
    返回值:
        str: 第一个读取到且非空的 API Key 字符串。
    """
    if env_path is None:
        env_path = get_project_root() / "config" / ".env"

    if env_path.exists():
        load_dotenv(dotenv_path=env_path)

    if key_names is None:
        key_names = ("OPENAI_API_KEY", "API_KEY", "KEY", "key")

    for key_name in key_names:
        api_key = os.getenv(key_name, "").strip()
        if api_key:
            return api_key

    raise ValueError(
        "未找到可用的 API Key。请在 config/.env 或系统环境变量中设置 OPENAI_API_KEY。"
    )


def create_openai_client(api_key: str, base_url: str) -> OpenAI:
    """
    功能:
        使用给定的认证信息和网关地址创建 OpenAI SDK 客户端实例。
    参数:
        api_key: 用于鉴权的 API Key。
        base_url: 模型服务的基础 URL。
    返回值:
        OpenAI: 已初始化完成、可直接发起对话请求的 SDK 客户端对象。
    """
    return OpenAI(api_key=api_key, base_url=base_url)


class LLMClient:
    """对 OpenAI SDK 进行轻量封装，提供简洁的对话调用接口。"""

    def __init__(self, model_name: str, base_url: str, api_key: str) -> None:
        """
        功能:
            初始化对话客户端并缓存模型配置，供后续对话调用复用。
        参数:
            model_name: 发起对话时使用的模型名称。
            base_url: 模型服务地址。
            api_key: 调用模型服务所需的 API Key。
        返回值:
            None: 构造函数仅完成实例初始化，不返回额外结果。
        """
        self.model_name = model_name
        self.client = create_openai_client(api_key=api_key, base_url=base_url)

    @classmethod
    def from_config(
        cls, config_path: Path | None = None, env_path: Path | None = None
    ) -> "LLMClient":
        """
        功能:
            从配置文件与 .env 中读取参数，并构建一个可直接使用的 LLMClient 实例。
        参数:
            config_path: 模型配置文件路径；不传时默认使用 config/models.json。
            env_path: 环境变量文件路径；不传时默认使用 config/.env。
        返回值:
            LLMClient: 完整初始化后的对话客户端实例。
        """
        config = load_model_config(config_path=config_path)
        api_key = load_api_key(env_path=env_path)
        return cls(
            model_name=config["MODEL_NAME"],
            base_url=config["URL"],
            api_key=api_key,
        )

    def chat(
        self,
        user_message: str,
        system_message: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> str:
        """
        功能:
            向模型发送一次聊天请求，并返回模型生成的文本内容。
        参数:
            user_message: 用户输入的问题或指令。
            system_message: 可选的系统角色提示词，用于控制模型行为。
            temperature: 采样温度，值越高输出越发散。
            max_tokens: 可选的最大输出 token 数限制。
        返回值:
            str: 模型返回的首条文本回复，已去除首尾空白。
        """
        messages: list[ChatCompletionMessageParam] = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": user_message})

        if max_tokens is None:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=temperature,
            )
        else:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

        content = response.choices[0].message.content
        if content is None:
            raise RuntimeError("模型返回内容为空，请检查模型服务是否可用。")
        return content.strip()
