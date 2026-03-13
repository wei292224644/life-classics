from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


RULES_DIR = Path(__file__).parent / "rules"


class RulesStore:
    """运行时动态加载的规则文件管理器。"""

    def __init__(self, rules_dir: str):
        self._dir = Path(rules_dir)
        self._ct_path = self._dir / "content_type_rules.json"
        self._dt_path = self._dir / "doc_type_rules.json"
        self._ct: Dict[str, Any] = {}
        self._dt: Dict[str, Any] = {}
        self._init_files()
        self.reload()

    def _init_files(self) -> None:
        """文件不存在时从默认规则复制创建。"""
        self._dir.mkdir(parents=True, exist_ok=True)
        for src_name, dst in [
            ("content_type_rules.json", self._ct_path),
            ("doc_type_rules.json", self._dt_path),
        ]:
            if not dst.exists():
                src = RULES_DIR / src_name
                dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")

    def reload(self) -> None:
        """从磁盘重新加载规则。"""
        self._ct = json.loads(self._ct_path.read_text(encoding="utf-8"))
        self._dt = json.loads(self._dt_path.read_text(encoding="utf-8"))

    def get_content_type_rules(self) -> Dict[str, Any]:
        return self._ct

    def get_doc_type_rules(self) -> Dict[str, Any]:
        return self._dt

    def get_confidence_threshold(self, config_override: float | None = None) -> float:
        if config_override is not None:
            return config_override
        return self._ct.get("confidence_threshold", 0.7)

    def get_transform_params(self, content_type_id: str) -> dict:
        for ct in self._ct.get("content_types", []):
            if ct["id"] == content_type_id:
                return ct.get("transform", {"strategy": "plain_embed"})
        return {"strategy": "plain_embed"}

    def append_content_type(self, new_entry: dict) -> None:
        """追加新 content_type，持久化后立即 reload。"""
        self._ct.setdefault("content_types", []).append(new_entry)
        self._ct_path.write_text(
            json.dumps(self._ct, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self.reload()

    def append_doc_type(self, new_entry: dict) -> None:
        """追加新 doc_type，持久化后立即 reload。"""
        self._dt.setdefault("doc_types", []).append(new_entry)
        self._dt_path.write_text(
            json.dumps(self._dt, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self.reload()

