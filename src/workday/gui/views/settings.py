"""设置视图"""
import customtkinter as ctk
from typing import Dict, Any


class SettingsView(ctk.CTkScrollableFrame):
    """设置视图"""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._widgets: Dict[str, Any] = {}
        self._monitor_options: list[str] = []
        self._build()
        self._load()

    def _build(self):
        ctk.CTkLabel(self, text="设置", font=("", 20, "bold")).pack(anchor="w", padx=16, pady=(16, 4))

        self._status_label = ctk.CTkLabel(self, text="", font=("", 12))
        self._status_label.pack(anchor="w", padx=16)

        self._build_llm_section()
        self._build_recording_section()
        self._add_section("分析设置", [
            ("analysis.interval", "分析间隔（分钟）", "int"),
            ("analysis.batch_duration", "批次时长（分钟）", "int"),
            ("analysis.debug_mode", "调试模式（跳过 LLM）", "bool"),
        ])
        self._add_section("数据保留", [
            ("retention.days", "保留天数", "int"),
        ])

        ctk.CTkFrame(self, height=1, fg_color=("gray80", "gray30")).pack(fill="x", padx=16, pady=8)
        ctk.CTkButton(self, text="保存设置", command=self._save, width=120).pack(anchor="w", padx=16, pady=(0, 8))

        ctk.CTkLabel(self, text="危险操作", font=("", 14, "bold"),
                     text_color=("#ef4444", "#f87171")).pack(anchor="w", padx=16, pady=(4, 4))
        ctk.CTkButton(self, text="清空所有数据", fg_color="#ef4444",
                      hover_color="#dc2626", command=self._clear_data,
                      width=120).pack(anchor="w", padx=16, pady=(0, 20))

    def _build_llm_section(self):
        frame = ctk.CTkFrame(self, corner_radius=8)
        frame.pack(fill="x", padx=16, pady=6)

        ctk.CTkLabel(frame, text="模型配置", font=("", 14, "bold")).pack(anchor="w", padx=12, pady=(10, 6))
        ctk.CTkFrame(frame, height=1, fg_color=("gray80", "gray30")).pack(fill="x", padx=12)

        # API Base
        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=4)
        ctk.CTkLabel(row, text="API Base URL", font=("", 12), width=180, anchor="w").pack(side="left")
        api_base_entry = ctk.CTkEntry(row, width=260, placeholder_text="https://api.openai.com/v1")
        api_base_entry.pack(side="left")
        self._widgets["llm.api_base"] = ("string", api_base_entry)

        # API Key
        row2 = ctk.CTkFrame(frame, fg_color="transparent")
        row2.pack(fill="x", padx=12, pady=4)
        ctk.CTkLabel(row2, text="API Key", font=("", 12), width=180, anchor="w").pack(side="left")
        api_key_entry = ctk.CTkEntry(row2, width=260, show="*")
        api_key_entry.pack(side="left")
        self._widgets["llm.api_key"] = ("password", api_key_entry)

        # Model（下拉 + 刷新）
        row3 = ctk.CTkFrame(frame, fg_color="transparent")
        row3.pack(fill="x", padx=12, pady=4)
        ctk.CTkLabel(row3, text="模型 ID", font=("", 12), width=180, anchor="w").pack(side="left")

        self._model_var = ctk.StringVar(value="")
        self._model_entry = ctk.CTkEntry(row3, width=200, textvariable=self._model_var,
                                          placeholder_text="手动输入或点击获取")
        self._model_entry.pack(side="left")
        ctk.CTkButton(row3, text="获取", width=52, height=28,
                      command=self._fetch_models).pack(side="left", padx=(8, 0))

        self._model_menu_frame = ctk.CTkFrame(frame, fg_color="transparent")
        self._model_menu_frame.pack(fill="x", padx=12, pady=(0, 4))
        self._model_menu = None

    def _fetch_models(self):
        api_base_entry = self._widgets["llm.api_base"][1]
        api_key_entry = self._widgets["llm.api_key"][1]
        api_base = api_base_entry.get().strip()
        api_key = api_key_entry.get().strip()

        if not api_base:
            self._status_label.configure(text="请先填写 API Base URL", text_color="orange")
            return

        self._status_label.configure(text="正在获取模型列表...", text_color=("gray50", "gray60"))
        self.update()

        try:
            from workday.services.llm_call import fetch_available_models
            models = fetch_available_models(api_base, api_key)
            if not models:
                self._status_label.configure(text="未获取到模型，请手动输入", text_color="orange")
                return

            self._status_label.configure(text=f"获取到 {len(models)} 个模型", text_color=("gray50", "gray60"))

            # 销毁旧下拉框，重建
            for w in self._model_menu_frame.winfo_children():
                w.destroy()

            current = self._model_var.get()
            if current not in models:
                self._model_var.set(models[0])

            ctk.CTkLabel(self._model_menu_frame, text="", width=180).pack(side="left")
            menu = ctk.CTkOptionMenu(self._model_menu_frame, variable=self._model_var,
                                     values=models, width=260)
            menu.pack(side="left")
            self._model_menu = menu
            self.after(3000, lambda: self._status_label.configure(text=""))
        except Exception as e:
            self._status_label.configure(text=f"获取失败: {e}", text_color="red")

    def _build_recording_section(self):
        frame = ctk.CTkFrame(self, corner_radius=8)
        frame.pack(fill="x", padx=16, pady=6)

        ctk.CTkLabel(frame, text="录制设置", font=("", 14, "bold")).pack(anchor="w", padx=12, pady=(10, 6))
        ctk.CTkFrame(frame, height=1, fg_color=("gray80", "gray30")).pack(fill="x", padx=12)

        # 显示器选择行
        mon_row = ctk.CTkFrame(frame, fg_color="transparent")
        mon_row.pack(fill="x", padx=12, pady=4)
        ctk.CTkLabel(mon_row, text="显示器", font=("", 12), width=180, anchor="w").pack(side="left")

        self._monitor_var = ctk.StringVar(value="加载中...")
        self._monitor_menu = ctk.CTkOptionMenu(mon_row, variable=self._monitor_var,
                                               values=["加载中..."], width=200)
        self._monitor_menu.pack(side="left")
        ctk.CTkButton(mon_row, text="刷新", width=52, height=28,
                      command=self._refresh_monitors).pack(side="left", padx=(8, 0))

        for key, label, field_type in [
            ("recording.capture_interval", "截图间隔（秒）", "int"),
            ("recording.chunk_duration", "片段时长（秒）", "int"),
            ("recording.quality", "图片质量 (1-100)", "int"),
            ("recording.output_dir", "输出目录", "string"),
        ]:
            row = ctk.CTkFrame(frame, fg_color="transparent")
            row.pack(fill="x", padx=12, pady=4)
            ctk.CTkLabel(row, text=label, font=("", 12), width=180, anchor="w").pack(side="left")
            entry = ctk.CTkEntry(row, width=260)
            entry.pack(side="left")
            self._widgets[key] = (field_type, entry)

        self._refresh_monitors()

    def _refresh_monitors(self):
        try:
            from workday.services.recorder import ScreenRecorder
            monitors = ScreenRecorder.list_monitors()
            self._monitor_options = [
                f"{m['index']} - {m.get('description', '')} ({m['width']}x{m['height']})"
                for m in monitors
            ]
            if not self._monitor_options:
                self._monitor_options = ["0 - 全部显示器"]
            self._monitor_menu.configure(values=self._monitor_options)
            current = self._monitor_var.get()
            if not any(current.startswith(opt.split(" ")[0]) for opt in self._monitor_options):
                self._monitor_var.set(self._monitor_options[0])
        except Exception:
            self._monitor_options = ["0 - 全部显示器"]
            self._monitor_menu.configure(values=self._monitor_options)

    def _get_monitor_index(self) -> str:
        return self._monitor_var.get().split(" ")[0]

    def _set_monitor_index(self, index: str):
        for opt in self._monitor_options:
            if opt.startswith(index + " "):
                self._monitor_var.set(opt)
                return
        if self._monitor_options:
            self._monitor_var.set(self._monitor_options[0])

    def _add_section(self, title: str, fields):
        frame = ctk.CTkFrame(self, corner_radius=8)
        frame.pack(fill="x", padx=16, pady=6)

        ctk.CTkLabel(frame, text=title, font=("", 14, "bold")).pack(anchor="w", padx=12, pady=(10, 6))
        ctk.CTkFrame(frame, height=1, fg_color=("gray80", "gray30")).pack(fill="x", padx=12)

        for key, label, field_type in fields:
            row = ctk.CTkFrame(frame, fg_color="transparent")
            row.pack(fill="x", padx=12, pady=4)
            ctk.CTkLabel(row, text=label, font=("", 12), width=180, anchor="w").pack(side="left")

            if field_type == "bool":
                var = ctk.BooleanVar()
                ctk.CTkSwitch(row, variable=var, text="").pack(side="left")
                self._widgets[key] = ("bool", var)
            else:
                entry = ctk.CTkEntry(row, width=260)
                entry.pack(side="left")
                self._widgets[key] = (field_type, entry)

    def _load(self):
        try:
            from workday.core.config import get_config
            cfg = get_config()

            # 显示器索引
            idx = cfg.get("recording.monitor_index", "0")
            self._set_monitor_index(str(idx))

            # 模型 ID
            self._model_var.set(cfg.get("llm.model", ""))

            for key, (field_type, widget) in self._widgets.items():
                if field_type == "bool":
                    widget.set(bool(cfg.get(key, False)))
                else:
                    raw = cfg.get_with_mask(key, mask=(field_type == "password"))
                    if raw is None:
                        raw = ""
                    widget.delete(0, "end")
                    widget.insert(0, str(raw))
        except Exception as e:
            self._status_label.configure(text=f"加载失败: {e}", text_color="red")

    def _save(self):
        try:
            from workday.core.config import get_config
            cfg = get_config()

            cfg.set("recording.monitor_index", self._get_monitor_index())

            model_val = self._model_var.get().strip()
            if model_val:
                cfg.set("llm.model", model_val)

            for key, (field_type, widget) in self._widgets.items():
                if field_type == "bool":
                    cfg.set(key, widget.get())
                else:
                    value = widget.get()
                    if value:
                        cfg.set(key, value)

            self._status_label.configure(text="已保存", text_color=("#10b981", "#34d399"))
            self.after(3000, lambda: self._status_label.configure(text=""))
        except Exception as e:
            self._status_label.configure(text=f"保存失败: {e}", text_color="red")

    def _clear_data(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("确认清空数据")
        dialog.geometry("320x140")
        dialog.grab_set()
        dialog.resizable(False, False)

        ctk.CTkLabel(dialog, text="确定要清空所有数据吗？\n此操作不可撤销！",
                     font=("", 13)).pack(pady=(20, 12))

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack()

        def confirm():
            try:
                from workday.core.config import get_config
                from workday.core.database import Database
                db = Database(get_config().database.path)
                db.clear_all_data(keep_videos=False)
                self._status_label.configure(text="数据已清空", text_color=("#10b981", "#34d399"))
            except Exception as e:
                self._status_label.configure(text=f"清空失败: {e}", text_color="red")
            dialog.destroy()

        ctk.CTkButton(btn_frame, text="取消", width=80,
                      command=dialog.destroy).pack(side="left", padx=8)
        ctk.CTkButton(btn_frame, text="清空", width=80,
                      fg_color="#ef4444", hover_color="#dc2626",
                      command=confirm).pack(side="left", padx=8)
