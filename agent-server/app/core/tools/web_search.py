"""
网络搜索工具 - 用于在知识库中没有相关信息时搜索网络内容
"""
from typing import List, Optional
from llama_index.core.tools import FunctionTool
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
    try:
        # 方法1: 使用 duckduckgo-search 库（需要安装: pip install duckduckgo-search）
        try:
            from duckduckgo_search import DDGS
            
            results = []
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=num_results):
                    results.append({
                        "title": r.get("title", ""),
                        "snippet": r.get("body", ""),
                        "url": r.get("href", "")
                    })
            
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
        except ImportError:
            # 如果库未安装，使用简单的 HTTP 请求
            return _simple_http_search(query, num_results)
    except Exception as e:
        return f"DuckDuckGo 搜索失败: {str(e)}"


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
            "max_results": num_results
        }
        
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        results = []
        for result in data.get("results", []):
            results.append({
                "title": result.get("title", ""),
                "content": result.get("content", ""),
                "url": result.get("url", "")
            })
        
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
            "Content-Type": "application/json"
        }
        payload = {
            "q": query,
            "num": num_results
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        results = []
        for result in data.get("organic", []):
            results.append({
                "title": result.get("title", ""),
                "snippet": result.get("snippet", ""),
                "url": result.get("link", "")
            })
        
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


def _simple_http_search(query: str, num_results: int = 5) -> str:
    """
    简单的 HTTP 搜索（备用方案）
    注意：这只是一个占位符，实际使用时需要安装 duckduckgo-search 或配置其他搜索 API
    """
    return f"搜索功能需要安装 duckduckgo-search 库或配置搜索 API 密钥。\n查询: {query}"


def get_web_search_tool() -> FunctionTool:
    """
    获取网络搜索工具实例
    
    Returns:
        FunctionTool: LlamaIndex 工具实例
    """
    return FunctionTool.from_defaults(
        fn=web_search_tool_function,
        name="web_search",
        description=(
            "当知识库中没有相关信息时，使用此工具搜索网络获取最新信息。"
            "特别适用于："
            "- 查询公司或品牌的近期新闻、事件"
            "- 查询食品安全问题、产品召回等最新信息"
            "- 查询当前日期、时间相关的信息"
            "- 查询知识库中没有的实时信息"
            "参数: query (搜索关键词), num_results (返回结果数量，默认5)"
        ),
    )
