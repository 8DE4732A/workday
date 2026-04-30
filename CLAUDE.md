# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Workday is a Python cross-platform implementation of [Dayflow](https://github.com/dayflow-ai/dayflow), an AI-powered work time tracking tool. It automatically records your screen at 1 FPS and uses a two-stage LLM analysis pipeline to generate activity timelines. The desktop GUI is built with CustomTkinter.

## Project Structure

```
workday/
├── src/
│   └── workday/
│       ├── __init__.py              # __version__ = "0.2.0"
│       ├── __main__.py              # python -m workday
│       ├── cli.py                   # CLI entry: workday [--version]
│       ├── core/
│       │   ├── models.py            # Data models + INIT_SQL
│       │   ├── database.py          # SQLite operations
│       │   ├── config.py            # Config management + get_config() factory
│       │   └── logger.py            # LogManager + get_logger()
│       ├── services/
│       │   ├── recorder.py          # Screen capture (MSS, 1 FPS)
│       │   ├── analysis.py          # LLM analysis pipeline manager
│       │   ├── llm_call.py          # Volcano Engine ARK API
│       │   └── prompts.py           # Prompt templates
│       ├── gui/
│       │   ├── app.py               # Main window + sidebar navigation
│       │   ├── views/
│       │   │   ├── timeline.py      # Timeline view
│       │   │   ├── settings.py      # Settings view
│       │   │   ├── dashboard.py     # Token usage dashboard
│       │   │   └── guide.py         # Usage guide
│       │   └── widgets/
│       │       ├── activity_card.py # Activity card component
│       │       ├── date_nav.py      # Date navigation component
│       │       └── recording_controls.py  # Recording controls
│       └── utils/
│           └── convert_video.py     # Video conversion tool
├── tests/
├── pyproject.toml
├── README.md
└── CLAUDE.md
```

## Development Commands

```bash
# Install dependencies
uv sync

# Install dev dependencies
uv sync --all-extras

# Launch GUI
uv run workday

# Print version
uv run workday --version

# Run tests
uv run pytest

# Lint
uv run ruff check src/

# Format
uv run ruff format src/
```

## Architecture Overview

### Two-Stage LLM Analysis Pipeline

1. **Stage 1: Video Transcription** (`transcribe_video()` in `services/llm_call.py`)
   - Input: 15-second screen recording chunks grouped into batches
   - Output: 3-5 Observations (timestamped activity descriptions)

2. **Stage 2: Activity Card Generation** (`generate_activity_cards()` in `services/llm_call.py`)
   - Input: Observations from Stage 1
   - Output: Timeline Cards (15-60 minute activity summaries)
   - Categories: 工作, 学习, 娱乐, 其他

### GUI Architecture

- **Main thread**: CustomTkinter mainloop (`gui/app.py`)
- **Daemon thread**: Screen recorder (`services/recorder.py`)
- **Background service**: `AnalysisManager` auto-started on app init
- Views are lazy-created on first navigation and toggled via `pack`/`pack_forget`

### Configuration System

All configuration stored in SQLite (`workday.db`). Access via `get_config()` lazy factory in `core/config.py`.

Key config paths:
- `recording.monitor_index`: Monitor selection (0=all, 1=primary, 2+=others)
- `analysis.model`: LLM model name
- `secrets.ark_api_key`: Volcano Engine API key (sensitive, masked in display)

### Database Schema

Five main tables in `workday.db`:
- `recording_chunks`: 15-second video segments
- `batches`: 15-minute analysis batches
- `observations`: Stage 1 LLM output
- `timeline_cards`: Stage 2 LLM output (final timeline)
- `config`: Key-value configuration store
- `token_usage`: LLM API token consumption records

## Environment Setup

1. (Optional) Set environment variable for first run:
```bash
# Windows (PowerShell)
$env:ARK_API_KEY="your_volcengine_ark_api_key"

# Linux/macOS
export ARK_API_KEY=your_volcengine_ark_api_key
```

2. Get API key from [Volcano Engine Console](https://console.volcengine.com/ark)

3. On first run, config auto-initializes from `ARK_API_KEY` env var and built-in defaults.
   You can also set it in the GUI Settings page.

## Data Locations

```
workday/
├── workday.db           # SQLite database (config + data)
├── recordings/          # Screen recording video chunks
└── logs/                # Application logs
```

## Key Implementation Details

### Circular Import Prevention

`core/config.py` uses a lazy `get_config()` factory (not a module-level singleton) and lazily imports `Database` inside `Config._get_db()`. This prevents circular imports between `config` ↔ `database`.

### Dynamic API Key Updates

`services/llm_call.py` caches the ARK client and recreates it when the API key changes — no restart required.

### Sensitive Config Masking

Values with `is_sensitive=True` in `CONFIG_SCHEMA` are displayed as `sk-12********89`. Masked values are auto-detected and skipped on save to prevent overwriting real values.

### Multi-Monitor Support

`recording.monitor_index`: 0=all monitors combined, 1=primary, 2+=secondary.
Use `workday list-monitors` to discover available monitors.
