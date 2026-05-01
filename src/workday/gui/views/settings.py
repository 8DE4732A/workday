"""设置视图"""
import customtkinter as ctk
from typing import Dict, Any, Callable, Optional


class _Tooltip:
    """轻量 Tooltip：hover 或点击 ? 按钮时在旁边弹出说明气泡"""

    def __init__(self, widget: ctk.CTkButton, text: str):
        self._widget = widget
        self._text = text
        self._win: ctk.CTkToplevel | None = None
        widget.bind("<Enter>", self._show)
        widget.bind("<Leave>", self._hide)
        widget.configure(command=self._toggle)

    def _show(self, event=None):
        if self._win is not None:
            return
        x = self._widget.winfo_rootx() + self._widget.winfo_width() + 4
        y = self._widget.winfo_rooty()
        win = ctk.CTkToplevel(self._widget)
        win.wm_overrideredirect(True)
        win.wm_geometry(f"+{x}+{y}")
        win.lift()
        win.attributes("-topmost", True)
        ctk.CTkLabel(
            win,
            text=self._text,
            font=("", 12),
            wraplength=260,
            justify="left",
            corner_radius=6,
            fg_color=("gray90", "gray20"),
            padx=10,
            pady=8,
        ).pack()
        self._win = win

    def _hide(self, event=None):
        if self._win is not None:
            self._win.destroy()
            self._win = None

    def _toggle(self):
        if self._win is not None:
            self._hide()
        else:
            self._show()


class SettingsView(ctk.CTkScrollableFrame):
    """设置视图"""

    def __init__(self, parent, on_developer_toggle: Optional[Callable[[bool], None]] = None, **kwargs):
        super().__init__(parent, **kwargs)
        self._on_developer_toggle = on_developer_toggle
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
            ("analysis.interval", "分析间隔（分钟）", "int",
             "后台分析服务的轮询间隔。每隔此时长检查一次是否有新录制片段或待生成卡片。"),
            ("analysis.batch_duration", "批次时长（分钟）", "int",
             "将多个 15 秒录制片段合并为一个分析批次的时间窗口。窗口内的片段会拼接成一段视频后送入 Stage 1。"),
            "--- Stage 1：视频转录",
            ("analysis.card_window_minutes", "触发时间窗口（分钟）", "int",
             "Stage 2 触发条件之一：最早待处理的 Observation 距现在超过此时长，则立即生成活动卡片，无需等待数量条件。"),
            ("analysis.card_min_observations", "触发最少观察数", "int",
             "Stage 2 触发条件之一：待处理的 Observation 数量达到此值，则立即生成活动卡片，无需等待时间条件。两个条件满足任一即触发。"),
            "--- Stage 2：活动卡片生成",
            ("analysis.context_window_minutes", "前序卡片时间窗口（分钟）", "int",
             "生成活动卡片时，向模型提供的历史上下文范围。会查询当前批次开始时间往前此时长内已生成的活动卡片，帮助模型保持时间线连贯。"),
            ("analysis.context_max_cards", "前序卡片最大数量", "int",
             "历史上下文卡片的数量上限。与时间窗口取并集：时间窗口内的卡片和最近 N 张卡片都会被包含，避免长时间空闲后上下文为空。"),
            "---",
            ("analysis.debug_mode", "调试模式（跳过 LLM）", "bool",
             "开启后跳过所有 LLM 调用，直接生成占位内容。用于调试界面和数据流，不消耗 Token。"),
        ])
        self._add_section("数据保留", [
            ("retention.days", "保留天数", "int"),
        ])
        self._build_log_section()
        self._build_developer_section()

        ctk.CTkFrame(self, height=1, fg_color=("gray80", "gray30")).pack(fill="x", padx=16, pady=8)
        ctk.CTkButton(self, text="保存设置", command=self._save, width=120).pack(anchor="w", padx=16, pady=(0, 8))

        ctk.CTkLabel(self, text="危险操作", font=("", 14, "bold"),
                     text_color=("#ef4444", "#f87171")).pack(anchor="w", padx=16, pady=(4, 4))
        ctk.CTkButton(self, text="清空所有数据", fg_color="#ef4444",
                      hover_color="#dc2626", command=self._clear_data,
                      width=120).pack(anchor="w", padx=16, pady=(0, 20))

    def _build_developer_section(self):
        frame = ctk.CTkFrame(self, corner_radius=8)
        frame.pack(fill="x", padx=16, pady=6)

        ctk.CTkLabel(frame, text="开发者选项", font=("", 14, "bold")).pack(anchor="w", padx=12, pady=(10, 6))
        ctk.CTkFrame(frame, height=1, fg_color=("gray80", "gray30")).pack(fill="x", padx=12)

        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=8)
        ctk.CTkLabel(row, text="开发者模式", font=("", 12), width=180, anchor="w").pack(side="left")
        self._dev_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(row, variable=self._dev_var, text="").pack(side="left")

        btn = ctk.CTkButton(
            row, text="?", width=24, height=24,
            font=("", 11), fg_color="transparent",
            text_color=("gray50", "gray60"),
            hover_color=("gray85", "gray25"),
            border_width=1, border_color=("gray70", "gray40"),
            corner_radius=12,
        )
        btn.pack(side="left", padx=(6, 0))
        _Tooltip(btn, "开启后在侧边栏显示「开发者」选项卡，\n提供日志查看与数据库浏览功能。\n默认关闭，不影响普通使用。")

    def _build_log_section(self):
        frame = ctk.CTkFrame(self, corner_radius=8)
        frame.pack(fill="x", padx=16, pady=6)

        ctk.CTkLabel(frame, text="日志设置", font=("", 14, "bold")).pack(anchor="w", padx=12, pady=(10, 6))
        ctk.CTkFrame(frame, height=1, fg_color=("gray80", "gray30")).pack(fill="x", padx=12)

        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=4)
        ctk.CTkLabel(row, text="文件日志级别", font=("", 12), width=180, anchor="w").pack(side="left")

        self._log_level_var = ctk.StringVar(value="WARNING")
        levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
        menu = ctk.CTkOptionMenu(row, variable=self._log_level_var, values=levels, width=160)
        menu.pack(side="left")

        btn = ctk.CTkButton(
            row, text="?", width=24, height=24,
            font=("", 11), fg_color="transparent",
            text_color=("gray50", "gray60"),
            hover_color=("gray85", "gray25"),
            border_width=1, border_color=("gray70", "gray40"),
            corner_radius=12,
        )
        btn.pack(side="left", padx=(6, 0))
        _Tooltip(btn, "控制写入日志文件的详细程度。\n"
                      "WARNING（默认）：仅记录警告和错误，磁盘占用最小。\n"
                      "INFO：记录主要操作流程，适合排查问题。\n"
                      "DEBUG：记录所有细节含 LLM 内容，仅在调试时使用。\n"
                      "ERROR：仅记录错误，日志量最少。")

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
        api_base = api_base_entry.get().strip()

        if not api_base:
            self._status_label.configure(text="请先填写 API Base URL", text_color="orange")
            return

        # api_key 优先用输入框里的值（用户刚输入但未保存），
        # 若输入框内容是掩码则回退到 config 中存储的真实值
        from workday.core.config import get_config, Config
        raw_input = self._widgets["llm.api_key"][1].get().strip()
        if raw_input and not Config.is_masked(raw_input):
            api_key = raw_input
        else:
            api_key = get_config().get("llm.api_key", "")

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

        for field in fields:
            # 分割线：纯字符串，"--- 可选标签"
            if isinstance(field, str):
                label_text = field.lstrip("- ").strip()
                divider_row = ctk.CTkFrame(frame, fg_color="transparent")
                divider_row.pack(fill="x", padx=12, pady=(8, 2))
                ctk.CTkFrame(divider_row, height=1, fg_color=("gray75", "gray35")).pack(
                    side="left", fill="x", expand=True, pady=6
                )
                if label_text:
                    ctk.CTkLabel(
                        divider_row, text=f"  {label_text}  ",
                        font=("", 11), text_color=("gray50", "gray55"),
                    ).pack(side="left")
                    ctk.CTkFrame(divider_row, height=1, fg_color=("gray75", "gray35")).pack(
                        side="left", fill="x", expand=True, pady=6
                    )
                continue

            key, label, field_type = field[0], field[1], field[2]
            tip = field[3] if len(field) > 3 else None

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

            if tip:
                btn = ctk.CTkButton(
                    row, text="?", width=24, height=24,
                    font=("", 11), fg_color="transparent",
                    text_color=("gray50", "gray60"),
                    hover_color=("gray85", "gray25"),
                    border_width=1,
                    border_color=("gray70", "gray40"),
                    corner_radius=12,
                )
                btn.pack(side="left", padx=(6, 0))
                _Tooltip(btn, tip)

    def _load(self):
        try:
            from workday.core.config import get_config
            cfg = get_config()

            # 显示器索引
            idx = cfg.get("recording.monitor_index", "0")
            self._set_monitor_index(str(idx))

            # 模型 ID
            self._model_var.set(cfg.get("llm.model", ""))

            # 日志级别
            self._log_level_var.set(cfg.get("log.file_level", "WARNING"))

            # 开发者模式
            dev_mode = cfg.get("app.developer_mode", False)
            self._dev_var.set(bool(dev_mode))

            for key, (field_type, widget) in self._widgets.items():
                if field_type == "bool":
                    widget.set(bool(cfg.get(key, False)))
                else:
                    raw = cfg.get_with_mask(key, mask=(field_type == "password"))
                    if raw is None:
                        raw = ""
                    widget.delete(0, "end")
                    widget.insert(0, str(raw))

            # api_key 和 api_base 均已配置时，延迟自动获取模型列表
            if cfg.get("llm.api_key", "") and cfg.get("llm.api_base", ""):
                self.after(300, self._fetch_models)

        except Exception as e:
            self._status_label.configure(text=f"加载失败: {e}", text_color="red")

    def _save(self):
        try:
            from workday.core.config import get_config, Config
            cfg = get_config()

            cfg.set("recording.monitor_index", self._get_monitor_index())

            model_val = self._model_var.get().strip()
            if model_val:
                cfg.set("llm.model", model_val)

            # 日志级别：保存并立即生效
            log_level = self._log_level_var.get()
            cfg.set("log.file_level", log_level)
            from workday.core.logger import log_manager
            log_manager.set_file_log_level(log_level)

            # 开发者模式：先记录旧值再保存，若改变则回调通知
            old_dev = bool(cfg.get("app.developer_mode", False))
            new_dev = bool(self._dev_var.get())
            cfg.set("app.developer_mode", new_dev)
            if old_dev != new_dev and self._on_developer_toggle:
                self._on_developer_toggle(new_dev)

            for key, (field_type, widget) in self._widgets.items():
                if field_type == "bool":
                    cfg.set(key, widget.get())
                else:
                    value = widget.get()
                    if not value:
                        continue
                    if field_type == "password" and Config.is_masked(value):
                        continue
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
