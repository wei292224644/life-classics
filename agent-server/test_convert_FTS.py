import json
import time

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.llm import chat


def main():
    row_content = {
        "chunk_id": "73c76ce5f3201066",
        "doc_id": "20120518_10_analysis",
        "doc_title": "20120518_10_analysis",
        "section_path": [
            "附 录 A 检验方法",
            "A.2 鉴别试验",
            "A.2.1 溶解性试验",
            "A.2.1.1 试剂和材料",
        ],
        "content_type": "reagent",
        "content": ["A.2.1.1.1 乙醇", "A.2.1.1.2 植物油"],
        "meta": {"standard_type": "国家标准", "source": "20120518_10_analysis.md"},
    }
    row_content_str = json.dumps(row_content, ensure_ascii=False)
    print(row_content_str)

    system_prompt = """你是一个“全文检索索引生成器（FTS Index Generator）”。

你的任务不是生成自然语言，而是从结构化内容中提取
“最有利于全文检索（FTS/BM25）的关键词搜索句”。

你生成的文本将用于数据库全文索引，不会直接展示给用户。
    """

    human_prompt = f"""你将收到一段结构化的 chunk（JSON 或类似结构）。

请遵循以下规则生成【一行】全文检索搜索句：

【生成规则】
1. 只输出关键词或短语，用空格分隔
2. 不要生成完整句子，不要使用“的、是、用于”等虚词
6. 不添加原文中不存在的专业概念
7. 输出内容顺序不重要，但应尽量覆盖所有可检索要点
8. 输出为【纯文本一行】，不要 JSON，不要 Markdown，不要解释
9. 内容必须完整，不要遗漏任何信息
10. 内容必须准确，不要添加任何主观判断或解释

【输入结构化 chunk】
{row_content_str}
"""
    start_time = time.time()
    print("开始时间：", time.time())
    response = chat(
        messages=[
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt),
        ],
        provider_name="ollama",
        provider_config={"model": "qwen3:1.7b", "temperature": 0.1, "reasoning": False},
    )
    print("=" * 20)
    print(response)
    print("=" * 20)
    print("结束时间：", time.time())
    print("耗时：", time.time() - start_time)


if __name__ == "__main__":
    main()
