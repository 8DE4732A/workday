# Workday - 工作时间记录和分析工具

基于 Python 实现的工作时间记录工具，参考 [Dayflow](https://github.com/dayflow-ai/dayflow) 设计，使用 AI 自动分析屏幕录制生成工作时间线。

## 功能特性

- 🎥 **自动屏幕录制**：使用 MSS 进行跨平台截图（1 FPS）
- 🖥️ **多显示器支持**：支持录制单个或所有显示器
- 🤖 **AI 智能分析**：两阶段 LLM 分析流程（参考 Dayflow）
- 📊 **时间线生成**：自动生成工作活动时间线
- 💾 **本地存储**：数据保存在 SQLite 数据库
- 🌐 **RESTful API**：基于 FastAPI 的 Web 服务
- ⚙️ **动态配置**：支持通过 Web API 动态修改配置
- 🔐 **敏感信息保护**：API Keys 等敏感配置自动掩码显示

## 系统架构（两阶段分析）

```
┌─────────────────┐
│  Screen Capture │  (MSS - 1 FPS)
└────────┬────────┘
         │ 15s chunks
         ▼
┌─────────────────┐
│   SQLite DB     │  (录制片段)
└────────┬────────┘
         │ 每 15 分钟
         ▼
┌─────────────────┐
│  Stage 1: LLM   │  (transcribeVideo)
│  视频 → 观察记录 │  → Observations
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  SQLite DB      │  (观察记录)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Stage 2: LLM   │  (generateActivityCards)
│  观察 → 活动卡片 │  → Timeline Cards
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Timeline Cards │  (时间线卡片)
└─────────────────┘
```

## 快速开始

### 1. 环境要求

- Python >= 3.12
- UV 包管理器（推荐）或 pip
- **支持多模态视频输入的 LLM 模型**：
  - 推荐使用火山引擎豆包系列模型，如 `doubao-seed-1.6-flash`
  - 模型必须支持视频帧输入（multimodal video input）
  - 其他兼容火山引擎 ARK API 且支持视频理解的模型

### 2. 安装依赖

```bash
# 使用 UV（推荐）
uv sync

# 或使用 pip
pip install -e .
```

### 3. 配置 ARK API Key（首次运行）

首次运行时，可以通过环境变量设置 API Key：

**Windows (PowerShell):**
```powershell
$env:ARK_API_KEY="your_api_key_here"
```

**Linux/macOS:**
```bash
export ARK_API_KEY=your_api_key_here
```

在[火山引擎控制台](https://console.volcengine.com/ark)获取 API Key。

### 4. 配置参数

启动服务后，通过 Web 设置页面（http://localhost:8000/settings）或 API 动态修改配置：

```bash
# 查看所有配置
curl http://localhost:8000/config/all

# 修改显示器索引
curl -X PUT http://localhost:8000/config/recording.monitor_index \
  -H "Content-Type: application/json" \
  -d '{"key": "recording.monitor_index", "value": "2"}'
```

**注意**: 首次运行时，配置会自动从环境变量 `ARK_API_KEY` 和内置默认值初始化到数据库中。之后可以通过 Web 设置页面或 API 动态管理所有配置。

**查看可用显示器**

```bash
# 列出所有显示器
uv run main.py --list-monitors
```

### 5. 运行服务

```bash
# 启动 API 服务
uv run api.py
```

API 服务将在 `http://localhost:8000` 启动。

## API 接口

### 录制管理

- `POST /recording/start` - 启动屏幕录制
- `POST /recording/stop` - 停止屏幕录制
- `GET /recording/status` - 获取录制状态
- `GET /recording/monitors` - 列出所有可用显示器

### 分析管理

- `POST /analysis/start` - 启动分析服务
- `POST /analysis/stop` - 停止分析服务
- `POST /analysis/trigger` - 立即触发分析
- `POST /analysis/reprocess` - 重新处理指定日期

### 时间线数据

- `GET /timeline/today` - 获取今天的时间线
- `GET /timeline/day/{day}` - 获取指定日期的时间线
- `GET /timeline/range?start_ts=xxx&end_ts=xxx` - 获取时间范围内的时间线

### 配置管理

- `GET /config` - 获取当前配置（嵌套格式，敏感信息自动掩码）
- `GET /config/all` - 获取所有配置及元数据
- `GET /config/{key}` - 获取单个配置项
- `PUT /config/{key}` - 更新单个配置项
- `POST /config/batch` - 批量更新配置
- `POST /config/reload` - 重新加载配置

### 统计信息

- `GET /stats` - 获取统计信息

## 项目结构

```
workday/
├── api.py                   # FastAPI Web 服务
├── main.py                  # 命令行工具
├── config_manager.py        # 配置管理（数据库配置）
├── database.py              # 数据库管理
├── models.py                # 数据模型
├── recorder.py              # 屏幕录制模块（支持多显示器）
├── analysis.py              # 两阶段分析管理
├── llm_call.py              # LLM API 调用（带日志）
├── prompts.py               # 提示词管理
├── logger.py                # 日志管理
├── pyproject.toml           # 项目配置
├── workday.db               # SQLite 数据库（包含配置）
├── README.md                # 项目说明
└── SENSITIVE_CONFIG.md      # 敏感配置管理文档
```

## 核心模块说明

### 1. 屏幕录制 (recorder.py)

- 使用 MSS 进行跨平台截图
- 1 FPS 录制，每 15 秒生成一个视频片段
- **多显示器支持**：
  - 可录制所有显示器或指定单个显示器
  - 通过 `monitor_index` 配置选择
  - 支持动态查询可用显示器列表
- 自动保存到配置的目录
- 详细的录制日志

### 2. 两阶段 AI 分析 (analysis.py)

参考 Dayflow 的设计，使用两阶段 LLM 分析流程：

#### 阶段 1: 视频转录 (transcribeVideo)
- **输入**：15 分钟的屏幕录制视频
- **处理**：LLM 分析视频内容
- **输出**：3-5 个观察记录（Observations）
- **特点**：
  - 按目的分组，而非按平台
  - 只在上下文完全改变且超过 2-3 分钟时才创建新片段
  - 包含时间戳（MM:SS 格式）

#### 阶段 2: 生成活动卡片 (generateActivityCards)
- **输入**：观察记录列表（Observations）
- **处理**：LLM 生成结构化的活动卡片
- **输出**：时间线卡片（Timeline Cards）
- **特点**：
  - 每张卡片 15-60 分钟
  - 包含详细信息（category, title, summary, detailedSummary）
  - 短于 10 分钟的活动会被合并

### 3. 数据管理 (database.py)

- SQLite 数据库存储
- 五张主表：
  - `recording_chunks` - 录制片段
  - `batches` - 分析批次
  - `observations` - 观察记录（阶段 1 结果）
  - `timeline_cards` - 时间线卡片（阶段 2 结果）
  - `config` - 配置存储（键值对，支持类型和分类）
- 自动清理旧数据（默认 3 天）
- 支持配置的 CRUD 操作

### 4. LLM 集成 (llm_call.py)

- `transcribe_video()` - 第一阶段：视频转录
- `generate_activity_cards()` - 第二阶段：生成活动卡片
- **支持火山引擎豆包多模态视频模型**：
  - 推荐模型：`doubao-seed-1.6-flash`（支持视频理解）
  - 要求模型必须支持视频帧输入（multimodal video input）
  - 可在设置页面动态切换模型，无需重启服务
- 自动处理视频 base64 编码
- **详细的请求/响应日志**：
  - 记录请求参数（模型、视频大小等）
  - 记录响应长度和预览
  - 记录错误和异常信息

### 5. 配置管理 (config_manager.py)

- **数据库优先**：配置存储在 SQLite 中，支持动态修改
- **自动初始化**：首次运行时自动从环境变量和内置默认值初始化
- **敏感信息保护**：API Keys 等敏感配置自动掩码显示
- **分类组织**：配置按功能分类（recording, analysis, secrets 等）
- **类型安全**：支持 string, int, float, bool 类型
- **Web 管理**：通过设置页面可视化管理所有配置

### 6. 提示词管理 (prompts.py)

- `get_transcription_prompt()` - 视频转录提示词
- `get_activity_cards_prompt()` - 活动卡片生成提示词
- 参考 Dayflow 的 GeminiDirectProvider 提示词设计

## 使用示例

### 命令行工具

```bash
# 查看可用显示器
uv run main.py --list-monitors

# 输出示例：
# 📺 可用的显示器：
# 索引     描述                      分辨率          位置
# ----------------------------------------------------------------------
# 0        All monitors combined    3840x1080       (0, 0)
# 1        Primary monitor          1920x1080       (0, 0)
# 2        Monitor 2                1920x1080       (1920, 0)
```

### API 调用示例

```bash
# 启动录制
curl -X POST http://localhost:8000/recording/start

# 查看状态
curl http://localhost:8000/recording/status

# 列出可用显示器
curl http://localhost:8000/recording/monitors

# 查看所有配置
curl http://localhost:8000/config/all

# 修改配置（切换到第2个显示器）
curl -X PUT http://localhost:8000/config/recording.monitor_index \
  -H "Content-Type: application/json" \
  -d '{"key": "recording.monitor_index", "value": "2"}'

# 获取今天的时间线
curl http://localhost:8000/timeline/today

# 停止录制
curl -X POST http://localhost:8000/recording/stop
```

### Python 代码示例

```python
import requests

# 启动录制
response = requests.post("http://localhost:8000/recording/start")
print(response.json())

# 获取时间线
response = requests.get("http://localhost:8000/timeline/today")
timeline = response.json()

for card in timeline:
    print(f"{card['title']}: {card['description']}")
```

## 配置管理

### 配置存储

所有配置存储在 SQLite 数据库中，支持通过 Web API 动态修改：

- **首次运行**：自动从环境变量 `ARK_API_KEY` 和内置默认值初始化配置
- **后续修改**：通过 Web 设置页面或 API 更新，无需重启服务
- **敏感保护**：API Keys 等敏感信息自动掩码显示

### 配置分类

- `recording`: 录制相关配置
- `analysis`: 分析相关配置
- `retention`: 数据保留配置
- `api`: API 服务配置
- `database`: 数据库配置
- `secrets`: 敏感信息（API Keys）

### 详细文档

- [敏感配置管理](./SENSITIVE_CONFIG.md) - 敏感信息保护机制

## 数据隐私

- ✅ 所有数据本地存储
- ✅ 仅在分析时调用 LLM API
- ✅ 录制数据自动清理（可配置保留天数）
- ✅ 敏感配置（API Keys）自动掩码显示
- ✅ 完整的日志记录便于审计

## 开发

```bash
# 安装开发依赖
uv sync --all-extras

# 运行测试
uv run pytest

# 代码格式化
uv run black .
uv run ruff check .

# 测试配置掩码功能
uv run test_masking.py

# 测试动态 API Key 更新
uv run test_dynamic_api_key.py
```

## 常见问题

### 多显示器配置

**Q: 如何录制特定的显示器？**

```bash
# 1. 查看可用显示器
uv run main.py --list-monitors

# 2. 通过 API 设置显示器索引
curl -X PUT http://localhost:8000/config/recording.monitor_index \
  -H "Content-Type: application/json" \
  -d '{"key": "recording.monitor_index", "value": "2"}'

# 3. 重启录制服务即可生效
```

### 配置管理

**Q: 如何查看当前配置？**

```bash
# 查看所有配置
curl http://localhost:8000/config/all

# 查看特定分类
curl http://localhost:8000/config/category/recording
```

**Q: 如何修改 API Key？**

```bash
# 方式1: 通过 API（推荐 - 立即生效，无需重启）
curl -X PUT http://localhost:8000/config/secrets.ark_api_key \
  -H "Content-Type: application/json" \
  -d '{"key": "secrets.ark_api_key", "value": "your-new-key"}'

# 方式2: 编辑 .env 文件后重启服务
```

**注意**: 通过 API 更新 API Key 后会立即生效，系统会自动重新初始化 LLM 客户端，无需重启服务。

### 日志查看

**Q: 如何查看运行日志？**

日志文件位于 `./logs/` 目录，按日期命名：

```bash
# 查看今天的日志
tail -f logs/workday_$(date +%Y%m%d).log

# 查看 LLM 请求日志
grep "llm_call" logs/workday_$(date +%Y%m%d).log
```

## 参考项目

- [Dayflow](https://github.com/dayflow-ai/dayflow) - 原始灵感来源（Swift/macOS）
- 本项目是 Dayflow 的 Python 跨平台实现，采用相同的两阶段 LLM 分析流程

## 许可证

MIT License
