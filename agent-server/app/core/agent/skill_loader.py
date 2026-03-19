"""
SkillLoader：从目录读取 Markdown 技能文件并按文件名排序拼接为 system prompt。
"""
import os

DEFAULT_SKILLS_DIR = "app/skills/food-safety"


def load_skills(skills_dir: str = DEFAULT_SKILLS_DIR) -> str:
    """
    读取目录下所有 .md 文件，按文件名排序后拼接返回。

    Args:
        skills_dir: 技能文件目录路径

    Returns:
        所有技能文件内容按顺序拼接的字符串，文件间以两个换行分隔
    """
    if not os.path.isdir(skills_dir):
        return ""

    md_files = sorted(
        f for f in os.listdir(skills_dir) if f.endswith(".md")
    )

    parts = []
    for filename in md_files:
        filepath = os.path.join(skills_dir, filename)
        with open(filepath, encoding="utf-8") as f:
            parts.append(f.read())

    return "\n\n".join(parts)