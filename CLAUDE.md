# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Workday is a Python cross-platform implementation of [Dayflow](https://github.com/dayflow-ai/dayflow), an AI-powered work time tracking tool. It automatically records your screen at 1 FPS and uses a two-stage LLM analysis pipeline to generate activity timelines. Configuration is stored in SQLite and can be dynamically updated via Web API without restarting the service.

## Development Commands

### Backend (Python)

```bash
# Install dependencies
uv sync

# Install dev dependencies
uv sync --all-extras

# Run API server
uv run api.py

# List available monitors
uv run main.py --list-monitors

# Run tests
uv run pytest

# Code formatting
uv run black .
uv run ruff check .

# Test configuration masking
uv run test_masking.py

# Test dynamic API key update
uv run test_dynamic_api_key.py
```

### Frontend (Next.js)

```bash
cd web

# Install dependencies
npm install

# Development server
npm run dev

# Build static export (outputs to web/out/)
npm run build
```

### Full Stack

```bash
# 1. Build frontend
cd web && npm install && npm run build && cd ..

# 2. Start API server (serves both API and static frontend)
uv run api.py
# Access at http://localhost:8000
```

## Architecture Overview

### Two-Stage LLM Analysis Pipeline

The system follows Dayflow's design with two LLM analysis stages:

1. **Stage 1: Video Transcription** (`transcribe_video()` in `llm_call.py`)
   - Input: 15-minute screen recording video
   - Output: 3-5 Observations (timestamped activity descriptions)
   - Groups activities by purpose, not platform

2. **Stage 2: Activity Card Generation** (`generate_activity_cards()` in `llm_call.py`)
   - Input: Observations from Stage 1
   - Output: Timeline Cards (15-60 minute activity summaries)
   - Categories: 工作, 学习, 娱乐, 其他

### Core Backend Modules

- **api.py**: FastAPI server with REST endpoints for recording, analysis, timeline, and config management
- **recorder.py**: Screen capture using MSS library (1 FPS), multi-monitor support via `monitor_index` config
- **analysis.py**: Manages analysis batches and triggers two-stage LLM pipeline
- **llm_call.py**: Volcano Engine ARK API integration with intelligent client caching for dynamic API key updates
- **config_manager.py**: Database-backed configuration with sensitive value masking
- **database.py**: SQLite operations for chunks, batches, observations, timeline_cards, and config tables

### Frontend Structure (web/)

Next.js 14 App Router with TypeScript and Tailwind CSS:
- **src/app/**: Pages (timeline, settings, analytics)
- **src/components/**: Reusable UI components
- **src/lib/api.ts**: API client for backend communication
- **src/types/**: TypeScript interfaces

### Configuration System

All configuration stored in SQLite with these features:
- First-run initialization from environment variable `ARK_API_KEY` and built-in defaults
- Dynamic updates via Web settings page or API without service restart
- Sensitive value masking (API keys show as `sk-12****89`)
- Type validation (string, int, float, bool)

Key config paths:
- `recording.monitor_index`: Monitor selection (0=all, 1=primary, 2+=others)
- `analysis.model`: LLM model name
- `secrets.ark_api_key`: Volcano Engine API key (sensitive)

### Database Schema

Five main tables in `workday.db`:
- `recording_chunks`: 15-second video segments
- `batches`: 15-minute analysis batches
- `observations`: Stage 1 LLM output
- `timeline_cards`: Stage 2 LLM output (final timeline)
- `config`: Key-value configuration store

## API Endpoints

### Recording
- `POST /recording/start` - Start screen recording
- `POST /recording/stop` - Stop screen recording
- `GET /recording/status` - Get recording state
- `GET /recording/monitors` - List available monitors

### Analysis
- `POST /analysis/start` - Start background analysis service
- `POST /analysis/trigger` - Trigger immediate analysis
- `POST /analysis/reprocess` - Reprocess specific day

### Timeline
- `GET /timeline/today` - Today's timeline cards
- `GET /timeline/day/{day}` - Specific day (YYYY-MM-DD)
- `GET /timeline/range?start_ts=&end_ts=` - Time range

### Configuration
- `GET /config` - Nested config object (masked)
- `GET /config/all` - All configs with metadata
- `PUT /config/{key}` - Update single config
- `POST /config/batch` - Batch update

## Environment Setup

1. (Optional) Set environment variable for first run:
```bash
# Windows (PowerShell)
$env:ARK_API_KEY="your_volcengine_ark_api_key"

# Linux/macOS
export ARK_API_KEY=your_volcengine_ark_api_key
```

2. Get API key from [Volcano Engine Console](https://console.volcengine.com/ark)

3. Configuration auto-initializes to database on first run from `ARK_API_KEY` environment variable and built-in defaults

## Data Locations

```
workday/
├── workday.db           # SQLite database (config + data)
├── recordings/          # Screen recording chunks (default)
└── logs/                # Application logs
```

## Key Implementation Details

### Dynamic API Key Updates

The LLM client in `llm_call.py` uses intelligent caching:
```python
def get_client() -> Ark:
    # Automatically recreates client when API key changes
    # No service restart required
```

### Sensitive Config Masking

Values are masked when `is_sensitive=True` in `CONFIG_SCHEMA`:
- Display: `sk-12********89` (first 4 + last 4 chars)
- Masked values cannot accidentally overwrite real values (auto-detected and skipped)

### Multi-Monitor Support

`recorder.py` supports selecting specific monitors:
- `monitor_index: 0` - All monitors combined
- `monitor_index: 1` - Primary monitor
- `monitor_index: 2+` - Secondary monitors

Use `/recording/monitors` API or `--list-monitors` CLI to discover available monitors.
