"""极简 Markdown 解析器，无三方依赖"""


def parse_markdown(text: str) -> tuple[dict, list[tuple[str, str]]]:
    """返回 (frontmatter_dict, blocks)。

    Block 类型：title / heading / subheading / body / bullet / code / space
    """
    lines = text.splitlines()
    frontmatter: dict = {}
    blocks: list[tuple[str, str]] = []

    i = 0
    # 解析可选 YAML frontmatter
    if lines and lines[0].strip() == "---":
        i = 1
        fm_lines = []
        while i < len(lines) and lines[i].strip() != "---":
            fm_lines.append(lines[i])
            i += 1
        i += 1  # 跳过结尾 ---
        for line in fm_lines:
            if ":" in line:
                k, _, v = line.partition(":")
                frontmatter[k.strip()] = v.strip()

    in_code = False
    pending_body: list[str] = []

    def flush_body():
        if pending_body:
            blocks.append((" ".join(pending_body), "body"))
            pending_body.clear()

    while i < len(lines):
        line = lines[i]
        i += 1

        if line.strip().startswith("```"):
            flush_body()
            in_code = not in_code
            if not in_code:
                blocks.append(("", "code_end"))
            continue

        if in_code:
            blocks.append((line, "code"))
            continue

        stripped = line.strip()

        if not stripped:
            flush_body()
            blocks.append(("", "space"))
            continue

        if stripped.startswith("### "):
            flush_body()
            blocks.append((stripped[4:], "subheading"))
        elif stripped.startswith("## "):
            flush_body()
            blocks.append((stripped[3:], "heading"))
        elif stripped.startswith("# "):
            flush_body()
            blocks.append((stripped[2:], "title"))
        elif stripped.startswith("- ") or stripped.startswith("* "):
            flush_body()
            blocks.append((stripped[2:], "bullet"))
        elif len(stripped) > 2 and stripped[0].isdigit() and stripped[1] in ".)" and stripped[2] == " ":
            flush_body()
            blocks.append((stripped[3:], "bullet"))
        elif len(stripped) > 3 and stripped[:2].isdigit() and stripped[2] in ".)" and stripped[3] == " ":
            flush_body()
            blocks.append((stripped[4:], "bullet"))
        else:
            pending_body.append(stripped)

    flush_body()

    # 移除 code_end 标记（仅作为占位符使用）
    blocks = [(t, s) for t, s in blocks if s != "code_end"]

    return frontmatter, blocks
