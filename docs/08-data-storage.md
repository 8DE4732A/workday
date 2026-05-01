---
title: 数据存储
---

# 数据存储

所有数据均保存在本地，不会上传云端（仅 LLM 调用时传输屏幕内容）。

## 文件结构

```
workday/
├── workday.db       SQLite 数据库，存储活动记录、配置和 Token 用量
├── recordings/      屏幕录制视频片段（15 秒 .mp4 文件）
└── logs/            应用运行日志
```

## 数据库表

- `recording_chunks` — 15 秒视频片段记录
- `batches` — 15 分钟分析批次
- `observations` — 第一阶段 LLM 输出（观察记录）
- `timeline_cards` — 第二阶段 LLM 输出（最终时间线）
- `config` — 键值配置存储
- `token_usage` — LLM API Token 消耗记录

## 隐私说明

- 屏幕截图/视频片段在 LLM 分析时会上传至配置的 API 服务商
- 分析完成后，原始录制文件保留在本地 `recordings/` 目录
- 如需清理磁盘空间，可手动删除 `recordings/` 下的旧文件，不影响已生成的时间线数据
