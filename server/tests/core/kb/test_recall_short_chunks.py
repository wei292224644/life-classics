"""
召回率测试：验证 embedding 模型对短 chunks 的召回能力。

测试场景：查询"需要哪些试剂"时，切分后的 4 个 chunks 是否都能被召回。
"""
import asyncio
import numpy as np
from kb.embeddings import embed_batch


def cosine_similarity(a: list[float], b: list[float]) -> float:
    a = np.array(a)
    b = np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


async def recall_test():
    # 4 个被拆分后的 chunks 内容（来自 final_chunks）
    chunks = [
        {
            "chunk_id": "759070e5122b8008",
            "content": "4 试剂与材料\n\n以下所用试剂，除特殊注明外均为分析纯试剂，水为符合 GB/T6682 规定的一级水。\n\n4.1 氯羟吡啶对照品：含量 ≥ 99%\n\n4.2 无水硫酸钠：使用前在马弗炉内 500°C 煅烧 5 h，冷却后，过 100 目筛，备用。"
        },
        {
            "chunk_id": "17f90f2bb967c612",
            "content": "4.3 碱性氧化铝：使用前在马弗炉内 300°C 煅烧 3 h，冷却后按每 100 g 加水 5 mL，混匀，干燥器中过夜，备用。\n\n4.4 N,O-双三甲基硅基三氟乙酰胺\n\n4.5 三甲基氯硅烷\n\n4.6 乙腈。\n\n4.7 甲苯：色谱纯。\n\n4.8 氦气：纯度 ≥ 99.999%\n\n4.9 衍生剂：取 N2O-双三甲基硅基三氟乙酰胺 99 mL，加三甲基氯硅烷 1 mL，混匀。"
        },
        {
            "chunk_id": "f7815cbbeab9705e",
            "content": "4.10 氧化铝层析柱：氧化铝柱用 30 mm × 15 mm 具塞玻璃层析柱，下配 G3 砂芯板，先装入适量的乙腈，然后装填 1 cm 高的无水硫酸钠，中间装 4 cm 高的碱性氧化铝，顶端再装 1 cm 高的硫酸钠，轻轻敲实填匀，备用。\n\n4.11 100 μg/mL 氯羟吡啶标准贮备液：精密称取氯羟吡啶对照品 10 mg，于 100 mL 量瓶中，用甲醇溶解并稀释至刻度，配制成浓度为 100 μg/mL 的氯羟吡啶标准贮备液。-20°C 以下保存，有效期 6 个月。"
        },
        {
            "chunk_id": "61a3939ca34cf162",
            "content": "4.12 1 μg/mL 氯羟吡啶标准工作液：精密量取 100 μg/mL 氯羟吡啶标准贮备液 1.0 mL，于 100 mL 容量瓶中，用甲醇稀释至刻度，配制成浓度为 1 μg/mL 的氯羟吡啶标准工作液，2 ~ 8°C 保存，有效期 1 周。"
        },
    ]

    # 合并后的理想 chunk（如果没被拆分）
    merged_content = "\n\n".join(c["content"] for c in chunks)

    # 测试 query
    queries = [
        "需要哪些试剂？",
        "试剂与材料有哪些？",
        "氯羟吡啶对照品的要求是什么？",
        "标准贮备液怎么配制？",
        "乙腈在哪里使用？",
    ]

    print("=" * 70)
    print("Embedding 模型召回测试")
    print("=" * 70)

    # 1. 先 embedding 所有 chunks
    chunk_texts = [c["content"] for c in chunks]
    chunk_vectors = await embed_batch(chunk_texts)

    # 2. 合并 chunk 的向量（简单平均）
    merged_vector = np.mean(chunk_vectors, axis=0).tolist()

    print(f"\nChunks 数量: {len(chunks)}")
    print(f"合并后内容长度: {len(merged_content)} 字符\n")

    for query in queries:
        print("-" * 70)
        print(f"Query: {query}")

        # Query embedding
        query_vector = (await embed_batch([query]))[0]

        # 逐个计算 similarity
        chunk_sims = []
        for i, (chunk, vec) in enumerate(zip(chunks, chunk_vectors)):
            sim = cosine_similarity(query_vector, vec)
            chunk_sims.append((sim, chunk["chunk_id"], chunk["content"][50:100]))
            print(f"  Chunk {i+1} ({chunk['chunk_id'][:8]}): sim={sim:.4f}")

        # 合并 chunk 的 similarity
        merged_sim = cosine_similarity(query_vector, merged_vector)
        print(f"  合并chunk: sim={merged_sim:.4f}")

        # 召回判断：sim > threshold 视为召回
        threshold = 0.5
        recalled = [c[1] for c in chunk_sims if c[0] > threshold]
        print(f"  召回 chunks ({threshold=}): {len(recalled)}/{len(chunks)} - {[r[:8] for r in recalled]}")

    print("\n" + "=" * 70)
    print("结论：如果每个 query 都能召回所有 4 个 chunks，说明 embedding 召回无虞")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(recall_test())
