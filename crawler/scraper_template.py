#!/usr/bin/env python3
"""
通用爬虫模板
特性：并发、重试、代理、UA轮换、去重、断点续爬、深度爬取
"""

import os
import sys
import json
import time
import random
import hashlib
from datetime import datetime
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import deque

import click
import requests
from bs4 import BeautifulSoup
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

console = Console()

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
]


class Scraper:
    """通用爬虫类"""

    def __init__(self, concurrency=5, timeout=30, retries=3, delay=1,
                 random_delay=True, proxy=None, max_depth=1, follow_links=False,
                 allowed_domains=None, output_path=None, resume=False):
        self.concurrency = concurrency
        self.timeout = timeout
        self.retries = retries
        self.delay = delay
        self.random_delay = random_delay
        self.proxy = proxy
        self.max_depth = max_depth
        self.follow_links = follow_links
        self.allowed_domains = allowed_domains or []
        self.output_path = output_path
        self.resume = resume

        self.session = requests.Session()
        self.visited_urls = set()
        self.content_hashes = set()
        self.results = []
        self.queue = deque()
        self.stats = {"success": 0, "failed": 0, "skipped": 0}

        # 加载断点
        if resume and output_path and os.path.exists(output_path):
            self._load_state()

    def _get_headers(self):
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        }

    def _get_proxies(self):
        if self.proxy:
            return {"http": self.proxy, "https": self.proxy}
        return None

    def _is_allowed(self, url):
        """检查URL是否在允许的域名内"""
        if not self.allowed_domains:
            return True
        try:
            domain = urlparse(url).netloc
            return any(d in domain for d in self.allowed_domains)
        except:
            return False

    def fetch(self, url):
        """抓取单个URL，带重试"""
        for attempt in range(self.retries):
            try:
                resp = self.session.get(
                    url,
                    headers=self._get_headers(),
                    proxies=self._get_proxies(),
                    timeout=self.timeout,
                    allow_redirects=True
                )
                resp.raise_for_status()
                return resp
            except requests.exceptions.RequestException as e:
                if attempt < self.retries - 1:
                    wait = (2 ** attempt) + random.uniform(0, 1)
                    console.print(f"  [yellow]重试 ({attempt+1}/{self.retries}): {url} - 等待 {wait:.1f}s[/yellow]")
                    time.sleep(wait)
                else:
                    console.print(f"  [red]失败: {url} - {e}[/red]")
                    return None

    def parse(self, url, response):
        """解析页面内容"""
        soup = BeautifulSoup(response.text, 'lxml')

        # 提取标题
        title = soup.title.string.strip() if soup.title else ""

        # 提取正文（简单策略：取所有p标签）
        paragraphs = soup.find_all('p')
        content = "\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))

        # 提取所有链接
        links = []
        if self.follow_links:
            for a in soup.find_all('a', href=True):
                href = a['href']
                if href.startswith(('http://', 'https://')):
                    full_url = href
                elif href.startswith('/'):
                    full_url = urljoin(url, href)
                else:
                    continue
                if self._is_allowed(full_url) and full_url not in self.visited_urls:
                    links.append(full_url)

        # 内容去重
        content_hash = hashlib.md5(content.encode()).hexdigest() if content else ""
        is_duplicate = content_hash in self.content_hashes if content_hash else False
        if content_hash:
            self.content_hashes.add(content_hash)

        return {
            "url": url,
            "status": response.status_code,
            "title": title,
            "content": content[:10000],  # 限制长度
            "content_length": len(content),
            "links": links,
            "links_count": len(links),
            "is_duplicate": is_duplicate,
            "encoding": response.encoding,
            "timestamp": datetime.now().isoformat()
        }

    def _save_result(self, result):
        """保存单个结果"""
        self.results.append(result)
        if self.output_path:
            mode = 'a' if self.stats["success"] > 0 or self.resume else 'w'
            with open(self.output_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(result, ensure_ascii=False) + "\n")

    def _load_state(self):
        """加载断点状态"""
        try:
            with open(self.output_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        self.visited_urls.add(data["url"])
                        if data.get("content"):
                            h = hashlib.md5(data["content"].encode()).hexdigest()
                            self.content_hashes.add(h)
                        self.stats["success"] += 1
            console.print(f"[green]已加载断点: {len(self.visited_urls)} 个URL已爬取[/green]")
        except Exception as e:
            console.print(f"[yellow]加载断点失败: {e}[/yellow]")

    def crawl(self, urls):
        """执行爬取"""
        # 初始化队列
        for url in urls:
            if url not in self.visited_urls:
                self.queue.append((url, 0))  # (url, depth)

        console.print(Panel(
            f"待爬取: {len(self.queue)} 个URL\n并发: {self.concurrency}\n"
            f"深度: {self.max_depth}\n代理: {self.proxy or '无'}",
            title="通用爬虫", border_style="blue"
        ))

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            task = progress.add_task("爬取中...", total=len(self.queue))

            while self.queue:
                batch = []
                for _ in range(min(self.concurrency, len(self.queue))):
                    if self.queue:
                        batch.append(self.queue.popleft())

                with ThreadPoolExecutor(max_workers=self.concurrency) as executor:
                    futures = {}
                    for url, depth in batch:
                        if url in self.visited_urls:
                            self.stats["skipped"] += 1
                            continue
                        self.visited_urls.add(url)
                        future = executor.submit(self._crawl_one, url, depth)
                        futures[future] = (url, depth)

                    for future in as_completed(futures):
                        url, depth = futures[future]
                        try:
                            result, new_links = future.result()
                            if result:
                                self._save_result(result)
                                self.stats["success"] += 1
                                # 添加新链接到队列
                                if self.follow_links and depth < self.max_depth:
                                    for link in new_links:
                                        if link not in self.visited_urls:
                                            self.queue.append((link, depth + 1))
                            else:
                                self.stats["failed"] += 1
                        except Exception as e:
                            console.print(f"[red]处理异常: {url} - {e}[/red]")
                            self.stats["failed"] += 1

                        progress.update(task, advance=1, total=len(self.visited_urls) + len(self.queue))

                        # 请求延迟
                        if self.delay > 0:
                            delay = self.delay + random.uniform(0, self.delay) if self.random_delay else self.delay
                            time.sleep(delay / self.concurrency)

        console.print(f"\n[bold green]爬取完成！[/bold green]")
        console.print(f"  成功: {self.stats['success']}")
        console.print(f"  失败: {self.stats['failed']}")
        console.print(f"  跳过: {self.stats['skipped']}")

        return self.results

    def _crawl_one(self, url, depth):
        """爬取单个页面"""
        response = self.fetch(url)
        if not response:
            return None, []
        result = self.parse(url, response)
        return result, result.get("links", [])


@click.command()
@click.option('--url', '-u', help='单个URL')
@click.option('--file', '-f', help='URL列表文件（每行一个）')
@click.option('--concurrency', '-c', default=5, type=int, help='并发数')
@click.option('--timeout', '-t', default=30, type=int, help='超时秒数')
@click.option('--retries', '-r', default=3, type=int, help='重试次数')
@click.option('--delay', '-d', default=1, type=float, help='请求延迟')
@click.option('--random-delay/--no-random-delay', default=True, help='随机延迟')
@click.option('--proxy', default=None, help='代理地址')
@click.option('--max-depth', default=1, type=int, help='爬取深度')
@click.option('--follow-links/--no-follow-links', default=False, help='跟踪页面链接')
@click.option('--allowed-domain', multiple=True, help='允许的域名（可多次指定）')
@click.option('--output', '-o', default='crawl-results.jsonl', help='输出文件')
@click.option('--resume/--no-resume', default=False, help='断点续爬')
def main(url, file, concurrency, timeout, retries, delay, random_delay, proxy,
         max_depth, follow_links, allowed_domain, output, resume):
    """通用爬虫模板"""

    urls = []
    if url:
        urls.append(url)
    if file:
        if os.path.exists(file):
            with open(file, 'r', encoding='utf-8') as f:
                urls.extend([line.strip() for line in f if line.strip() and not line.startswith('#')])
        else:
            console.print(f"[red]文件不存在: {file}[/red]")
            sys.exit(1)

    if not urls:
        console.print("[red]错误: 请指定 --url 或 --file[/red]")
        sys.exit(1)

    scraper = Scraper(
        concurrency=concurrency,
        timeout=timeout,
        retries=retries,
        delay=delay,
        random_delay=random_delay,
        proxy=proxy,
        max_depth=max_depth,
        follow_links=follow_links,
        allowed_domains=list(allowed_domain),
        output_path=output,
        resume=resume
    )

    results = scraper.crawl(urls)
    console.print(f"\n[green]结果已保存到: {output}[/green]")


if __name__ == "__main__":
    main()
