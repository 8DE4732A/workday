"""关于视图"""
import customtkinter as ctk
from pathlib import Path


def _fmt_size(size_bytes: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def _dir_size(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file():
        return path.stat().st_size
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


class AboutView(ctk.CTkScrollableFrame):
    """关于视图"""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._build()
        self._refresh()

    def _build(self):
        ctk.CTkLabel(self, text="关于", font=("", 20, "bold")).pack(anchor="w", padx=20, pady=(20, 4))
        ctk.CTkLabel(self, text="Workday — AI 驱动的工作时间追踪工具",
                     font=("", 13), text_color=("gray40", "gray70")).pack(anchor="w", padx=20, pady=(0, 16))

        # 版本
        from workday import __version__
        self._add_row("版本", f"v{__version__}")

        ctk.CTkFrame(self, height=1, fg_color=("gray80", "gray30")).pack(fill="x", padx=20, pady=12)
        ctk.CTkLabel(self, text="数据存储", font=("", 14, "bold")).pack(anchor="w", padx=20, pady=(0, 8))

        # 数据目录路径
        from workday.core.config import get_data_dir
        self._data_dir = get_data_dir()
        self._add_row("数据目录", str(self._data_dir), copyable=True)

        # 各项大小（先占位，_refresh 填充）
        self._db_size_label = self._add_row("workday.db", "计算中...")
        self._rec_size_label = self._add_row("recordings/", "计算中...")
        self._log_size_label = self._add_row("logs/", "计算中...")
        self._total_size_label = self._add_row("合计", "计算中...", bold=True)

        refresh_btn = ctk.CTkButton(self, text="刷新", width=80, height=28,
                                    command=self._refresh)
        refresh_btn.pack(anchor="w", padx=20, pady=(8, 0))

        ctk.CTkFrame(self, height=1, fg_color=("gray80", "gray30")).pack(fill="x", padx=20, pady=12)
        ctk.CTkLabel(self, text="开源地址", font=("", 14, "bold")).pack(anchor="w", padx=20, pady=(0, 4))
        ctk.CTkLabel(self, text="https://github.com/liuping/workday",
                     font=("", 12), text_color=("gray50", "gray60")).pack(anchor="w", padx=20)

        ctk.CTkFrame(self, height=24, fg_color="transparent").pack()

    def _add_row(self, label: str, value: str, copyable: bool = False, bold: bool = False) -> ctk.CTkLabel:
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=3)
        ctk.CTkLabel(row, text=label, font=("", 12), width=120,
                     text_color=("gray50", "gray60"), anchor="w").pack(side="left")
        font = ("", 12, "bold") if bold else ("", 12)
        val_label = ctk.CTkLabel(row, text=value, font=font, anchor="w")
        val_label.pack(side="left", fill="x", expand=True)
        if copyable:
            def copy(v=value):
                self.clipboard_clear()
                self.clipboard_append(v)
            ctk.CTkButton(row, text="复制", width=48, height=24,
                          command=copy).pack(side="right")
        return val_label

    def _refresh(self):
        db_path = self._data_dir / "workday.db"
        rec_path = self._data_dir / "recordings"
        log_path = self._data_dir / "logs"

        db_size = _dir_size(db_path)
        rec_size = _dir_size(rec_path)
        log_size = _dir_size(log_path)
        total = db_size + rec_size + log_size

        self._db_size_label.configure(text=_fmt_size(db_size))
        self._rec_size_label.configure(text=_fmt_size(rec_size))
        self._log_size_label.configure(text=_fmt_size(log_size))
        self._total_size_label.configure(text=_fmt_size(total))
