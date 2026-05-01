"""
提示词模板
参考 Dayflow 的 GeminiDirectProvider 提示词
"""


def get_transcription_prompt(duration_string: str) -> str:
    return f"""# Video Transcription Prompt

Your job is to transcribe someone's computer usage into a small number of meaningful activity segments.

## CRITICAL: This video is exactly {duration_string} long. ALL timestamps MUST be within 00:00 to {duration_string}.

## Golden Rule: Aim for 3-5 segments per 15-minute video (fewer is better than more)

## Core Principles:
1. **Group by purpose, not by platform** - If someone is planning a trip across 5 websites, that's ONE segment
2. **Include interruptions in the description** - Don't create segments for brief distractions
3. **Only split when context changes for 2-3+ minutes** - Quick checks don't count as context switches
4. **Combine related activities** - Multiple videos on the same topic = one segment
5. **Think in terms of "sessions"** - What would you tell a friend you spent time doing?
6. **Idle detection** - if the screen stays exactly the same for 5+ minutes, make sure to note that within the observation that the user was idle during that period and not performing any actions, but still be specific about what's currently on the screen.

## When to create a new segment:
Only when the user switches to a COMPLETELY different purpose for MORE than 2-3 minutes:
- Entertainment → Work
- Learning → Shopping
- Project A → Project B
- Topic X → Unrelated Topic Y

## Format:
```json
[
  {{
    "startTimestamp": "MM:SS",
    "endTimestamp": "MM:SS",
    "description": "1-3 sentences describing what the user accomplished"
  }}
]
```

## Examples:

**GOOD - Properly condensed:**
```json
[
  {{
    "startTimestamp": "00:00",
    "endTimestamp": "06:45",
    "description": "User plans a trip to Japan, researching flights on multiple booking sites, reading hotel reviews, and watching YouTube videos about Tokyo neighborhoods. They briefly check email twice and respond to a text message during their research."
  }},
  {{
    "startTimestamp": "06:45",
    "endTimestamp": "10:30",
    "description": "User takes an online Spanish course, completing lesson exercises and watching grammar explanation videos. They use Google Translate to verify some phrases and briefly check Reddit when they get stuck on a difficult concept."
  }},
  {{
    "startTimestamp": "10:30",
    "endTimestamp": "14:58",
    "description": "User shops for home gym equipment, comparing prices across Amazon, fitness retailer sites, and watching product review videos. They check their banking app to verify their budget midway through."
  }}
]
```

**BAD - Too many segments:**
```json
[
  {{
    "startTimestamp": "00:00",
    "endTimestamp": "02:00",
    "description": "User searches for flights to Tokyo"
  }},
  {{
    "startTimestamp": "02:00",
    "endTimestamp": "02:30",
    "description": "User checks email"
  }},
  {{
    "startTimestamp": "02:30",
    "endTimestamp": "04:00",
    "description": "User looks at hotels in Tokyo"
  }},
  {{
    "startTimestamp": "04:00",
    "endTimestamp": "05:00",
    "description": "User watches a Tokyo travel video"
  }}
]
```

Remember: The goal is to tell the story of what someone accomplished, not log every click. Group aggressively and only split when they truly change what they're doing for an extended period.
"""


def get_transcription_prompt_images(duration_string: str, frame_count: int) -> str:
    return f"""# Image Transcription Prompt

Your job is to transcribe someone's computer usage into a small number of meaningful activity segments.

## CRITICAL: You will receive {frame_count} screenshots taken over {duration_string}. Each screenshot is preceded by a 'Frame at HH:MM:SS:' marker. Frames that didn't change significantly have been deduplicated. ALL timestamps MUST be within 00:00 to {duration_string}.

## Golden Rule: Aim for 3-5 segments per 15-minute period (fewer is better than more)

## Core Principles:
1. **Group by purpose, not by platform** - If someone is planning a trip across 5 websites, that's ONE segment
2. **Include interruptions in the description** - Don't create segments for brief distractions
3. **Only split when context changes for 2-3+ minutes** - Quick checks don't count as context switches
4. **Combine related activities** - Multiple screenshots on the same topic = one segment
5. **Think in terms of "sessions"** - What would you tell a friend you spent time doing?
6. **Idle detection** - if the screenshots show the same screen for an extended period, note that the user was idle but still describe what's on screen.

## When to create a new segment:
Only when the user switches to a COMPLETELY different purpose for MORE than 2-3 minutes:
- Entertainment → Work
- Learning → Shopping
- Project A → Project B
- Topic X → Unrelated Topic Y

## Format:
```json
[
  {{
    "startTimestamp": "MM:SS",
    "endTimestamp": "MM:SS",
    "description": "1-3 sentences describing what the user accomplished"
  }}
]
```

## Examples:

**GOOD - Properly condensed:**
```json
[
  {{
    "startTimestamp": "00:00",
    "endTimestamp": "06:45",
    "description": "User plans a trip to Japan, researching flights on multiple booking sites, reading hotel reviews, and watching YouTube videos about Tokyo neighborhoods. They briefly check email twice and respond to a text message during their research."
  }},
  {{
    "startTimestamp": "06:45",
    "endTimestamp": "10:30",
    "description": "User takes an online Spanish course, completing lesson exercises and watching grammar explanation videos. They use Google Translate to verify some phrases and briefly check Reddit when they get stuck on a difficult concept."
  }},
  {{
    "startTimestamp": "10:30",
    "endTimestamp": "{duration_string}",
    "description": "User shops for home gym equipment, comparing prices across Amazon, fitness retailer sites, and watching product review videos. They check their banking app to verify their budget midway through."
  }}
]
```

Remember: The goal is to tell the story of what someone accomplished, not log every screenshot. Group aggressively and only split when they truly change what they're doing for an extended period.
"""


def get_activity_cards_prompt(observations_text: str, existing_cards_json: str = "[]") -> str:
    return f"""You are a digital anthropologist, observing a user's raw activity log. Your goal is to synthesize this log into a high-level, human-readable story of their session, presented as a series of timeline cards.

THE GOLDEN RULE:
    Create cards that narrate one cohesive session, aiming for 15–60 minutes. Keep every card ≥10 minutes, split up any cards that are >60 minutes, and if a prospective card would be <10 minutes, merge it into the neighboring card that preserves the best story.

    CONTINUITY RULE:
    You may adjust boundaries for clarity, but never introduce new gaps or overlaps. Preserve any original gaps in the source timeline and keep adjacent covered spans meeting cleanly.

    CORE DIRECTIVES:
    - Theme Test Before Extending: Extend the current card only when the new observations continue the same dominant activity. Shifts shorter than 10 minutes should be logged as distractions or merged into the adjacent segment that keeps the theme coherent; shifts ≥10 minutes become new cards.

TITLE
- 2-5 words that capture the essence of what the user did.
- Use action verbs (e.g., "Designing website mockups" not "Website design").
- Be specific but concise (e.g., "Writing Python documentation" not "Working on code").
- Avoid vague titles like "Various tasks" or "Computer work".

SUMMARY
- 1-2 sentences (max 150 characters) describing the main accomplishment or activity.
- Focus on the outcome or goal, not individual steps.
- Use past tense to describe what was done.

CATEGORY
Choose exactly one category that best describes this activity from these options:
- "工作" (Work) - Professional tasks, coding, writing, meetings, emails
- "学习" (Learning) - Courses, tutorials, reading documentation, studying
- "娱乐" (Entertainment) - Videos, games, social media browsing
- "其他" (Other) - Everything else

Return the category exactly as written above.

DETAILED SUMMARY
- 2-4 sentences (max 500 characters) providing more context.
- Include specific tools, websites, or applications used.
- Mention any notable accomplishments or blockers.
- Can include brief interruptions if they're part of the story.

INPUTS:
Previous cards: {existing_cards_json}
New observations: {observations_text}

Return ONLY a JSON array with this EXACT structure:

[
  {{
    "startTime": "1:12 PM",
    "endTime": "1:30 PM",
    "category": "工作",
    "subcategory": "编程",
    "title": "实现用户认证功能",
    "summary": "完成了用户登录和注册功能的后端实现，包括 JWT token 生成和验证",
    "detailedSummary": "在 VS Code 中编写 Python Flask 代码，实现了用户认证系统。创建了登录和注册 API 端点，集成了 JWT token 认证。测试了基本功能并修复了几个边缘情况的 bug。期间查看了 Flask-JWT-Extended 文档来确认最佳实践。",
    "distractions": [
      {{
        "startTime": "1:15 PM",
        "endTime": "1:18 PM",
        "title": "查看微信消息",
        "summary": "快速回复了几条工作相关的消息"
      }}
    ]
  }}
]
"""


def get_analysis_summary_prompt(
    scope_label: str,
    stats: dict,
    cards_brief: list,
) -> str:
    """构造分析报告 LLM prompt"""
    total_seconds = stats.get("total_active_seconds", 0)
    total_h = total_seconds // 3600
    total_m = (total_seconds % 3600) // 60
    total_str = f"{total_h} 小时 {total_m} 分钟" if total_h else f"{total_m} 分钟"

    total_cards = stats.get("total_cards", 0)

    cat_lines = []
    cat_total = sum(c["seconds"] for c in stats.get("category_breakdown", []))
    for c in stats.get("category_breakdown", []):
        pct = round(c["seconds"] / cat_total * 100) if cat_total else 0
        h = c["seconds"] // 3600
        m = (c["seconds"] % 3600) // 60
        dur = f"{h}h {m}m" if h else f"{m}m"
        cat_lines.append(f"  - {c['category']}：{dur}（{pct}%）")
    cat_block = "\n".join(cat_lines) if cat_lines else "  - 暂无分类数据"

    hourly = stats.get("hourly_distribution", [])
    if hourly:
        peak = max(hourly, key=lambda x: x["seconds"])
        peak_str = f"{peak['hour']:02d}:00-{peak['hour']+1:02d}:00"
    else:
        peak_str = "未知"

    top_lines = []
    for i, act in enumerate(cards_brief[:8], 1):
        h = act["seconds"] // 3600
        m = (act["seconds"] % 3600) // 60
        dur = f"{h}h {m}m" if h else f"{m}m"
        top_lines.append(f"  {i}. [{act['category']}] {act['title']} - {dur}")
    top_block = "\n".join(top_lines) if top_lines else "  暂无活动"

    detail_lines = []
    for act in cards_brief[:15]:
        h = act["seconds"] // 3600
        m = (act["seconds"] % 3600) // 60
        dur = f"{h}h {m}m" if h else f"{m}m"
        desc = act.get("description", "")[:80]
        detail_lines.append(f"  {act['category']} | {act['title']} | {dur} | {desc}")
    detail_block = "\n".join(detail_lines) if detail_lines else "  暂无详情"

    return f"""你是一位专业的工作复盘助手，请基于用户在 {scope_label} 的活动记录生成一份简洁的工作分析报告。

## 活动数据
- 总活跃时长：{total_str}
- 卡片数量：{total_cards}
- 分类分布：
{cat_block}
- 最活跃时段：{peak_str}
- 主要活动（Top 8）：
{top_block}

## 卡片细节（每条：类别 | 标题 | 时长 | 简述）
{detail_block}

## 输出要求
用**中文 Markdown**输出（## 二级标题 + - 无序列表），控制在 500 字内，包含以下部分：
## 整体总结
一段 2-3 句话描述这段时间的整体状态。

## 工作亮点
1-3 条核心产出

## 学习收获
1-3 条学到的东西（没有则写"本日无明显学习活动"）

## 改进建议
1-2 条可落地的建议（基于娱乐占比、专注时段分布等）

**不要**输出任何代码块、寒暄、"好的以下是"等字样，直接从 `## 整体总结` 开始。"""
