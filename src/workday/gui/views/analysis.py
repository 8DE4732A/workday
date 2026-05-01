"""分析视图 - 日/周工作情况分析 + HTML 报告导出"""
import json
import threading
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

import customtkinter as ctk

from workday.gui.widgets.calendar_picker import CalendarPicker, DateButton
from workday.utils import fmt_duration


CAT_COLORS = {
    "工作": "#3b82f6",
    "学习": "#10b981",
    "娱乐": "#f59e0b",
    "其他": "#6b7280",
}


def _date_to_week_key(d: date) -> str:
    iso = d.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def _week_key_label(week_key: str) -> str:
    year_str, week_str = week_key.split("-W")
    year, week = int(year_str), int(week_str)
    monday = date.fromisocalendar(year, week, 1)
    sunday = monday + timedelta(days=6)
    return f"{week_key} ({monday.strftime('%m-%d')}~{sunday.strftime('%m-%d')})"


class _WeekButton(ctk.CTkFrame):
    """带日历弹窗的周选择控件"""

    def __init__(self, parent, on_change=None, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self._on_change = on_change
        self._week_key = _date_to_week_key(date.today())
        self._picker: Optional[CalendarPicker] = None

        self._label = ctk.CTkEntry(self, width=160, placeholder_text="YYYY-Www",
                                   font=("", 12))
        self._label.pack(side="left")
        self._label.insert(0, _week_key_label(self._week_key))
        self._label.configure(state="readonly")

        ctk.CTkButton(self, text="📅", width=28, height=28,
                      font=("", 13), fg_color="transparent",
                      hover_color=("gray80", "gray30"),
                      command=self._open_picker).pack(side="left", padx=(2, 0))

    def _open_picker(self):
        if self._picker and self._picker.winfo_exists():
            self._picker._close()
            self._picker = None
            return
        year_str, week_str = self._week_key.split("-W")
        monday = date.fromisocalendar(int(year_str), int(week_str), 1)
        self._picker = CalendarPicker(
            self._label,
            on_select=self._on_date_selected,
            initial=monday.isoformat()
        )
        self._picker.focus_set()

    def _on_date_selected(self, date_str: str):
        d = date.fromisoformat(date_str)
        self._week_key = _date_to_week_key(d)
        self._label.configure(state="normal")
        self._label.delete(0, "end")
        self._label.insert(0, _week_key_label(self._week_key))
        self._label.configure(state="readonly")
        self._picker = None
        if self._on_change:
            self._on_change(self._week_key)

    def get(self) -> str:
        return self._week_key

    def set(self, week_key: str):
        self._week_key = week_key
        self._label.configure(state="normal")
        self._label.delete(0, "end")
        self._label.insert(0, _week_key_label(week_key))
        self._label.configure(state="readonly")


class AnalysisView(ctk.CTkFrame):
    """分析视图"""

    def __init__(self, parent, db, **kwargs):
        super().__init__(parent, **kwargs)
        self.db = db
        self._scope = "day"
        self._period_key = date.today().isoformat()
        self._report = None
        self._generating = False
        self._has_data_cache: Optional[bool] = None

        self._build()
        self._load_cached()

    def _build(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(16, 8))
        ctk.CTkLabel(header, text="工作分析", font=("", 20, "bold")).pack(side="left")

        ctrl = ctk.CTkFrame(self, fg_color="transparent")
        ctrl.pack(fill="x", padx=16, pady=(0, 12))

        self._scope_seg = ctk.CTkSegmentedButton(
            ctrl, values=["日", "周"], width=120,
            command=self._on_scope_change
        )
        self._scope_seg.set("日")
        self._scope_seg.pack(side="left", padx=(0, 12))

        self._day_btn = DateButton(ctrl, on_change=self._on_date_change,
                                   initial=date.today().isoformat())
        self._day_btn.pack(side="left")

        self._week_btn = _WeekButton(ctrl, on_change=self._on_date_change)
        self._week_btn.pack_forget()

        btn_frame = ctk.CTkFrame(ctrl, fg_color="transparent")
        btn_frame.pack(side="right")
        self._gen_btn = ctk.CTkButton(btn_frame, text="生成", width=72, height=30,
                                       command=self._on_generate)
        self._gen_btn.pack(side="left", padx=(0, 6))
        self._regen_btn = ctk.CTkButton(btn_frame, text="重新生成", width=88, height=30,
                                         command=self._on_regenerate)
        self._regen_btn.pack(side="left", padx=(0, 6))
        self._export_btn = ctk.CTkButton(btn_frame, text="导出 HTML", width=88, height=30,
                                          command=self._on_export)
        self._export_btn.pack(side="left")

        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._scroll.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        self._placeholder = ctk.CTkLabel(
            self._scroll, text="选择日期后点击「生成」生成工作分析报告",
            font=("", 13), text_color=("gray50", "gray60")
        )
        self._placeholder.pack(pady=60)

        self._kpi_frame = ctk.CTkFrame(self._scroll, fg_color="transparent")
        self._cat_frame = ctk.CTkFrame(self._scroll, fg_color="transparent")
        self._summary_frame = ctk.CTkFrame(self._scroll, fg_color="transparent")

        self._update_btn_states()

    # ─────────────────── 事件处理 ───────────────────

    def _on_scope_change(self, val: str):
        self._scope = "day" if val == "日" else "week"
        if self._scope == "day":
            self._week_btn.pack_forget()
            self._day_btn.pack(side="left", before=self._week_btn)
            self._period_key = self._day_btn.get() or date.today().isoformat()
        else:
            self._day_btn.pack_forget()
            self._week_btn.pack(side="left", after=self._scope_seg)
            self._period_key = self._week_btn.get()
        self._report = None
        self._has_data_cache = None
        self._load_cached()

    def _on_date_change(self, new_val: str):
        self._period_key = new_val
        self._report = None
        self._has_data_cache = None
        self._load_cached()

    def _on_generate(self):
        self._start_generate()

    def _on_regenerate(self):
        if self._report:
            self.db.delete_analysis_report(self._scope, self._period_key)
            self._report = None
        self._start_generate()

    def _on_export(self):
        if not self._report:
            return
        from tkinter import filedialog, messagebox
        path = filedialog.asksaveasfilename(
            title="导出 HTML 报告",
            defaultextension=".html",
            filetypes=[("HTML 文件", "*.html"), ("所有文件", "*.*")],
            initialfile=f"workday-report-{self._period_key}.html",
        )
        if not path:
            return
        try:
            from workday.services.analysis_report import export_html
            export_html(self._report, Path(path))
            messagebox.showinfo("导出成功", f"报告已保存至：\n{path}")
        except Exception as e:
            messagebox.showerror("导出失败", str(e))

    # ─────────────────── 数据加载 ───────────────────

    def _load_cached(self):
        if not self._period_key:
            return
        cached = self.db.get_analysis_report(self._scope, self._period_key)
        if cached:
            self._report = cached
            self._has_data_cache = True
            self._render_report(cached)
        else:
            self._clear_content()
            has_data = self._get_has_data()
            if not has_data:
                self._show_placeholder("该日期无活动数据")
            else:
                self._show_placeholder("选择日期后点击「生成」生成工作分析报告")
        self._update_btn_states()

    def _get_has_data(self) -> bool:
        if self._has_data_cache is not None:
            return self._has_data_cache
        try:
            count = self.db.count_timeline_cards_for_period(self._scope, self._period_key)
            self._has_data_cache = count > 0
        except Exception:
            self._has_data_cache = False
        return bool(self._has_data_cache)

    def _start_generate(self):
        if self._generating:
            return
        self._generating = True
        self._update_btn_states()
        self._gen_btn.configure(text="生成中...")

        def _run():
            try:
                from workday.services.analysis_report import generate_report
                report = generate_report(self.db, self._scope, self._period_key)
                self.after(0, lambda: self._on_report_done(report))
            except Exception as e:
                self.after(0, lambda: self._on_generate_error(str(e)))

        threading.Thread(target=_run, daemon=True).start()

    def _on_report_done(self, report):
        self._report = report
        self._generating = False
        self._gen_btn.configure(text="生成")
        self._render_report(report)
        self._update_btn_states()

    def _on_generate_error(self, msg: str):
        from tkinter import messagebox
        self._generating = False
        self._gen_btn.configure(text="生成")
        self._update_btn_states()
        messagebox.showerror("生成失败", f"生成分析报告时出错：\n{msg}")

    # ─────────────────── 渲染 ───────────────────

    def _show_placeholder(self, text: str):
        self._placeholder.configure(text=text)
        self._placeholder.pack(pady=60)

    def _clear_content(self):
        self._placeholder.pack_forget()
        self._kpi_frame.pack_forget()
        self._cat_frame.pack_forget()
        self._summary_frame.pack_forget()
        for frame in (self._kpi_frame, self._cat_frame, self._summary_frame):
            for w in frame.winfo_children():
                w.destroy()

    def _render_report(self, report):
        self._clear_content()
        stats = json.loads(report.stats_json)

        self._kpi_frame.pack(fill="x", pady=(0, 12))
        total_s = stats.get("total_active_seconds", 0)
        total_cards = stats.get("total_cards", 0)
        cat_breakdown = stats.get("category_breakdown", [])
        main_cat = max(cat_breakdown, key=lambda x: x["seconds"], default={"category": "—", "seconds": 0})
        total_nz = total_s or 1
        main_pct = round(main_cat["seconds"] / total_nz * 100)

        for title, val in [
            ("总活跃时长", fmt_duration(total_s)),
            ("活动卡片数", str(total_cards)),
            ("主要分类", main_cat["category"]),
            ("主要分类占比", f"{main_pct}%"),
        ]:
            card = ctk.CTkFrame(self._kpi_frame, corner_radius=8, fg_color=("gray90", "gray18"))
            card.pack(side="left", padx=(0, 10), ipadx=12, ipady=8)
            ctk.CTkLabel(card, text=title, font=("", 11),
                         text_color=("gray50", "gray55")).pack(anchor="w")
            ctk.CTkLabel(card, text=val, font=("", 20, "bold")).pack(anchor="w")

        self._cat_frame.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(self._cat_frame, text="分类分布", font=("", 13, "bold")).pack(anchor="w", pady=(0, 6))
        for c in cat_breakdown:
            if c["seconds"] == 0:
                continue
            pct = round(c["seconds"] / total_nz * 100)
            row = ctk.CTkFrame(self._cat_frame, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=c["category"], width=50, font=("", 12),
                         anchor="w").pack(side="left")
            bar_outer = ctk.CTkFrame(row, height=16, corner_radius=4,
                                      fg_color=("gray85", "gray25"))
            bar_outer.pack(side="left", fill="x", expand=True, padx=(6, 6))
            ctk.CTkFrame(bar_outer, height=16, corner_radius=4,
                          fg_color=CAT_COLORS.get(c["category"], "#6b7280")).place(
                              x=0, y=0, relwidth=pct / 100, relheight=1)
            ctk.CTkLabel(row, text=f"{fmt_duration(c['seconds'])} ({pct}%)",
                         font=("", 11), text_color=("gray50", "gray55"),
                         width=120, anchor="e").pack(side="left")

        self._summary_frame.pack(fill="x", pady=(0, 12))
        ctk.CTkLabel(self._summary_frame, text="AI 工作总结", font=("", 13, "bold")).pack(anchor="w", pady=(0, 6))
        textbox = ctk.CTkTextbox(self._summary_frame, height=280, wrap="word", font=("", 12))
        textbox.pack(fill="x")
        textbox.insert("1.0", report.summary)
        textbox.configure(state="disabled")

    def _update_btn_states(self):
        if self._generating:
            self._gen_btn.configure(state="disabled")
            self._regen_btn.configure(state="disabled")
            self._export_btn.configure(state="disabled")
            return

        has_report = self._report is not None
        has_data = has_report or self._get_has_data()

        self._gen_btn.configure(state="disabled" if (has_report or not has_data) else "normal")
        self._regen_btn.configure(state="normal" if has_report else "disabled")
        self._export_btn.configure(state="normal" if has_report else "disabled")
