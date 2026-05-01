---
title: 命令行用法
---

# 命令行用法

## 基本命令

```
workday                 启动 GUI 界面
workday --version       查看版本号
workday list-monitors   列出可用显示器编号
```

## 多显示器配置

使用 `list-monitors` 查看显示器编号后，在「设置 → 录制配置 → 显示器」中选择：

- `0` — 录制所有显示器合并画面
- `1` — 主显示器
- `2+` — 其他显示器（依编号）

## 直接运行（无需安装）

```
# 使用 uv 在项目目录运行
uv run workday

# 作为 Python 模块运行
python -m workday
```

## 安装方式

```
# 从源码安装（开发模式）
uv sync

# 构建并安装 wheel
uv build
pip install dist/workday-*.whl
```
