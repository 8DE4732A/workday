"""
提示词模板
参考 Dayflow 的 GeminiDirectProvider 提示词
"""

def get_transcription_prompt(duration_string: str) -> str:
    """
    获取视频转录提示词

    Args:
        duration_string: 视频时长格式化字符串 (MM:SS)

    Returns:
        提示词字符串
    """
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

**ALSO BAD - Splitting brief interruptions:**
```json
[
  {{
    "startTimestamp": "00:00",
    "endTimestamp": "05:00",
    "description": "User shops for gym equipment"
  }},
  {{
    "startTimestamp": "05:00",
    "endTimestamp": "05:45",
    "description": "User checks their bank balance"
  }},
  {{
    "startTimestamp": "05:45",
    "endTimestamp": "10:00",
    "description": "User continues shopping for gym equipment"
  }}
]
```

**CORRECT way to handle the above:**
```json
[
  {{
    "startTimestamp": "00:00",
    "endTimestamp": "10:00",
    "description": "User shops for home gym equipment across multiple retailers, comparing dumbbells, benches, and resistance bands. They briefly check their bank balance around the 5-minute mark to confirm their budget before continuing."
  }}
]
```

Remember: The goal is to tell the story of what someone accomplished, not log every click. Group aggressively and only split when they truly change what they're doing for an extended period. If an activity is less than 2-3 minutes, it almost never deserves its own segment.
"""


def get_activity_cards_prompt(observations_text: str, existing_cards_json: str = "[]") -> str:
    """
    获取活动卡片生成提示词

    Args:
        observations_text: 格式化的观察记录文本
        existing_cards_json: 已存在的卡片 JSON（用于滑动窗口）

    Returns:
        提示词字符串
    """
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

DISTRACTIONS
A "distraction" is a brief (<5 min) and unrelated activity that interrupts the main theme of a card. Sustained activities (>5 min) are NOT distractions - they either belong to the current theme or warrant a new card. Don't label related sub-tasks as distractions.

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
