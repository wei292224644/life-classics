"""
法规语义解析器（Regulatory Semantic Analyst）

职责：
- 从结构单元中识别规范性规则（Normative Rules）
- 将无法规则化的内容转换为解释型问答（QA）
- 过滤无语义价值的内容（Ignore）

核心原则：
- chunk的最小单位必须是"一条可独立判断真伪的规范性规则"
- 规则边界由大模型根据法规语义判断，而不是通过文本结构判断
"""

import json
import re
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, asdict
from langchain_core.messages import HumanMessage
from app.core.llm import get_llm
from app.core.config import settings


@dataclass
class StructuralUnit:
    """结构单元"""

    content: str  # 单元内容
    unit_type: str  # 单元类型：table_row, sentence/句子, paragraph/段落, note/注释
    page_num: Optional[int] = None  # 页码
    metadata: Optional[Dict[str, Any]] = None  # 额外元数据


@dataclass
class NormativeRule:
    """规范性规则"""

    document: str  # 完整的自然语言描述（使用法规语义表达）
    item: str  # 约束对象
    limit_type: str  # 约束类型：>=, <=, range, enum
    limit_value: Union[float, int, str, List]  # 数值或范围
    unit: str  # 单位（如 %、mg/kg）
    condition: str  # 适用条件（如"发酵法产品"）
    standard_ref: str  # 标准编号（如 GB 28310-2012）


@dataclass
class QA:
    """问答对"""

    question: str  # 问题
    answer: str  # 答案（稳定、可复用，不包含合规判断结论）
    standard_ref: str  # 标准编号


@dataclass
class AnalysisResult:
    """分析结果"""

    type: str  # "rule", "qa", "ignore"
    rules: Optional[List[NormativeRule]] = None
    qas: Optional[List[QA]] = None


class RegulatorySemanticAnalyzer:
    """法规语义解析器"""

    def __init__(self, standard_ref: Optional[str] = None):
        """
        初始化解析器

        Args:
            standard_ref: 标准编号（如 "GB 28310-2012"）
        """
        self.standard_ref = standard_ref or "未知标准"
        self.llm = get_llm()

    def analyze_unit(self, unit: StructuralUnit) -> AnalysisResult:
        """
        分析单个结构单元

        Args:
            unit: 结构单元

        Returns:
            AnalysisResult: 分析结果
        """
        prompt = self._build_analysis_prompt(unit)

        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])

            if hasattr(response, "content"):
                response_text = response.content
            elif isinstance(response, str):
                response_text = response
            else:
                response_text = str(response)

            # 解析大模型返回的结果
            result = self._parse_llm_response(response_text, unit)
            return result

        except Exception as e:
            print(f"解析结构单元失败 (类型: {unit.unit_type}): {e}")
            # 返回ignore结果
            return AnalysisResult(type="ignore")

    def _build_analysis_prompt(self, unit: StructuralUnit) -> str:
        """构建分析提示词"""
        prompt = f"""你是一名法规语义解析专家（Regulatory Semantic Analyst），
擅长从国家食品安全标准、行业标准中，识别可用于合规判断的规范性规则（Normative Rules），并将无法规则化的内容转换为解释型问答（QA）。

## 输入说明

你将收到一个"结构单元（Structural Unit）"，该单元可能来源于：
- 表格中的一行
- 章节中的一句或一段
- 注释（如"注：……"）

该结构单元不一定完整，也不一定是规则。

## 重要设计原则（必须遵守）

- 不要直接向量化 PDF 原文、OCR 文本或 Markdown 内容
- 不要使用传统 chunk 策略（按字数、段落、标题、父子 chunk）
- chunk 的最小单位必须是"一条可独立判断真伪的规范性规则（Normative Rule）"
- 规则的边界必须由大模型根据法规语义判断，而不是通过文本结构判断

## 你的任务（严格按顺序）

### Step 1：判断该结构单元的类型（必须）

你必须先判断该结构单元属于以下哪一类（只能选一类）：

- "rule"：可构成一条或多条规范性规则
- "qa"：不构成规则，但具有解释、定义或背景价值
- "ignore"：纯引用、纯指引、无语义价值（如"见表2""见附录A"）

### Step 2A：如果类型为 "rule"

你必须执行以下操作：

1️⃣ 规则边界判断

判断该结构单元包含：
- 0 条
- 1 条
- 多条

规范性规则

⚠️ 不得将多条规则合并为一条。

2️⃣ 规则重写（必须）

对每一条规则：
- 使用完整、明确的自然语言
- 使用法规语义表达：
  - "不得低于"
  - "不得超过"
  - "应当"
- 不得使用 ≥ ≤ 等符号
- 不得引用"见上文 / 表X"

3️⃣ 规则结构化抽取（必须）

对每条规则，提取以下字段：
- item：约束对象
- limit_type：约束类型（>=, <=, range, enum）
- limit_value：数值或范围
- unit：单位（如 %、mg/kg）
- condition：适用条件（如"发酵法产品"）
- standard_ref：标准编号（如 GB 28310-2012）

### Step 2B：如果类型为 "qa"

你必须执行以下操作：

1️⃣ 问题生成

提炼 1 个或多个明确问题
- 问题应符合真实用户可能提出的问题
- 不得是"本标准是什么"这类空泛问题

2️⃣ 答案生成

答案必须：
- 稳定
- 可复用
- 不包含合规判断结论
- 不包含阈值判定结果
- 答案用于解释规则，而不是替代规则

### Step 2C：如果类型为 "ignore"

输出空数组
不生成 Rule 或 QA

## 输出格式（严格遵守）

如果是 Rule:
{{
  "type": "rule",
  "rules": [
    {{
      "document": "Natural language description of the rule.",
      "item": "...",
      "limit_type": "...",
      "limit_value": ...,
      "unit": "...",
      "condition": "...",
      "standard_ref": "{self.standard_ref}"
    }}
  ]
}}

如果是 QA:
{{
  "type": "qa",
  "qas": [
    {{
      "question": "...",
      "answer": "...",
      "standard_ref": "{self.standard_ref}"
    }}
  ]
}}

如果是 Ignore:
{{
  "type": "ignore"
}}

## ⚠️ 严格约束（违反即错误）

❌ 不得同时输出 rule 和 qa
❌ 不得输出不完整规则
❌ 不得使用 Markdown
❌ 不得引用"本表""上文"
❌ 不得输出原文照抄

## 🧠 内部判断原则（必须遵守）

- 如果一句话 可以写成 if / else → Rule
- 如果一句话 只能解释 why / what → QA
- 如果一句话 既不能判断，也不能解释 → Ignore

## 结构单元信息

标准编号: {self.standard_ref}
结构单元类型: {unit.unit_type}
{f"注意：以下内容包含多个{unit.unit_type}单元合并后的内容，请分别分析每个单元。" if unit.metadata and unit.metadata.get("batch_size", 0) > 1 else ""}
结构单元内容:
{unit.content}

请严格按照上述要求进行分析，只返回JSON格式的结果，不要添加任何解释或说明。"""

        return prompt

    def _parse_llm_response(
        self, response_text: str, unit: StructuralUnit
    ) -> AnalysisResult:
        """解析大模型返回的结果"""
        # 尝试提取JSON
        json_match = re.search(
            r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", response_text, re.DOTALL
        )

        if not json_match:
            # 如果没有找到JSON，尝试查找type字段
            if '"type"' in response_text or "'type'" in response_text:
                # 尝试提取整个JSON对象
                json_match = re.search(r'\{.*"type".*\}', response_text, re.DOTALL)

        if json_match:
            try:
                json_str = json_match.group(0)
                # 清理可能的markdown代码块标记
                json_str = re.sub(r"```json\s*", "", json_str)
                json_str = re.sub(r"```\s*", "", json_str)
                json_str = json_str.strip()

                data = json.loads(json_str)
                result_type = data.get("type", "ignore")

                if result_type == "rule":
                    rules = []
                    rules_data = data.get("rules", [])
                    for rule_data in rules_data:
                        rule = NormativeRule(
                            document=rule_data.get("document", ""),
                            item=rule_data.get("item", ""),
                            limit_type=rule_data.get("limit_type", ""),
                            limit_value=rule_data.get("limit_value", ""),
                            unit=rule_data.get("unit", ""),
                            condition=rule_data.get("condition", ""),
                            standard_ref=rule_data.get(
                                "standard_ref", self.standard_ref
                            ),
                        )
                        # 验证规则完整性
                        if rule.document and rule.item:
                            rules.append(rule)

                    return AnalysisResult(type="rule", rules=rules)

                elif result_type == "qa":
                    qas = []
                    qas_data = data.get("qas", [])
                    for qa_data in qas_data:
                        qa = QA(
                            question=qa_data.get("question", ""),
                            answer=qa_data.get("answer", ""),
                            standard_ref=qa_data.get("standard_ref", self.standard_ref),
                        )
                        # 验证QA完整性
                        if qa.question and qa.answer:
                            qas.append(qa)

                    return AnalysisResult(type="qa", qas=qas)

                else:
                    return AnalysisResult(type="ignore")

            except json.JSONDecodeError as e:
                print(f"JSON解析失败: {e}")
                print(f"响应文本片段: {response_text[:500]}")
                return AnalysisResult(type="ignore")

        # 如果没有找到有效的JSON，返回ignore
        return AnalysisResult(type="ignore")

    def analyze_units(self, units: List[StructuralUnit]) -> Dict[str, Any]:
        """
        批量分析结构单元（优化版：按类型分组批量处理）

        Args:
            units: 结构单元列表

        Returns:
            包含所有分析结果的字典：
            {
                "rules": List[NormativeRule],
                "qas": List[QA],
                "ignored_count": int
            }
        """
        all_rules = []
        all_qas = []
        ignored_count = 0

        # 按unit_type分组
        units_by_type: Dict[str, List[StructuralUnit]] = {}
        for unit in units:
            unit_type = unit.unit_type
            if unit_type not in units_by_type:
                units_by_type[unit_type] = []
            units_by_type[unit_type].append(unit)

        print(f"\n结构单元分组统计: {[(k, len(v)) for k, v in units_by_type.items()]}")

        # 处理每种类型的单元
        for unit_type, type_units in units_by_type.items():
            print(f"\n处理 {unit_type} 类型单元（共 {len(type_units)} 个）...")

            if unit_type == "sentence" or unit_type == "note":
                # sentence和note：合并后批量处理
                result = self._analyze_sentences_batch(type_units)
            elif unit_type == "table_row":
                # table_row：批量处理表格行
                result = self._analyze_table_rows_batch(type_units)
            elif unit_type == "paragraph":
                # paragraph：TODO 后续处理
                print(f"  ⚠ paragraph类型暂未实现批量处理，逐个处理...")
                result = self._analyze_units_one_by_one(type_units)
            else:
                # 其他类型：逐个处理
                result = self._analyze_units_one_by_one(type_units)

            # 汇总结果
            if result["rules"]:
                all_rules.extend(result["rules"])
            if result["qas"]:
                all_qas.extend(result["qas"])
            ignored_count += result["ignored_count"]

        return {
            "rules": all_rules,
            "qas": all_qas,
            "ignored_count": ignored_count,
            "total_units": len(units),
        }

    def _analyze_sentences_batch(self, units: List[StructuralUnit]) -> Dict[str, Any]:
        """
        批量分析sentence和note类型的单元

        简单处理：将每个unit重新组织成一句符合逻辑的话，不需要rule/qa分类
        """
        if not units:
            return {"rules": [], "qas": [], "ignored_count": 0}

        print(f"  批量处理 {len(units)} 个{units[0].unit_type}单元（简化模式）...")

        # 构建批量处理的prompt
        prompt = self._build_sentence_rewrite_prompt(units)

        try:
            response = self.llm.invoke([HumanMessage(content=prompt)])

            if hasattr(response, "content"):
                response_text = response.content
            elif isinstance(response, str):
                response_text = response
            else:
                response_text = str(response)

            # 解析LLM返回的重写结果
            rewritten_sentences = self._parse_sentence_rewrite_response(
                response_text, len(units)
            )

            # 将重写后的句子转换为Document格式（作为QA存储）
            qas = []
            for i, rewritten in enumerate(rewritten_sentences):
                if rewritten and len(rewritten.strip()) > 5:  # 过滤空结果
                    original = units[i].content if i < len(units) else ""
                    # 创建QA对：问题可以是原句，答案是重写后的句子
                    qa = QA(
                        question=f"请解释：{original[:100]}",
                        answer=rewritten,
                        standard_ref=self.standard_ref,
                    )
                    qas.append(qa)

            return {
                "rules": [],
                "qas": qas,
                "ignored_count": len(units) - len(qas),  # 未成功重写的算作忽略
            }

        except Exception as e:
            print(f"  批量处理sentence/note失败: {e}")
            return {"rules": [], "qas": [], "ignored_count": len(units)}

    def _build_sentence_rewrite_prompt(self, units: List[StructuralUnit]) -> str:
        """构建sentence/note批量重写的prompt"""
        unit_type = units[0].unit_type if units else "sentence"
        unit_type_name = "句子" if unit_type == "sentence" else "注释"

        # 构建输入内容列表
        content_list = []
        for i, unit in enumerate(units, 1):
            content_list.append(f"{i}. {unit.content}")

        content_text = "\n".join(content_list)

        prompt = f"""你是一名文本整理专家。请将以下{unit_type_name}重新组织成符合逻辑、表达清晰的句子。

要求：
1. 保持原意不变
2. 使用规范的法规语言表达
3. 句子完整、通顺
4. 如果原句已经是规范表达，可以保持原样

输入{unit_type_name}列表：
{content_text}

请按照以下JSON格式返回结果，每个输入对应一个输出：
{{
  "sentences": [
    "重写后的第1个句子",
    "重写后的第2个句子",
    ...
  ]
}}

注意：
- 输出数组的长度必须与输入数量相同
- 如果某个输入无法重写或没有意义，输出空字符串""
- 只返回JSON，不要添加任何解释"""

        return prompt

    def _parse_sentence_rewrite_response(
        self, response_text: str, expected_count: int
    ) -> List[str]:
        """解析sentence重写的响应"""
        sentences = []

        # 尝试提取JSON
        json_match = re.search(
            r'\{[^{}]*"sentences"[^{}]*\[.*?\]\s*\}', response_text, re.DOTALL
        )

        if json_match:
            try:
                json_str = json_match.group(0)
                # 清理markdown代码块标记
                json_str = re.sub(r"```json\s*", "", json_str)
                json_str = re.sub(r"```\s*", "", json_str)
                json_str = json_str.strip()

                data = json.loads(json_str)
                sentences = data.get("sentences", [])

                # 确保数量匹配
                if len(sentences) < expected_count:
                    # 如果数量不足，用空字符串补齐
                    sentences.extend([""] * (expected_count - len(sentences)))
                elif len(sentences) > expected_count:
                    # 如果数量过多，截断
                    sentences = sentences[:expected_count]

            except json.JSONDecodeError as e:
                print(f"  解析sentence重写结果失败: {e}")
                sentences = [""] * expected_count
        else:
            # 如果没有找到JSON，尝试按行分割
            lines = [line.strip() for line in response_text.split("\n") if line.strip()]
            sentences = lines[:expected_count]
            if len(sentences) < expected_count:
                sentences.extend([""] * (expected_count - len(sentences)))

        return sentences

    def _analyze_table_rows_batch(self, units: List[StructuralUnit]) -> Dict[str, Any]:
        """
        批量分析table_row类型的单元

        表格行可以按表格分组，同一表格的行一起处理
        """
        if not units:
            return {"rules": [], "qas": [], "ignored_count": 0}

        all_rules = []
        all_qas = []
        ignored_count = 0

        # 按表格分组（通过metadata中的table_index）
        tables: Dict[int, List[StructuralUnit]] = {}
        for unit in units:
            table_idx = unit.metadata.get("table_index") if unit.metadata else None
            if table_idx is None:
                # 如果没有table_index，每个单元单独处理
                result = self.analyze_unit(unit)
                if result.rules:
                    all_rules.extend(result.rules)
                if result.qas:
                    all_qas.extend(result.qas)
                if result.type == "ignore":
                    ignored_count += 1
            else:
                if table_idx not in tables:
                    tables[table_idx] = []
                tables[table_idx].append(unit)

        # 批量处理每个表格
        for table_idx, table_rows in tables.items():
            if len(table_rows) == 1:
                # 单个行，直接处理
                result = self.analyze_unit(table_rows[0])
            else:
                # 多个行，合并处理
                print(f"  批量处理表格 {table_idx}（共 {len(table_rows)} 行）...")

                # 构建表格内容
                table_content = "\n".join([row.content for row in table_rows])

                # 获取表头（从第一行的metadata）
                header = (
                    table_rows[0].metadata.get("header", [])
                    if table_rows[0].metadata
                    else []
                )

                # 创建合并后的单元
                combined_unit = StructuralUnit(
                    content=table_content,
                    unit_type="table_row",
                    page_num=table_rows[0].page_num if table_rows else None,
                    metadata={
                        "table_index": table_idx,
                        "header": header,
                        "row_count": len(table_rows),
                        "batch_processing": True,
                    },
                )

                result = self.analyze_unit(combined_unit)

            if result.rules:
                all_rules.extend(result.rules)
            if result.qas:
                all_qas.extend(result.qas)
            if result.type == "ignore":
                ignored_count += 1

        return {"rules": all_rules, "qas": all_qas, "ignored_count": ignored_count}

    def _analyze_units_one_by_one(self, units: List[StructuralUnit]) -> Dict[str, Any]:
        """
        逐个分析单元（用于paragraph等暂未优化的类型）
        """
        all_rules = []
        all_qas = []
        ignored_count = 0

        for i, unit in enumerate(units, 1):
            print(f"  处理单元 {i}/{len(units)}: {unit.unit_type}")
            result = self.analyze_unit(unit)

            if result.rules:
                all_rules.extend(result.rules)
            if result.qas:
                all_qas.extend(result.qas)
            if result.type == "ignore":
                ignored_count += 1

        return {"rules": all_rules, "qas": all_qas, "ignored_count": ignored_count}

    def to_dict(self, result: AnalysisResult) -> Dict[str, Any]:
        """将分析结果转换为字典格式（用于JSON序列化）"""
        if result.type == "rule" and result.rules:
            return {
                "type": "rule",
                "rules": [
                    {
                        "document": rule.document,
                        "item": rule.item,
                        "limit_type": rule.limit_type,
                        "limit_value": rule.limit_value,
                        "unit": rule.unit,
                        "condition": rule.condition,
                        "standard_ref": rule.standard_ref,
                    }
                    for rule in result.rules
                ],
            }
        elif result.type == "qa" and result.qas:
            return {
                "type": "qa",
                "qas": [
                    {
                        "question": qa.question,
                        "answer": qa.answer,
                        "standard_ref": qa.standard_ref,
                    }
                    for qa in result.qas
                ],
            }
        else:
            return {"type": "ignore"}


# 全局解析器实例（需要在使用时指定standard_ref）
# regulatory_analyzer = RegulatorySemanticAnalyzer()
