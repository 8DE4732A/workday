"""使用指南视图"""
import customtkinter as ctk


GUIDE_CONTENT = [
    ("Workday 使用指南", "title"),
    ("", "space"),
    ("Workday 是一款 AI 驱动的工作时间追踪工具，自动录制屏幕并通过 LLM 生成每日活动时间线。", "intro"),
    ("", "space"),
    ("快速开始", "heading"),
    (
        "1. 配置模型：在「设置」页面填写 API Base URL 和 API Key，"
        "点击「获取」自动拉取模型列表后选择，也可手动输入模型 ID。",
        "body"
    ),
    (
        "2. 开始录制：点击左侧侧边栏底部的「开始录制」按钮，"
        "程序将以 1 FPS 截取屏幕，每 15 秒打包为一个视频片段保存到 recordings/ 目录。",
        "body"
    ),
    (
        "3. AI 分析：录制数据自动提交后台分析，通过两阶段 LLM 流水线处理："
        "\n  · 第一阶段：视频转录，将屏幕录制解读为 3-5 条观察记录"
        "\n  · 第二阶段：活动卡片生成，将观察记录合成为 15-60 分钟的活动卡片",
        "body"
    ),
    (
        "4. 查看时间线：切换到「时间线」视图，用日期导航浏览每天的活动，"
        "点击卡片查看详细描述。",
        "body"
    ),
    ("", "space"),
    ("模型配置", "heading"),
    ("支持任何兼容 OpenAI API 格式的服务商，例如：", "body"),
    ("  OpenAI          https://api.openai.com/v1", "bullet"),
    ("  火山引擎 ARK     https://ark.cn-beijing.volces.com/api/v3", "bullet"),
    ("  本地 Ollama      http://localhost:11434/v1", "bullet"),
    ("  其他兼容服务      填写对应的 Base URL 即可", "bullet"),
    (
        "填写 API Base URL 和 API Key 后点击「获取」，程序将通过 /models 接口自动拉取"
        "可用模型列表供选择；也可以跳过此步骤，直接在输入框中手动填写模型 ID。",
        "body"
    ),
    ("", "space"),
    ("活动分类", "heading"),
    ("每个活动卡片会自动归入以下四种类型之一：", "body"),
    ("  工作 - 编程、写作、会议、邮件等职业任务", "bullet"),
    ("  学习 - 课程、教程、文档阅读、技术研究", "bullet"),
    ("  娱乐 - 视频、游戏、社交媒体浏览", "bullet"),
    ("  其他 - 不属于以上分类的活动", "bullet"),
    ("", "space"),
    ("Token 用量", "heading"),
    (
        "在「仪表盘」页面可查看每次 AI 分析消耗的 Token 数量，支持按日期过滤。"
        "每批次视频分析包含两次 LLM 调用（转录 + 卡片生成）。",
        "body"
    ),
    ("", "space"),
    ("数据存储", "heading"),
    ("所有数据均保存在本地，不会上传云端（仅 LLM 调用时传输屏幕内容）。", "body"),
    ("  workday.db    SQLite 数据库，存储活动记录、配置和 Token 用量", "bullet"),
    ("  recordings/   屏幕录制视频片段", "bullet"),
    ("  logs/         应用运行日志", "bullet"),
    ("", "space"),
    ("命令行用法", "heading"),
    ("  workday            启动 GUI 界面", "code"),
    ("  workday --version  查看版本", "code"),
]


class GuideView(ctk.CTkScrollableFrame):
    """使用指南视图"""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._build()

    def _build(self):
        for text, style in GUIDE_CONTENT:
            if style == "space":
                ctk.CTkFrame(self, height=8, fg_color="transparent").pack()
                continue
            if style == "title":
                ctk.CTkLabel(self, text=text, font=("", 22, "bold"),
                             anchor="w").pack(fill="x", padx=20, pady=(20, 4))
            elif style == "heading":
                ctk.CTkLabel(self, text=text, font=("", 15, "bold"),
                             anchor="w").pack(fill="x", padx=20, pady=(8, 4))
            elif style == "intro":
                ctk.CTkLabel(self, text=text, font=("", 13),
                             anchor="w", wraplength=640,
                             text_color=("gray40", "gray70")).pack(fill="x", padx=20, pady=2)
            elif style == "body":
                ctk.CTkLabel(self, text=text, font=("", 13),
                             anchor="w", justify="left", wraplength=640).pack(fill="x", padx=20, pady=2)
            elif style == "bullet":
                row = ctk.CTkFrame(self, fg_color="transparent")
                row.pack(fill="x", padx=20, pady=1)
                ctk.CTkLabel(row, text=text, font=("", 13),
                             anchor="w", wraplength=620).pack(side="left")
            elif style == "code":
                frame = ctk.CTkFrame(self, fg_color=("gray90", "gray20"), corner_radius=4)
                frame.pack(fill="x", padx=20, pady=2)
                ctk.CTkLabel(frame, text=text, font=("Courier", 12),
                             anchor="w").pack(padx=12, pady=4)

        ctk.CTkFrame(self, height=24, fg_color="transparent").pack()
