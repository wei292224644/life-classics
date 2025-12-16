"""
网络搜索工具 - 用于在知识库中没有相关信息时搜索网络内容
"""

from typing import List, Optional
from langchain_core.tools import tool
from app.core.config import settings
import requests
import json


def web_search_tool_function(query: str, num_results: int = 5) -> str:
    """
    执行网络搜索

    Args:
        query: 搜索查询字符串
        num_results: 返回结果数量，默认5条

    Returns:
        搜索结果摘要文本
    """
    try:
        # 使用 DuckDuckGo 搜索（免费，无需 API 密钥）
        # 或者可以使用其他搜索 API，如 Google Custom Search, Bing Search API 等

        if settings.SEARCH_PROVIDER == "duckduckgo":
            return _duckduckgo_search(query, num_results)
        elif settings.SEARCH_PROVIDER == "tavily":
            return _tavily_search(query, num_results)
        elif settings.SEARCH_PROVIDER == "serper":
            return _serper_search(query, num_results)
        else:
            # 默认使用 DuckDuckGo
            return _duckduckgo_search(query, num_results)
    except Exception as e:
        return f"搜索时出错: {str(e)}"


def _duckduckgo_search(query: str, num_results: int = 5) -> str:
    """
    使用 DuckDuckGo 搜索（免费，无需 API 密钥）
    注意：DuckDuckGo 没有官方 API，这里使用 duckduckgo-search 库或直接请求
    """
    from ddgs import DDGS

    # 添加调试日志，记录实际接收到的查询参数
    import logging

    logger = logging.getLogger(__name__)
    logger.warning(f"[DEBUG] DuckDuckGo 搜索接收到的查询参数: {query!r}")

    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=num_results):
            results.append(
                {
                    "title": r.get("title", ""),
                    "snippet": r.get("body", ""),
                    "url": r.get("href", ""),
                }
            )

    if not results:
        return "未找到相关搜索结果。"

    # 格式化结果
    formatted_results = []
    for i, result in enumerate(results, 1):
        formatted_results.append(
            f"[{i}] {result['title']}\n"
            f"摘要: {result['snippet'][:200]}...\n"
            f"链接: {result['url']}\n"
        )

    return "\n".join(formatted_results)


def _tavily_search(query: str, num_results: int = 5) -> str:
    """
    使用 Tavily Search API（需要 API 密钥）
    """
    if not settings.TAVILY_API_KEY:
        return "Tavily API 密钥未配置，无法使用搜索功能。"

    try:
        url = "https://api.tavily.com/search"
        payload = {
            "api_key": settings.TAVILY_API_KEY,
            "query": query,
            "search_depth": "basic",
            "max_results": num_results,
        }

        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()

        results = []
        for result in data.get("results", []):
            results.append(
                {
                    "title": result.get("title", ""),
                    "content": result.get("content", ""),
                    "url": result.get("url", ""),
                }
            )

        if not results:
            return "未找到相关搜索结果。"

        # 格式化结果
        formatted_results = []
        for i, result in enumerate(results, 1):
            formatted_results.append(
                f"[{i}] {result['title']}\n"
                f"内容: {result['content'][:300]}...\n"
                f"链接: {result['url']}\n"
            )

        return "\n".join(formatted_results)
    except Exception as e:
        return f"Tavily 搜索失败: {str(e)}"


def _serper_search(query: str, num_results: int = 5) -> str:
    """
    使用 Serper API（Google 搜索，需要 API 密钥）
    """
    if not settings.SERPER_API_KEY:
        return "Serper API 密钥未配置，无法使用搜索功能。"

    try:
        url = "https://google.serper.dev/search"
        headers = {
            "X-API-KEY": settings.SERPER_API_KEY,
            "Content-Type": "application/json",
        }
        payload = {"q": query, "num": num_results}

        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()

        results = []
        for result in data.get("organic", []):
            results.append(
                {
                    "title": result.get("title", ""),
                    "snippet": result.get("snippet", ""),
                    "url": result.get("link", ""),
                }
            )

        if not results:
            return "未找到相关搜索结果。"

        # 格式化结果
        formatted_results = []
        for i, result in enumerate(results, 1):
            formatted_results.append(
                f"[{i}] {result['title']}\n"
                f"摘要: {result['snippet'][:200]}...\n"
                f"链接: {result['url']}\n"
            )

        return "\n".join(formatted_results)
    except Exception as e:
        return f"Serper 搜索失败: {str(e)}"


@tool
def web_search(query: str, num_results: int = 5) -> str:
    """
    该工具仅用于查询与食品安全相关的“近期 / 最新 / 时效性”信息。

    允许使用场景包括但不限于：
    - 近期食品安全事件或舆情
    - 最新法规、标准修订或官方通报
    - 最近的风险预警、召回信息

    禁止使用场景：
    - 知识库中已存在的信息
    - 非时间敏感的基础知识
    - 常识性解释或背景说明


    Args:
        query: 搜索关键词，必须是用户问题的核心内容，不要使用知识库检索到的无关内容
        num_results: 返回结果数量，默认5
    """
    # 添加调试日志
    import logging

    logger = logging.getLogger(__name__)
    logger.info(
        f"[DEBUG] web_search 工具被调用，query={query!r}, num_results={num_results}"
    )
    print(f"[DEBUG] web_search 工具被调用，query={query!r}, num_results={num_results}")

    return web_search_tool_function(query, num_results)


def get_web_search_tool():
    """获取网络搜索工具实例"""
    return web_search
