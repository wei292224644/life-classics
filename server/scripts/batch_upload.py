"""
批量上传 MD 文件到知识库。

使用方式：
    cd server
    uv run python3 scripts/batch_upload.py

跳过已上传的文件（通过 title 字段去重）。
失败文件不影响其他文件的上传。
"""

from __future__ import annotations

import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

# ── 配置 ──────────────────────────────────────────────────────────────────────
SOURCE_DIR = Path("/Users/wwj/Desktop/myself/download_test/reorganized")
API_BASE = "http://localhost:9999"
CONCURRENCY = 2
TIMEOUT_PER_FILE = 12000  # 秒
DELAY_BETWEEN_FILES = 60 * 30  # 秒，每个文件完成后等待
DELAY_BEFORE_START = 0 # 秒，启动前等待

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── 工具函数 ──────────────────────────────────────────────────────────────────


def get_uploaded_titles() -> set[str]:
    """从服务器获取已上传文档的 title 集合。"""
    try:
        resp = requests.get(f"{API_BASE}/api/documents", timeout=10)
        resp.raise_for_status()
        docs = resp.json().get("documents", [])
        # 过滤 title 为空的文档（历史数据），这类文档若重复上传视为新文档处理
        return {d["title"] for d in docs if d.get("title")}
    except requests.RequestException as e:
        logger.error("无法获取已上传文档列表：%s", e)
        raise SystemExit(1)


def clean_title(path: Path) -> str:
    """
    从文件路径提取 clean title：
      GB xxx.reorganized.md → GB xxx
      GB xxx.md             → GB xxx
    """
    stem = path.stem  # 去掉 .md
    if stem.endswith(".reorganized"):
        stem = stem[: -len(".reorganized")]
    return stem


def upload_file(path: Path) -> tuple[str, str | None]:
    """
    上传单个文件。返回 (clean_title, error_message)。
    error_message 为 None 表示成功。
    """
    title = clean_title(path)
    upload_filename = title + ".md"

    try:
        with open(path, "rb") as f:
            file_content = f.read()

        with requests.post(
            f"{API_BASE}/api/documents",
            files={"file": (upload_filename, file_content, "text/markdown")},
            stream=True,
            timeout=TIMEOUT_PER_FILE,
        ) as resp:
            resp.raise_for_status()
            for raw_line in resp.iter_lines():
                if not raw_line:
                    continue
                line = (
                    raw_line.decode("utf-8")
                    if isinstance(raw_line, bytes)
                    else raw_line
                )
                if not line.startswith("data:"):
                    continue
                payload = line[len("data:") :].strip()
                try:
                    event = json.loads(payload)
                except json.JSONDecodeError:
                    continue
                if event.get("type") == "done":
                    return title, None
                if event.get("type") == "error":
                    return title, event.get("message", "未知错误")
            # SSE 流结束但未收到 done/error
            return title, "SSE 流意外结束"

    except requests.Timeout:
        return title, f"超时（>{TIMEOUT_PER_FILE}s）"
    except Exception as e:
        return title, str(e)


# ── 主逻辑 ────────────────────────────────────────────────────────────────────


def main() -> None:
    logger.info("启动前等待 %ds ...", DELAY_BEFORE_START)
    time.sleep(DELAY_BEFORE_START)

    uploaded_titles = get_uploaded_titles()

    all_files = sorted(SOURCE_DIR.glob("*.md"))
    to_upload = [f for f in all_files if clean_title(f) not in uploaded_titles]
    skipped = len(all_files) - len(to_upload)

    if not to_upload:
        logger.info("全部文件已上传，跳过 %d 个。", skipped)
        return

    logger.info(
        "共 %d 个文件，跳过 %d 个，待上传 %d 个",
        len(all_files),
        skipped,
        len(to_upload),
    )

    successes: list[str] = []
    failures: list[tuple[str, str]] = []

    with ThreadPoolExecutor(max_workers=CONCURRENCY) as executor:
        futures = {executor.submit(upload_file, f): f for f in to_upload}
        for i, future in enumerate(as_completed(futures)):
            title, error = future.result()
            if error is None:
                successes.append(title)
                logger.info("✓ %s", title)
            else:
                failures.append((title, error))
                logger.warning("✗ %s：%s", title, error)
            if i < len(to_upload) - 1:
                logger.info("等待 %ds ...", DELAY_BETWEEN_FILES)
                time.sleep(DELAY_BETWEEN_FILES)

    logger.info("── 汇总 ──────────────────────────────────────────")
    logger.info("✓ 成功 %d 个", len(successes))
    if failures:
        logger.warning("✗ 失败 %d 个：", len(failures))
        for title, error in failures:
            logger.warning("    - %s.md：%s", title, error)
    logger.info("→ 跳过（已上传）%d 个", skipped)


if __name__ == "__main__":
    main()
