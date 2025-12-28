"""
将文档列表转换为结构化文档列表
"""

from typing import Optional, List

from langchain_core.messages import HumanMessage, SystemMessage
from app.core.document_chunk import DocumentChunk
from app.core.llm import get_llm


def convert_to_structured(document: DocumentChunk) -> DocumentChunk:
    """
    将文档列表转换为结构化文档列表

    Args:
        document: 待转换的文档

    Returns:
        转换后的文档
    """
    text = analyze_with_llm(document.content)
    # 保存到缓存
    with open(f"./markdown_cache/{document.doc_id}.md", "w") as f:
        f.write(text)
    # 更新文档内容
    document.content = text
    # 更新文档元数据
    document.meta["markdown_cache"] = True
    return document


def analyze_with_llm(text: str) -> str:
    """
    使用LLM分析PDF文本

    Args:
        text: PDF文本内容

    Returns:
        LLM的分析结果
    """
    # 限制文本长度（避免超出token限制）
    max_length = 8000  # 可以根据模型调整
    if len(text) > max_length:
        print(f"\n⚠️  文本过长（{len(text)}字符），截取前{max_length}字符")
        text = text[:max_length] + "\n\n[文本已截断...]"

    # 构建prompt
    system_prompt = """你是一名资深的【文档解析与知识工程专家】，
擅长将标准类 PDF 文档转化为可直接用于知识库（RAG / Agent / 推理系统）的结构化文本。

你将收到一份 PDF 文档内容，请严格按照以下规则解析并输出结果。

====================
【一、核心目标】
====================
1. 完整提取 PDF 中出现的所有信息，不得遗漏正文、公式、表格、注释、脚注、说明、条件限制等内容。
2. 不追求版式复刻，但必须保证语义完整、逻辑清晰、结构稳定。
3. 输出结果必须“可直接切 chunk 入库”，无需人工二次清洗。

====================
【二、绝对禁止事项（高优先级）】
====================
1. 禁止对任何数值、单位、公式进行修改、推导、估算或重新计算。
2. 禁止合并、简化或省略变量定义、符号说明或注释内容。
3. 禁止引入 PDF 中未出现的背景知识、解释或结论。
4. 禁止使用“约”“大致”“通常”等模糊表述。

====================
【三、文档结构规范（强制）】
====================
1. 严格按以下层级组织内容：
   - 文档标题
   - 一级章节（##）
   - 二级章节（###）
   - 三级章节（####，如存在）
2. 每一个最小语义单元必须可作为一个独立 chunk 使用。
3. 不使用“如上所述”“见下表”等依赖版面的指代。

====================
【四、content_type 语义标注（必须使用）】
====================
每一个可切分的最小内容块，必须在标题下一行显式标注 content_type：

[content_type: <type>]

允许使用的 content_type 如下（只能从此列表中选择）：

- metadata                文档元信息（标准号、适用对象等）
- scope                   适用范围
- definition              概念 / 常数 / 术语定义
- chemical_formula        分子式
- chemical_structure      结构式说明
- molecular_weight        相对分子质量
- specification_table     技术指标 / 限量表格
- specification_text      技术要求（非表格）
- test_method             检验 / 测定方法
- instrument              仪器设备
- reagent                 试剂与材料
- calculation_formula     计算公式
- chromatographic_method  色谱 / 光谱类方法
- identification_test     鉴别试验
- general_rule            一般规定
- note                    注释 / 说明


====================
【五、数学公式处理规则】
====================
1. 所有公式必须使用 Markdown 数学公式格式（$$ ... $$）。
2. 公式后必须紧跟“变量解释区”，逐一列出：
   - 符号
   - 含义
   - 单位（如有）
3. 若公式中出现常数，必须说明其物理或化学含义及来源。
4. 若公式中出现公式（或计算式）的符号说明 / 参数定义（Symbol definitions / Where clause），必须用一个[__calculation_formula_note__]的标记替换类似“其中：”、“其中”、”注：”等字样。
5. 变量解释区不要被识别成其他的 content_type，应该添加[__calculation_formula_note__]标识。


====================
【六、表格处理规则】
====================
1. 表格必须作为一个完整的语义块，不得拆分为多段。
2. 使用标准 Markdown 表格格式。
3. 保留表头、单位、数值、注释、来源说明。
4. 表格下方如存在“注”“说明”“备注”，必须单独保留。
6. 如表格中出现“同上”“同下”“同前”等指代性内容：
   - 必须将其替换为所指向行的完整原文内容
   - 替换后不得保留“同上”等字样
示例：
原文：
| 项目 | 要求 | 检验方法 |  
| 色泽 | 无色 | 取适量样品置于清洁、干燥的白瓷盘中，在自然光线下，观察其色泽和状态，并嗅其味 |  
| 气味 | 无味 | 同上 |  

输出：
| 项目 | 要求 | 检验方法 |  
| 色泽 | 无色 | 取适量样品置于清洁、干燥的白瓷盘中，在自然光线下，观察其色泽和状态，并嗅其味 |  
| 气味 | 无味 | 取适量样品置于清洁、干燥的白瓷盘中，在自然光线下，观察其色泽和状态，并嗅其味 |  

====================
【七、 Metadata 处理规则】
====================
1. 采用无序列表格式。
2. 采用自然语言描述，不要使用表格格式。
3. 必须使用 [content_type: metadata] 标记。
示例：
[content_type: metadata]
- 本标准的标准号为 GB 28302—2012
- 本标准的中文名称为食品安全国家标准 食品添加剂 辛,癸酸甘油酯
- 本标准的发布日期为 2012-04-25
- 本标准的实施日期为 2012-06-25
- 本标准的发布机构为中华人民共和国卫生部


====================
【八、输出格式要求】
====================
1. 使用 Markdown 作为最终输出格式。
2. 仅输出解析后的结构化内容，不输出解析过程、思考说明或免责声明。
3. 不添加总结、评价或推论性内容。
"""

    human_prompt = f"""这是 PDF 文档的内容，请按照要求进行解析：{text}"""

    try:
        print("\n正在调用LLM分析...")
        llm = get_llm("dashscope")
        response = llm.invoke(
            [SystemMessage(content=system_prompt), HumanMessage(content=human_prompt)]
        )
        if hasattr(response, "content"):
            return response.content
        elif isinstance(response, str):
            return response
        else:
            return str(response)

    except Exception as e:
        print(f"LLM调用失败: {e}")
        import traceback

        traceback.print_exc()
        return f"错误: {str(e)}"
