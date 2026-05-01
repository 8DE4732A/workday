"""开发者视图 - 日志查看与数据库浏览"""
import sqlite3
import webbrowser
from pathlib import Path

import customtkinter as ctk

TABLES = [
    ("recording_chunks", "id"),
    ("batches", "id"),
    ("observations", "id"),
    ("timeline_cards", "id"),
    ("token_usage", "id"),
    ("config", "key"),
]
TABLE_NAMES = [t[0] for t in TABLES]
PAGE_SIZE = 50
LOG_TAIL_BYTES = 200 * 1024  # 200 KB


class DeveloperView(ctk.CTkFrame):
    """开发者视图：日志查看 + 数据库浏览"""

    def __init__(self, parent, db, **kwargs):
        super().__init__(parent, **kwargs)
        self.db = db
        self._log_files: list[Path] = []
        self._db_page = 0
        self._db_total = 0
        self._current_table = TABLE_NAMES[0]
        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="开发者工具", font=("", 20, "bold")).pack(
            anchor="w", padx=16, pady=(16, 4)
        )

        tabs = ctk.CTkTabview(self)
        tabs.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        tabs.add("日志")
        tabs.add("数据库")

        self._build_log_tab(tabs.tab("日志"))
        self._build_db_tab(tabs.tab("数据库"))

    # ──────────────────────────── 日志 tab ────────────────────────────

    def _build_log_tab(self, parent):
        top = ctk.CTkFrame(parent, fg_color="transparent")
        top.pack(fill="x", pady=(8, 4))

        ctk.CTkLabel(top, text="日志文件:", font=("", 12)).pack(side="left", padx=(0, 6))
        self._log_var = ctk.StringVar(value="")
        self._log_menu = ctk.CTkOptionMenu(
            top, variable=self._log_var, values=["（无日志文件）"],
            width=320, command=self._on_log_select
        )
        self._log_menu.pack(side="left")

        ctk.CTkButton(top, text="刷新", width=60, height=28,
                      command=self._refresh_log).pack(side="left", padx=(8, 0))
        ctk.CTkButton(top, text="复制路径", width=72, height=28,
                      command=self._copy_log_path).pack(side="left", padx=(6, 0))
        ctk.CTkButton(top, text="打开目录", width=72, height=28,
                      command=self._open_log_dir).pack(side="left", padx=(6, 0))

        self._log_size_label = ctk.CTkLabel(parent, text="", font=("", 11),
                                            text_color=("gray50", "gray55"))
        self._log_size_label.pack(anchor="w", padx=2, pady=(2, 4))

        self._log_box = ctk.CTkTextbox(
            parent, font=("Courier", 11), wrap="none", state="disabled"
        )
        self._log_box.pack(fill="both", expand=True)

        self._refresh_log_files()

    def _get_log_dir(self) -> Path:
        from workday.core.config import get_data_dir
        return get_data_dir() / "logs"

    def _refresh_log_files(self):
        log_dir = self._get_log_dir()
        if not log_dir.exists():
            self._log_files = []
            self._log_menu.configure(values=["（无日志文件）"])
            self._log_var.set("（无日志文件）")
            return

        files = sorted(log_dir.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
        self._log_files = files
        if not files:
            self._log_menu.configure(values=["（无日志文件）"])
            self._log_var.set("（无日志文件）")
            return

        names = [f.name for f in files]
        self._log_menu.configure(values=names)
        current = self._log_var.get()
        file_map = {f.name: f for f in files}
        if current not in file_map:
            self._log_var.set(names[0])
            self._load_log(files[0])
        else:
            self._load_log(file_map[current])

    def _on_log_select(self, name: str):
        for f in self._log_files:
            if f.name == name:
                self._load_log(f)
                return

    def _load_log(self, path: Path):
        try:
            size = path.stat().st_size
            with path.open("rb") as f:
                if size > LOG_TAIL_BYTES:
                    f.seek(-LOG_TAIL_BYTES, 2)
                    f.readline()  # 跳过可能的截断半行
                content = f.read().decode("utf-8", errors="replace")

            self._log_size_label.configure(
                text=f"文件大小: {size / 1024:.1f} KB  |  显示尾部 {min(size, LOG_TAIL_BYTES) / 1024:.0f} KB"
            )
            self._log_box.configure(state="normal")
            self._log_box.delete("1.0", "end")
            self._log_box.insert("end", content)
            self._log_box.see("end")
            self._log_box.configure(state="disabled")
        except Exception as e:
            self._log_box.configure(state="normal")
            self._log_box.delete("1.0", "end")
            self._log_box.insert("end", f"读取失败: {e}")
            self._log_box.configure(state="disabled")

    def _refresh_log(self):
        self._refresh_log_files()

    def _copy_log_path(self):
        name = self._log_var.get()
        for f in self._log_files:
            if f.name == name:
                self.clipboard_clear()
                self.clipboard_append(str(f))
                return

    def _open_log_dir(self):
        log_dir = self._get_log_dir()
        try:
            webbrowser.open(log_dir.as_uri())
        except Exception:
            pass

    # ──────────────────────────── 数据库 tab ────────────────────────────

    def _build_db_tab(self, parent):
        top = ctk.CTkFrame(parent, fg_color="transparent")
        top.pack(fill="x", pady=(8, 4))

        ctk.CTkLabel(top, text="数据表:", font=("", 12)).pack(side="left", padx=(0, 6))
        self._table_var = ctk.StringVar(value=TABLE_NAMES[0])
        ctk.CTkOptionMenu(
            top, variable=self._table_var, values=TABLE_NAMES,
            width=200, command=self._on_table_select
        ).pack(side="left")

        self._row_count_label = ctk.CTkLabel(top, text="", font=("", 11),
                                             text_color=("gray50", "gray55"))
        self._row_count_label.pack(side="left", padx=(12, 0))

        ctk.CTkButton(top, text="刷新", width=60, height=28,
                      command=self._refresh_table).pack(side="left", padx=(8, 0))

        # 分页控件
        page_bar = ctk.CTkFrame(parent, fg_color="transparent")
        page_bar.pack(fill="x", pady=(2, 4))

        ctk.CTkButton(page_bar, text="◀", width=32, height=26,
                      command=self._prev_page).pack(side="left")
        self._page_label = ctk.CTkLabel(page_bar, text="第 1/1 页", font=("", 11), width=90)
        self._page_label.pack(side="left", padx=4)
        ctk.CTkButton(page_bar, text="▶", width=32, height=26,
                      command=self._next_page).pack(side="left")

        # 表格区（可滚动）
        self._table_scroll = ctk.CTkScrollableFrame(parent, orientation="vertical")
        self._table_scroll.pack(fill="both", expand=True)

        self._load_table(TABLE_NAMES[0], page=0)

    def _on_table_select(self, name: str):
        self._current_table = name
        self._db_page = 0
        self._load_table(name, page=0)

    def _refresh_table(self):
        self._load_table(self._current_table, page=self._db_page)

    def _prev_page(self):
        if self._db_page > 0:
            self._db_page -= 1
            self._load_table(self._current_table, page=self._db_page)

    def _next_page(self):
        max_page = max(0, (self._db_total - 1) // PAGE_SIZE)
        if self._db_page < max_page:
            self._db_page += 1
            self._load_table(self._current_table, page=self._db_page)

    def _get_order_col(self, table: str) -> str:
        for t, col in TABLES:
            if t == table:
                return col
        return "rowid"

    def _query_table(self, table: str, order_col: str, limit: int, offset: int):
        db_path = self.db.db_path
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                f"SELECT * FROM {table} ORDER BY {order_col} DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
            total = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        return rows, total

    def _mask_sensitive(self, table: str, key: str, value: str) -> str:
        if table != "config":
            return value
        from workday.core.config import Config
        if key in Config.SENSITIVE_KEYS:
            return Config.mask_value(value)
        return value

    def _load_table(self, table: str, page: int):
        order_col = self._get_order_col(table)
        try:
            rows, total = self._query_table(table, order_col, PAGE_SIZE, page * PAGE_SIZE)
        except Exception as e:
            self._clear_table_frame()
            ctk.CTkLabel(self._table_scroll, text=f"查询失败: {e}",
                         text_color="red").pack(padx=8, pady=8)
            return

        self._db_total = total
        max_page = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        self._page_label.configure(text=f"第 {page + 1}/{max_page} 页")
        self._row_count_label.configure(text=f"共 {total} 条")

        self._clear_table_frame()
        if not rows:
            ctk.CTkLabel(self._table_scroll, text="（暂无数据）",
                         font=("", 12), text_color=("gray50", "gray55")).pack(pady=20)
            return

        cols = rows[0].keys()
        col_widths = self._estimate_col_widths(cols, rows)

        # 表头行
        header = ctk.CTkFrame(self._table_scroll, fg_color=("gray80", "gray25"))
        header.pack(fill="x", pady=(0, 1))
        for col, w in zip(cols, col_widths):
            ctk.CTkLabel(
                header, text=col, font=("Courier", 11, "bold"),
                width=w, anchor="w"
            ).pack(side="left", padx=4, pady=3)

        # 数据行
        for i, row in enumerate(rows):
            bg = ("gray92", "gray18") if i % 2 == 0 else ("gray96", "gray15")
            row_frame = ctk.CTkFrame(self._table_scroll, fg_color=bg)
            row_frame.pack(fill="x", pady=0)
            for col, w in zip(cols, col_widths):
                raw = row[col]
                if raw is None:
                    text = "NULL"
                else:
                    text = str(raw)
                    text = self._mask_sensitive(table, col, text)
                    if len(text) > 80:
                        text = text[:77] + "..."
                ctk.CTkLabel(
                    row_frame, text=text, font=("Courier", 11),
                    width=w, anchor="w"
                ).pack(side="left", padx=4, pady=2)

    def _estimate_col_widths(self, cols, rows) -> list[int]:
        widths = []
        for col in cols:
            max_len = len(str(col))
            for row in rows:
                v = row[col]
                max_len = max(max_len, min(len(str(v)) if v is not None else 4, 80))
            widths.append(max(60, min(max_len * 7 + 16, 300)))
        return widths

    def _clear_table_frame(self):
        for w in self._table_scroll.winfo_children():
            w.destroy()
