# 浏览器自动化搜索模块

基于 Playwright 的多搜索引擎自动化搜索工具，支持无头浏览器、结果提取、批量搜索。

## 功能

- **多引擎支持**：Google、Bing、百度、DuckDuckGo、搜狗
- **无头模式**：支持有头/无头浏览器切换
- **结果提取**：自动提取标题、链接、摘要、排名
- **批量搜索**：支持从文件读取关键词批量搜索
- **反爬策略**：随机延迟、User-Agent 轮换、代理支持
- **多种输出**：JSON、CSV、Markdown 格式

## 安装

```bash
pip install -r requirements.txt
playwright install chromium
```

## 快速使用

### 1. 单关键词搜索

```bash
python search.py --query "Python 爬虫教程" --engine google --headless
```

### 2. 多引擎搜索

```bash
python search.py --query "AI 工具" --engine all --output results.json
```

### 3. 批量搜索

```bash
# 从文件读取关键词（每行一个）
python search.py --file keywords.txt --engine bing --output batch_results.csv
```

### 4. 有头模式（调试用）

```bash
python search.py --query "test" --engine baidu --no-headless
```

## 支持的搜索引擎

| 引擎 | 命令值 | 状态 | 备注 |
|------|--------|------|------|
| Google | `google` | ✅ | 需要能访问 google.com |
| Bing | `bing` | ✅ | 稳定 |
| 百度 | `baidu` | ✅ | 国内稳定 |
| DuckDuckGo | `duckduckgo` | ✅ | 隐私搜索 |
| 搜狗 | `sogou` | ✅ | 微信搜索支持 |
| 全部 | `all` | ✅ | 依次搜索所有引擎 |

## 输出格式

### JSON
```json
{
  "query": "Python 爬虫",
  "engine": "google",
  "timestamp": "2026-08-19T12:00:00",
  "results": [
    {
      "rank": 1,
      "title": "Python 爬虫入门教程",
      "url": "https://example.com/python-crawler",
      "snippet": "从零开始学习 Python 爬虫..."
    }
  ]
}
```

### CSV
```csv
rank,title,url,snippet,engine,query
1,Python 爬虫入门,https://example.com,从零开始...,google,Python 爬虫
```

## 高级用法

### 使用代理
```bash
python search.py --query "test" --engine google --proxy "http://127.0.0.1:7890"
```

### 自定义搜索数量
```bash
python search.py --query "test" --engine bing --num-results 50
```

### 延迟设置（反爬）
```bash
python search.py --query "test" --engine all --delay 3 --random-delay
```

## 注意事项

1. **遵守 robots.txt**：不要爬取明确禁止的内容
2. **控制频率**：建议设置 `--delay` 避免被封 IP
3. **Google 访问**：国内使用 Google 需要代理
4. **结果数量**：各引擎首页结果数量不同，通常 10-20 条
