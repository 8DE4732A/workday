"""文档目录扫描与加载"""
from pathlib import Path

from workday.utils.markdown_parser import parse_markdown


def get_docs_dir() -> Path | None:
    """返回 docs/ 目录路径；找不到返回 None。

    优先查找开发时的项目根目录，其次查找 wheel 安装后的包内目录。
    """
    # 开发时：__file__ = .../src/workday/utils/docs_loader.py，parents[3] 为项目根
    dev_path = Path(__file__).resolve().parents[3] / "docs"
    if dev_path.is_dir():
        return dev_path
    # 安装后：docs/ 被复制到 site-packages/workday/docs/
    pkg_path = Path(__file__).resolve().parents[1] / "docs"
    if pkg_path.is_dir():
        return pkg_path
    return None


def list_doc_files() -> list[Path]:
    """返回按文件名排序的所有 .md 文件"""
    docs_dir = get_docs_dir()
    if docs_dir is None:
        return []
    return sorted(docs_dir.glob("*.md"))


def load_doc(path: Path) -> tuple[str, list[tuple[str, str]]]:
    """加载单个文档，返回 (title, blocks)。

    title 优先级：frontmatter title > 首个 # 标题 > 文件名 slug
    """
    text = path.read_text(encoding="utf-8")
    frontmatter, blocks = parse_markdown(text)

    # 从 frontmatter 取 title
    if "title" in frontmatter:
        title = frontmatter["title"]
    else:
        # 从 blocks 中找第一个 title 类型
        title = next((t for t, s in blocks if s == "title"), None)
        if title is None:
            # 文件名去掉数字前缀和连字符
            stem = path.stem
            parts = stem.split("-", 1)
            title = parts[1] if len(parts) == 2 else stem

    return title, blocks
