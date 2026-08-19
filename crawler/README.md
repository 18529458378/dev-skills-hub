# 网络爬虫模块

通用爬虫模板和网文平台爬虫，支持并发、重试、代理、数据清洗管道。

## 功能

### 通用爬虫模板 (scraper_template.py)
- **并发爬取**：基于 ThreadPoolExecutor 的多线程爬虫
- **自动重试**：失败自动重试，指数退避
- **代理支持**：HTTP/HTTPS 代理池
- **User-Agent 轮换**：随机 UA 降低被封风险
- **请求限流**：可配置 QPS 和并发数
- **数据去重**：URL 去重、内容哈希去重
- **断点续爬**：支持保存/恢复爬取进度
- **多种解析**：BeautifulSoup / lxml / 正则表达式

### 网文平台爬虫 (novel_crawler.py)
- **多平台支持**：番茄小说、起点中文、飞卢、纵横
- **章节爬取**：批量下载小说章节内容
- **目录解析**：自动解析小说目录页
- **格式输出**：TXT / EPUB / JSONL
- **内容清洗**：去除广告、乱码、多余空行
- **增量更新**：检测新章节并追加

## 安装

```bash
pip install -r requirements.txt
```

## 快速使用

### 1. 通用爬虫

```bash
# 爬取单个页面
python scraper_template.py --url "https://example.com" --output data.json

# 批量爬取（从文件读取URL）
python scraper_template.py --file urls.txt --concurrency 10 --output results.jsonl

# 使用代理
python scraper_template.py --url "https://example.com" --proxy "http://127.0.0.1:7890"
```

### 2. 网文爬虫

```bash
# 爬取番茄小说
python novel_crawler.py --platform fanqie --book-id "123456789" --output novel.txt

# 爬取起点小说（需要cookie）
python novel_crawler.py --platform qidian --url "https://book.qidian.com/info/1012345678" --cookie "你的cookie" --output novel.epub

# 只爬取前10章
python novel_crawler.py --platform fanqie --book-id "123456" --max-chapters 10
```

## 通用爬虫配置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--concurrency` | 5 | 并发线程数 |
| `--timeout` | 30 | 请求超时（秒） |
| `--retries` | 3 | 失败重试次数 |
| `--delay` | 1 | 请求间隔（秒） |
| `--random-delay` | True | 随机延迟 |
| `--max-depth` | 1 | 爬取深度 |
| `--follow-links` | False | 是否跟踪页面内链接 |

## 网文平台支持

| 平台 | 命令值 | 状态 | 备注 |
|------|--------|------|------|
| 番茄小说 | `fanqie` | ✅ | 免费章节，无需登录 |
| 起点中文 | `qidian` | ⚠️ | 需 Cookie，VIP章节需订阅 |
| 飞卢小说 | `faloo` | ⚠️ | 需 Cookie |
| 纵横中文 | `zongheng` | ✅ | 免费章节 |

## 输出格式

### JSONL (通用爬虫)
```json
{"url": "https://example.com", "status": 200, "title": "页面标题", "content": "...", "links": [...], "timestamp": "..."}
```

### TXT (网文爬虫)
```
第1章 标题

正文内容...

第2章 标题

正文内容...
```

## 爬虫管道架构

```
URL列表 → 去重器 → 调度器 → 下载器(并发/重试/代理) → 解析器 → 清洗器 → 存储器
                ↑                                                    ↓
                └────────────── 新URL发现 ←─────────────────────────┘
```

## 法律与道德声明

1. **遵守 robots.txt**：爬取前检查目标网站的 robots.txt
2. **控制频率**：不要对目标服务器造成过大压力
3. **尊重版权**：爬取的内容仅供个人学习使用
4. **数据保护**：不要爬取个人隐私数据
5. **用户协议**：部分平台明确禁止爬虫，请遵守相关规定

## 推荐工具

- **Scrapling**：现代Python爬虫框架，替代BeautifulSoup
- **Katana**：Go语言编写的高速爬虫
- **Crawl4AI**：AI驱动的网页爬取和解析
- **Colly**：Go语言爬虫框架
