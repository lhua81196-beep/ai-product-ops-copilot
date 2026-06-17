# -*- coding: utf-8 -*-
"""
DeepSeek API 封装模块
通过 OpenAI SDK 兼容接口调用 DeepSeek API。
"""

import os
from typing import Optional
import json
import re

from openai import OpenAI

# 默认配置
DEFAULT_MODEL = "deepseek-chat"
DEFAULT_TEMPERATURE = 0.8
DEFAULT_MAX_TOKENS = 4096


def get_client() -> OpenAI:
    """初始化并返回 DeepSeek API 客户端。"""
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError(
            "未设置 DEEPSEEK_API_KEY 环境变量。"
            "请在项目根目录创建 .env 文件并添加：DEEPSEEK_API_KEY=your_key"
        )
    return OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com/v1",
    )


def chat(
    system_prompt: str,
    user_prompt: str,
    model: str = DEFAULT_MODEL,
    temperature: float = DEFAULT_TEMPERATURE,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    stream: bool = False,
) -> str:
    """调用 DeepSeek Chat 模型。

    Args:
        system_prompt: 系统指令
        user_prompt: 用户输入
        model: 模型名称
        temperature: 生成温度
        max_tokens: 最大输出长度
        stream: 是否流式输出

    Returns:
        模型生成的文本内容
    """
    client = get_client()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
        stream=stream,
    )

    if stream:
        collected = []
        for chunk in response:
            delta = chunk.choices[0].delta
            if delta.content:
                collected.append(delta.content)
        return "".join(collected)

    return response.choices[0].message.content or ""


def chat_stream(
    system_prompt: str,
    user_prompt: str,
    model: str = DEFAULT_MODEL,
    temperature: float = DEFAULT_TEMPERATURE,
    max_tokens: int = DEFAULT_MAX_TOKENS,
):
    """流式调用 DeepSeek Chat 模型，逐 block 产出文本。

    是一个生成器函数，每次 yield 一个文本片段。
    """
    client = get_client()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
        stream=True,
    )

    for chunk in response:
        delta = chunk.choices[0].delta
        if delta.content:
            yield delta.content


def chat_json(
    system_prompt: str,
    user_prompt: str,
    model: str = DEFAULT_MODEL,
    temperature: float = DEFAULT_TEMPERATURE,
    max_tokens: int = 2048,
) -> list:
    """调用 DeepSeek 并安全解析返回的 JSON 数据。

    多层兜底策略：
    1. 直接 json.loads
    2. 提取 ```json ... ``` 代码块
    3. 正则提取第一个 [...] 数组
    4. 提取第一个 {...} 对象并包裹为数组
    5. 以上全部失败 → 返回标准空结构（永不抛异常）

    Returns:
        解析后的 list[dict]；完全失败时返回含一条空记录的标准结构
    """
    text = chat(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        stream=False,
    )

    raw = text.strip()

    # ------ 策略 1: 直接解析 ------
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else [data]
    except (json.JSONDecodeError, TypeError):
        pass

    # ------ 策略 2: 提取 ```json ... ``` 代码块 ------
    code_blocks = re.findall(
        r"```(?:json)?\s*\n?(.*?)\n?```", raw, re.DOTALL
    )
    if code_blocks:
        for block in reversed(code_blocks):  # 优先取最后一个（最完整）
            block = block.strip()
            try:
                data = json.loads(block)
                return data if isinstance(data, list) else [data]
            except (json.JSONDecodeError, TypeError):
                continue

    # ------ 策略 3: 正则提取第一个 [...] 数组 ------
    array_match = re.search(r"\[.*?\]", raw, re.DOTALL)
    if array_match:
        try:
            data = json.loads(array_match.group())
            return data if isinstance(data, list) else [data]
        except (json.JSONDecodeError, TypeError):
            pass

    # ------ 策略 4: 提取第一个 {...} 对象并包装为数组 ------
    # 从左到右依次尝试，取第一个可解析的对象
    for m in re.finditer(r"\{[^{}]*\}", raw):
        try:
            obj = json.loads(m.group())
            if isinstance(obj, dict):
                return [obj]
        except (json.JSONDecodeError, TypeError):
            continue

    # ------ 策略 5: 全部失败 → 标准空结构（永不抛异常）------
    return [
        {
            "product": "",
            "positioning": "",
            "target_user": "",
            "core_advantage": "",
            "core_disadvantage": "",
            "business_model": "",
            "confidence": 0.0,
            "confidence_reason": "",
        }
    ]
