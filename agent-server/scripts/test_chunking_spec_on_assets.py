#!/usr/bin/env python3
"""
对 docs/assets 下所有 .md 文件运行与 heading_strategy 等价的标题切分逻辑，
并依据 docs/plans/2026-03-02-chunking-strategy-spec.md 做符合性分析，输出到 cache/。
不依赖 app / langchain，仅用标准库。
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = ROOT / "docs" / "assets"
CACHE_DIR = ROOT / "cache"
REPORT_MD = CACHE_DIR / "chunking_spec_test_report.md"
DATA_JSON = CACHE_DIR / "chunking_spec_test_data.json"

HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$")

# 规范中的引用模式（本文件内）
REF_PATTERNS = [
    re.compile(r"同\s*[A-Z]?\s*[\d.]+\s*[.。]?"),
    re.compile(r"按\s*附录\s*[A-Z]?\s*中?\s*[A-Z]?\s*[\d.]+"),
    re.compile(r"按\s*[A-Z]?\s*[\d.]+"),
    re.compile(r"见\s*[A-Z]?\s*[\d.]+"),
]

TABLE_PATTERNS = [
    re.compile(r"^\s*\|.+\|", re.MULTILINE),
    re.compile(r"<table", re.IGNORECASE),
]


def split_heading_from_markdown_inline(markdown_content: str) -> list[dict]:
    """
    与 heading_strategy.split_heading_from_markdown 等价的纯逻辑：
    按 # 标题切分，返回 [{"section_path": [...], "content": "..."}, ...]。
    """
    chunks: list[dict] = []
    lines = markdown_content.splitlines()
    path_by_level: list[str] = []
    current_section_path: list[str] = []
    current_content_lines: list[str] = []
    i = 0

    def flush(content: str) -> None:
        if not content.strip():
            return
        chunks.append({
            "section_path": current_section_path.copy(),
            "content": content.strip(),
        })

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        match = HEADING_RE.match(stripped)
        if match:
            level = len(match.group(1))
            title = match.group(2).strip()
            if current_content_lines:
                flush("\n".join(current_content_lines))
                current_content_lines = []
            while len(path_by_level) > level:
                path_by_level.pop()
            if len(path_by_level) < level:
                path_by_level.extend([""] * (level - len(path_by_level)))
            path_by_level[level - 1] = title
            current_section_path = [t for t in path_by_level if t]
            current_content_lines = [line]
            i += 1
            continue
        current_content_lines.append(line)
        i += 1

    if current_content_lines:
        flush("\n".join(current_content_lines))

    return chunks


def _count_refs(text: str) -> list[str]:
    found = []
    for pat in REF_PATTERNS:
        for m in pat.finditer(text):
            found.append(m.group(0).strip())
    return list(dict.fromkeys(found))


def _has_table(text: str) -> bool:
    return any(p.search(text) for p in TABLE_PATTERNS)


def _infer_doc_type(filename: str, first_heading: str | None, section_paths: list[list[str]]) -> str:
    name_lower = (filename + " " + (first_heading or "")).lower()
    paths_str = " ".join(" ".join(p) for p in section_paths).lower()

    if "4789" in filename or "微生物" in filename or "沙门" in filename or "检验程序" in paths_str:
        return "microbiological"
    if any(x in filename for x in ["5009", "23200", "31604", "31659"]) or "测定" in filename or "检测" in filename or "第一法" in paths_str or "液相色谱" in paths_str:
        return "detection_method"
    if any(x in filename for x in ["1886", "8821", "29972"]) or "食品添加剂" in filename or ("附录 a" in paths_str and "鉴别" in paths_str):
        return "single_additive"
    if "31636" in filename or "花粉" in filename or "产品" in filename:
        return "product"
    return "other"


def analyze_file(md_path: Path) -> dict:
    content = md_path.read_text(encoding="utf-8", errors="replace")

    chunks = split_heading_from_markdown_inline(content)

    section_paths = [c["section_path"] for c in chunks]
    first_heading = section_paths[0][0] if chunks and section_paths[0] else None

    chunks_with_refs = []
    chunks_with_tables = []
    all_refs = []
    for i, c in enumerate(chunks):
        refs = _count_refs(c["content"])
        if refs:
            chunks_with_refs.append({"index": i, "section_path": c["section_path"], "refs": refs})
            all_refs.extend(refs)
        if _has_table(c["content"]):
            chunks_with_tables.append({"index": i, "section_path": c["section_path"]})

    inferred_type = _infer_doc_type(md_path.name, first_heading, section_paths)

    return {
        "file": md_path.name,
        "path": str(md_path),
        "size_bytes": len(content.encode("utf-8")),
        "size_chars": len(content),
        "chunk_count": len(chunks),
        "section_paths": section_paths,
        "first_heading": first_heading,
        "inferred_type": inferred_type,
        "chunks_with_cross_refs": chunks_with_refs,
        "chunks_with_tables": chunks_with_tables,
        "all_cross_ref_samples": list(dict.fromkeys(all_refs)),
        "content_type_used": "GENERAL_RULE",
    }


def main() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    md_files = sorted(ASSETS_DIR.glob("*.md"))
    if not md_files:
        print("No .md files in docs/assets")
        return

    results = []
    for p in md_files:
        try:
            results.append(analyze_file(p))
        except Exception as e:
            results.append({
                "file": p.name,
                "path": str(p),
                "error": str(e),
                "chunk_count": 0,
            })

    with open(DATA_JSON, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    lines = [
        "# 国标 Markdown 切分规范符合性测试报告",
        "",
        "> 对 `docs/assets` 下所有 .md 使用与 `split_heading_from_markdown` 等价的标题切分逻辑进行切分，并对照 `docs/plans/2026-03-02-chunking-strategy-spec.md` 做符合性分析。",
        "",
        "## 1. 概览",
        "",
        f"- **测试文件数**：{len(md_files)}",
        "- **切分逻辑**：与 `heading_strategy.split_heading_from_markdown` 一致（仅按 `#` 标题粗粒度，未做文档类型区分、引用展开、表按行切分）",
        "",
        "## 2. 各文件统计",
        "",
        "| 文件名 | 大小(字符) | Chunk 数 | 推断类型 | 含「同/按/见」引用的块数 | 含表格的块数 | 说明 |",
        "|--------|------------|----------|----------|--------------------------|--------------|------|",
    ]

    type_counts: dict[str, int] = {}
    for r in results:
        if "error" in r:
            lines.append(f"| {r['file']} | - | 0 | - | - | - | 错误: {r['error']} |")
            continue
        ref_cnt = len(r.get("chunks_with_cross_refs", []))
        table_cnt = len(r.get("chunks_with_tables", []))
        t = r.get("inferred_type", "other")
        type_counts[t] = type_counts.get(t, 0) + 1
        note = ""
        if ref_cnt:
            note = "含本文件内引用，规范要求展开"
        if t == "other":
            note = (note + " 未归类到规范三类").strip() or "-"
        lines.append(f"| {r['file']} | {r.get('size_chars', '-')} | {r.get('chunk_count', 0)} | {t} | {ref_cnt} | {table_cnt} | {note} |")

    lines.extend([
        "",
        "## 3. 推断文档类型分布",
        "",
        "| 类型 | 数量 | 对应规范节 |",
        "|------|------|------------|",
    ])
    for t, n in sorted(type_counts.items(), key=lambda x: -x[1]):
        spec = {"single_additive": "3.1", "detection_method": "3.2", "microbiological": "3.3", "product": "3.1", "other": "-"}.get(t, "-")
        lines.append(f"| {t} | {n} | {spec} |")
    lines.append("")

    lines.extend([
        "## 4. 规范符合性结论",
        "",
        "### 4.1 当前实现与规范的差距",
        "",
        "- **文档类型未区分**：所有文件均按同一套「标题层级」切分，未按 3.1～3.3 做「单添加剂 / 检测方法 / 微生物」差异化粒度（如表按行、方法整块、流程节点）。",
        "- **引用未展开**：含「同 A.x.x」「按 A.x」等句子的块未做引用展开，也未写入 `ref_section_code`。",
        "- **content_type 单一**：当前全部为 GENERAL_RULE，规范建议按块内容使用 SPECIFICATION_TABLE、TEST_METHOD、REAGENT 等。",
        "- **版本元数据未注入**：规范 6.2 要求的 standard_no / standard_year 等未在测试中注入（可由上游导入流程统一加）。",
        "",
        "### 4.2 规范适用性",
        "",
        "- **标题结构**：所有被测文件均含 `#` 标题，按标题切分能产出稳定 chunk 与 section_path，与规范第 5 节一致。",
        "- **引用与表格**：多数国标存在本文件内引用和表格；规范第 4、3.1～3.3 的「引用展开」与「表按行/整表」需在实现中补齐。",
        "- **非国标/非标准文档**：若 assets 中混入非国标（如「细菌回复突变试验」「硬脂酸钾」等），规范仍可适用为「按业务单元+引用展开」的通用原则，类型可标为 other 或后续扩展子类。",
        "",
        "## 5. 详细数据",
        "",
        f"完整 JSON 见：`{DATA_JSON.name}`",
        "",
    ])

    with open(REPORT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Report: {REPORT_MD}")
    print(f"Data:   {DATA_JSON}")


if __name__ == "__main__":
    main()
