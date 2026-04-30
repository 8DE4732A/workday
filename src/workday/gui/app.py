"""主应用窗口"""
import customtkinter as ctk
from typing import Optional


class WorkdayApp(ctk.CTk):
    """Workday 主窗口"""

    NAV_ITEMS = [
        ("timeline", "时间线", "📋"),
        ("dashboard", "仪表盘", "📊"),
        ("settings", "设置", "⚙️"),
        ("guide", "指南", "📖"),
        ("about", "关于", "ℹ️"),
    ]

    def __init__(self):
        super().__init__()

        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        self.title("Workday")
        self.geometry("1280x800")
        self.minsize(900, 600)

        # 初始化共享数据库
        from workday.core.config import get_config
        from workday.core.database import Database
        cfg = get_config()
        self.db = Database(cfg.database.path)

        # 启动后台分析服务
        from workday.services.analysis import AnalysisManager
        self._analysis_mgr = AnalysisManager(self.db)
        self._analysis_mgr.start()

        self._views = {}
        self._current_view: Optional[str] = None
        self._nav_buttons = {}

        self._build()
        self._show_view("timeline")

    def _build(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 左侧边栏
        self._sidebar = ctk.CTkFrame(self, width=190, corner_radius=0)
        self._sidebar.grid(row=0, column=0, sticky="nsew")
        self._sidebar.grid_propagate(False)
        self._build_sidebar()

        # 右内容区
        self._content = ctk.CTkFrame(self, fg_color=("gray95", "gray10"), corner_radius=0)
        self._content.grid(row=0, column=1, sticky="nsew")

    def _build_sidebar(self):
        # 应用标题
        title_frame = ctk.CTkFrame(self._sidebar, fg_color="transparent")
        title_frame.pack(fill="x", padx=12, pady=(20, 16))
        ctk.CTkLabel(title_frame, text="⏱ Workday", font=("", 18, "bold")).pack(anchor="w")
        ctk.CTkLabel(title_frame, text="AI 工作时间追踪", font=("", 11),
                     text_color=("gray50", "gray60")).pack(anchor="w")

        ctk.CTkFrame(self._sidebar, height=1, fg_color=("gray80", "gray30")).pack(fill="x", padx=12, pady=(0, 8))

        # 导航按钮
        for view_id, label, icon in self.NAV_ITEMS:
            btn = ctk.CTkButton(
                self._sidebar,
                text=f"  {icon}  {label}",
                anchor="w",
                height=40,
                corner_radius=6,
                fg_color="transparent",
                hover_color=("gray80", "gray25"),
                text_color=("gray20", "gray90"),
                command=lambda vid=view_id: self._show_view(vid)
            )
            btn.pack(fill="x", padx=8, pady=2)
            self._nav_buttons[view_id] = btn

        # 底部录制控制
        spacer = ctk.CTkFrame(self._sidebar, fg_color="transparent")
        spacer.pack(fill="both", expand=True)

        ctk.CTkFrame(self._sidebar, height=1, fg_color=("gray80", "gray30")).pack(fill="x", padx=12, pady=4)

        rec_frame = ctk.CTkFrame(self._sidebar, fg_color="transparent")
        rec_frame.pack(fill="x", padx=8, pady=(4, 16))

        ctk.CTkLabel(rec_frame, text="屏幕录制", font=("", 11, "bold"),
                     anchor="w").pack(fill="x", padx=4, pady=(0, 4))

        from workday.gui.widgets.recording_controls import RecordingControls
        self._rec_controls = RecordingControls(rec_frame, db=self.db)
        self._rec_controls.pack(fill="x", padx=4)

    def _show_view(self, view_id: str):
        if view_id == self._current_view:
            return

        # 高亮选中按钮
        for vid, btn in self._nav_buttons.items():
            if vid == view_id:
                btn.configure(
                    fg_color=("gray75", "gray30"),
                    text_color=("gray5", "white")
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    text_color=("gray20", "gray90")
                )

        # 隐藏当前视图
        if self._current_view and self._current_view in self._views:
            self._views[self._current_view].pack_forget()

        # 创建或显示目标视图
        if view_id not in self._views:
            self._views[view_id] = self._create_view(view_id)

        self._views[view_id].pack(fill="both", expand=True)
        self._current_view = view_id

    def _create_view(self, view_id: str) -> ctk.CTkFrame:
        parent = self._content

        if view_id == "timeline":
            from workday.gui.views.timeline import TimelineView
            return TimelineView(parent, db=self.db)
        elif view_id == "dashboard":
            from workday.gui.views.dashboard import DashboardView
            return DashboardView(parent, db=self.db)
        elif view_id == "settings":
            from workday.gui.views.settings import SettingsView
            return SettingsView(parent)
        elif view_id == "guide":
            from workday.gui.views.guide import GuideView
            return GuideView(parent)
        elif view_id == "about":
            from workday.gui.views.about import AboutView
            return AboutView(parent)
        else:
            frame = ctk.CTkFrame(parent)
            ctk.CTkLabel(frame, text=f"视图 '{view_id}' 未找到").pack(expand=True)
            return frame

    def on_closing(self):
        """应用关闭时清理"""
        try:
            self._analysis_mgr.stop()
        except Exception:
            pass
        self.destroy()


def run_app():
    """启动 GUI 应用"""
    app = WorkdayApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
