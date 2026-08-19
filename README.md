# Dev Skills Hub

开发者技能工具集，涵盖代码生成推理、Windows 系统清理优化、浏览器自动化搜索、网络爬虫四大模块。

## 模块概览

| 模块 | 语言 | 用途 |
|------|------|------|
| [code-gen](./code-gen) | Python | 基于 DeepSeek API 的代码生成、审查、推理 |
| [windows-cleanup](./windows-cleanup) | PowerShell | Windows 临时文件清理、系统优化、隐私保护 |
| [browser-search](./browser-search) | Python | 多搜索引擎自动化搜索、结果提取、无头浏览器 |
| [crawler](./crawler) | Python | 通用爬虫模板、网文平台爬虫、数据清洗管道 |

## 快速开始

```bash
# 克隆仓库
git clone https://github.com/18529458378/dev-skills-hub.git
cd dev-skills-hub

# 安装各模块依赖
cd code-gen && pip install -r requirements.txt
cd ../browser-search && pip install -r requirements.txt
cd ../crawler && pip install -r requirements.txt
```

## 环境要求

- Python 3.10+
- PowerShell 5.1+（Windows 模块）
- DeepSeek API Key（代码生成模块）

## License

MIT
