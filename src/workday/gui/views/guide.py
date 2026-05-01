"""使用指南视图 - 从 docs/ 目录动态加载 Markdown 文档"""
import customtkinter as ctk
from pathlib import Path

from workday.utils.docs_loader import list_doc_files, load_doc


class GuideView(ctk.CTkFrame):
    """使用指南视图，左侧目录 + 右侧内容区"""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self._selected_btn: ctk.CTkButton | None = None
        self._build()

    def _build(self):
        doc_files = list_doc_files()

        # 左侧目录区
        sidebar = ctk.CTkScrollableFrame(self, width=180, fg_color=("gray95", "gray15"))
        sidebar.pack(side="left", fill="y", padx=(0, 4))

        ctk.CTkLabel(sidebar, text="目录", font=("", 13, "bold"),
                     anchor="w").pack(fill="x", padx=12, pady=(12, 4))

        # 右侧内容区
        self._content = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._content.pack(side="left", fill="both", expand=True)

        if not doc_files:
            self._show_placeholder()
            return

        # 为每个文档创建目录按钮
        self._btn_map: dict[Path, ctk.CTkButton] = {}
        for path in doc_files:
            title, _ = load_doc(path)
            btn = ctk.CTkButton(
                sidebar,
                text=title,
                anchor="w",
                font=("", 12),
                fg_color="transparent",
                text_color=("gray10", "gray90"),
                hover_color=("gray85", "gray25"),
                command=lambda p=path: self._show(p),
            )
            btn.pack(fill="x", padx=4, pady=1)
            self._btn_map[path] = btn

        # 自动显示第一个文档
        self._show(doc_files[0])

    def _show_placeholder(self):
        ctk.CTkLabel(
            self._content,
            text="未找到 docs/ 目录，请检查项目结构。",
            font=("", 13),
            text_color=("gray50", "gray60"),
            anchor="w",
        ).pack(fill="x", padx=20, pady=20)

    def _show(self, path: Path):
        # 更新目录按钮选中态
        if self._selected_btn is not None:
            self._selected_btn.configure(fg_color="transparent")
        btn = self._btn_map.get(path)
        if btn:
            btn.configure(fg_color=("gray80", "gray30"))
            self._selected_btn = btn

        # 清空内容区
        for widget in self._content.winfo_children():
            widget.destroy()

        _, blocks = load_doc(path)
        self._render_blocks(blocks)

        try:
            self._content._parent_canvas.yview_moveto(0)  # CTkScrollableFrame 内部 canvas
        except Exception:
            pass

    def _render_blocks(self, blocks: list[tuple[str, str]]):
        code_frame: ctk.CTkFrame | None = None

        for text, style in blocks:
            if style != "code":
                code_frame = None  # 非代码行时重置，使下个代码块新建框

            if style == "space":
                ctk.CTkFrame(self._content, height=8, fg_color="transparent").pack()

            elif style == "title":
                ctk.CTkLabel(self._content, text=text, font=("", 22, "bold"),
                             anchor="w").pack(fill="x", padx=20, pady=(20, 4))

            elif style == "heading":
                ctk.CTkLabel(self._content, text=text, font=("", 15, "bold"),
                             anchor="w").pack(fill="x", padx=20, pady=(8, 4))

            elif style == "subheading":
                ctk.CTkLabel(self._content, text=text, font=("", 13, "bold"),
                             anchor="w").pack(fill="x", padx=20, pady=(6, 2))

            elif style == "body":
                ctk.CTkLabel(self._content, text=text, font=("", 13),
                             anchor="w", justify="left",
                             wraplength=640).pack(fill="x", padx=20, pady=2)

            elif style == "bullet":
                row = ctk.CTkFrame(self._content, fg_color="transparent")
                row.pack(fill="x", padx=20, pady=1)
                ctk.CTkLabel(row, text=f"• {text}", font=("", 13),
                             anchor="w", wraplength=620).pack(side="left")

            elif style == "code":
                if code_frame is None:
                    code_frame = ctk.CTkFrame(self._content,
                                              fg_color=("gray90", "gray20"),
                                              corner_radius=4)
                    code_frame.pack(fill="x", padx=20, pady=(2, 4))
                if code_frame:
                    ctk.CTkLabel(code_frame, text=text, font=("Courier", 12),
                                 anchor="w").pack(fill="x", padx=12, pady=(2, 2))

        # 末尾留白
        ctk.CTkFrame(self._content, height=24, fg_color="transparent").pack()
