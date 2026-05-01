---
title: 模型配置
---

# 模型配置

支持任何兼容 OpenAI API 格式的服务商。

## 常用服务商

- OpenAI — https://api.openai.com/v1
- 火山引擎 ARK — https://ark.cn-beijing.volces.com/api/v3
- 本地 Ollama — http://localhost:11434/v1
- 其他兼容服务 — 填写对应的 Base URL 即可

## 配置步骤

1. 在「设置」页面填写 **API Base URL** 和 **API Key**
2. 点击「获取」，程序通过 `/models` 接口自动拉取可用模型列表
3. 从下拉列表中选择目标模型，或直接在输入框中手动填写模型 ID

也可以跳过「获取」步骤，直接在输入框中手动填写模型 ID。

修改后**无需重启**即可生效。

## API Key 安全

API Key 在设置页面以掩码形式显示（如 `sk-12********89`），保存时自动识别掩码值并跳过，不会覆盖真实密钥。
