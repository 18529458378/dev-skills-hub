#!/usr/bin/env python3
"""
网文平台爬虫
支持：番茄小说、起点中文、飞卢、纵横
输出：TXT / EPUB / JSONL
"""

import os
import sys
import json
import time
import random
import re
from datetime import datetime
from urllib.parse import urljoin, quote

import click
import requests
from bs4 import BeautifulSoup
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

console = Console()

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
]


def get_headers(cookie=None):
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9",
    }
    if cookie:
        headers["Cookie"] = cookie
    return headers


def clean_content(text):
    """清洗小说正文"""
    if not text:
        return ""
    # 去除HTML标签
    text = re.sub(r'<[^>]+>', '', text)
    # 去除广告关键词
    ad_patterns = [
        r'加入书架.*?',
        r'推荐票.*?',
        r'月票.*?',
        r'打赏.*?',
        r'本章说.*?',
        r'手机用户.*?',
        r'https?://\S+',
        r'www\.\S+',
        r'（本章未完.*?）',
        r'点击下一章.*?',
    ]
    for pattern in ad_patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    # 规范化空白
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


# ========== 番茄小说 ==========

class FanqieCrawler:
    """番茄小说爬虫"""

    BASE_URL = "https://fanqienovel.com"

    def __init__(self, cookie=None, delay=1):
        self.cookie = cookie
        self.delay = delay
        self.session = requests.Session()

    def get_book_info(self, book_id):
        """获取书籍信息"""
        url = f"{self.BASE_URL}/page/{book_id}"
        try:
            resp = self.session.get(url, headers=get_headers(self.cookie), timeout=30)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'lxml')

            title = soup.find('h1')
            title = title.get_text(strip=True) if title else f"book_{book_id}"

            author = soup.find('span', class_='author')
            author = author.get_text(strip=True) if author else "未知"

            return {"id": book_id, "title": title, "author": author, "url": url}
        except Exception as e:
            console.print(f"[red]获取书籍信息失败: {e}[/red]")
            return {"id": book_id, "title": f"book_{book_id}", "author": "未知", "url": url}

    def get_chapter_list(self, book_id):
        """获取章节列表"""
        url = f"{self.BASE_URL}/page/{book_id}"
        chapters = []
        try:
            resp = self.session.get(url, headers=get_headers(self.cookie), timeout=30)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'lxml')

            # 番茄小说目录通常在 div.chapter-item 或 a 标签中
            chapter_links = soup.find_all('a', href=re.compile(r'/reader/'))
            for i, link in enumerate(chapter_links, 1):
                chapter_url = urljoin(self.BASE_URL, link['href'])
                chapter_title = link.get_text(strip=True) or f"第{i}章"
                chapters.append({
                    "index": i,
                    "title": chapter_title,
                    "url": chapter_url
                })
        except Exception as e:
            console.print(f"[red]获取章节列表失败: {e}[/red]")

        return chapters

    def get_chapter_content(self, chapter_url):
        """获取章节内容"""
        try:
            resp = self.session.get(chapter_url, headers=get_headers(self.cookie), timeout=30)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'lxml')

            # 番茄小说正文容器
            content_div = soup.find('div', class_=re.compile(r'content|chapter-content|muye-reader-content'))
            if content_div:
                paragraphs = content_div.find_all('p')
                content = "\n\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
            else:
                # 备用：提取所有p标签
                paragraphs = soup.find_all('p')
                content = "\n\n".join(p.get_text(strip=True) for p in paragraphs
                                       if len(p.get_text(strip=True)) > 20)

            return clean_content(content)
        except Exception as e:
            console.print(f"  [red]获取章节失败: {e}[/red]")
            return ""


# ========== 起点中文 ==========

class QidianCrawler:
    """起点中文爬虫（需Cookie）"""

    BASE_URL = "https://book.qidian.com"

    def __init__(self, cookie=None, delay=1):
        self.cookie = cookie
        self.delay = delay
        self.session = requests.Session()

    def get_book_info(self, book_id=None, url=None):
        if not url:
            url = f"{self.BASE_URL}/info/{book_id}"
        try:
            resp = self.session.get(url, headers=get_headers(self.cookie), timeout=30)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'lxml')

            title = soup.find('h1')
            title = title.get_text(strip=True) if title else "未知书名"

            author = soup.find('a', class_='writer')
            author = author.get_text(strip=True) if author else "未知"

            return {"id": book_id or url.split('/')[-1], "title": title, "author": author, "url": url}
        except Exception as e:
            console.print(f"[red]获取书籍信息失败: {e}[/red]")
            return {"id": book_id, "title": "未知", "author": "未知", "url": url}

    def get_chapter_list(self, book_id=None, url=None):
        if not url:
            url = f"{self.BASE_URL}/info/{book_id}"
        chapters = []
        try:
            # 起点目录页
            catalog_url = url.replace("/info/", "/") if "/info/" in url else url
            resp = self.session.get(catalog_url, headers=get_headers(self.cookie), timeout=30)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'lxml')

            chapter_items = soup.find_all('li', class_='j_chapterBox') or soup.find_all('div', class_='volume')
            for vol in chapter_items:
                links = vol.find_all('a')
                for i, link in enumerate(links, 1):
                    chapter_url = urljoin(self.BASE_URL, link.get('href', ''))
                    chapter_title = link.get_text(strip=True)
                    if chapter_title and chapter_url:
                        chapters.append({"index": len(chapters)+1, "title": chapter_title, "url": chapter_url})
        except Exception as e:
            console.print(f"[red]获取章节列表失败: {e}[/red]")
        return chapters

    def get_chapter_content(self, chapter_url):
        try:
            resp = self.session.get(chapter_url, headers=get_headers(self.cookie), timeout=30)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'lxml')

            content_div = soup.find('div', class_='read-content') or soup.find('div', id='content')
            if content_div:
                content = content_div.get_text('\n', strip=True)
            else:
                paragraphs = soup.find_all('p')
                content = "\n\n".join(p.get_text(strip=True) for p in paragraphs
                                       if len(p.get_text(strip=True)) > 10)
            return clean_content(content)
        except Exception as e:
            console.print(f"  [red]获取章节失败: {e}[/red]")
            return ""


# ========== 输出函数 ==========

def save_as_txt(chapters, book_info, output_path):
    """保存为TXT"""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"{book_info['title']}\n")
        f.write(f"作者: {book_info['author']}\n")
        f.write(f"来源: {book_info.get('url', '')}\n")
        f.write(f"下载时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 50 + "\n\n")

        for ch in chapters:
            f.write(f"{ch['title']}\n\n")
            f.write(f"{ch['content']}\n\n")
            f.write("-" * 30 + "\n\n")

    console.print(f"[green]TXT已保存: {output_path}[/green]")


def save_as_jsonl(chapters, book_info, output_path):
    """保存为JSONL"""
    with open(output_path, 'w', encoding='utf-8') as f:
        for ch in chapters:
            record = {
                "book_id": book_info.get("id", ""),
                "book_title": book_info["title"],
                "author": book_info["author"],
                "chapter_index": ch["index"],
                "chapter_title": ch["title"],
                "content": ch["content"],
                "word_count": len(ch["content"]),
                "timestamp": datetime.now().isoformat()
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    console.print(f"[green]JSONL已保存: {output_path}[/green]")


def save_as_epub(chapters, book_info, output_path):
    """保存为EPUB（需要ebooklib）"""
    try:
        from ebooklib import epub
    except ImportError:
        console.print("[yellow]未安装ebooklib，跳过EPUB生成，使用TXT代替[/yellow]")
        save_as_txt(chapters, book_info, output_path.replace('.epub', '.txt'))
        return

    book = epub.EpubBook()
    book.set_identifier(book_info.get("id", "unknown"))
    book.set_title(book_info["title"])
    book.set_language("zh")
    book.add_author(book_info["author"])

    epub_chapters = []
    for ch in chapters:
        c = epub.EpubHtml(title=ch["title"], file_name=f"chap_{ch['index']}.xhtml", lang="zh")
        content_html = "<h2>" + ch["title"] + "</h2>"
        for para in ch["content"].split("\n\n"):
            if para.strip():
                content_html += f"<p>{para.strip()}</p>"
        c.content = content_html
        book.add_item(c)
        epub_chapters.append(c)

    book.toc = tuple(epub_chapters)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ["nav"] + epub_chapters

    epub.write_epub(output_path, book)
    console.print(f"[green]EPUB已保存: {output_path}[/green]")


# ========== 主程序 ==========

@click.command()
@click.option('--platform', '-p', required=True,
              type=click.Choice(['fanqie', 'qidian', 'faloo', 'zongheng']),
              help='网文平台')
@click.option('--book-id', help='书籍ID')
@click.option('--url', help='书籍URL（优先于book-id）')
@click.option('--cookie', help='登录Cookie（VIP章节需要）')
@click.option('--output', '-o', default='novel.txt', help='输出文件 (.txt/.epub/.jsonl)')
@click.option('--max-chapters', default=0, type=int, help='最大章节数（0=全部）')
@click.option('--start-chapter', default=1, type=int, help='起始章节')
@click.option('--delay', default=1, type=float, help='请求延迟秒数')
def main(platform, book_id, url, cookie, output, max_chapters, start_chapter, delay):
    """网文平台爬虫"""

    # 选择爬虫
    if platform == "fanqie":
        crawler = FanqieCrawler(cookie=cookie, delay=delay)
    elif platform == "qidian":
        crawler = QidianCrawler(cookie=cookie, delay=delay)
    else:
        console.print(f"[yellow]平台 {platform} 开发中，使用通用模式[/yellow]")
        crawler = FanqieCrawler(cookie=cookie, delay=delay)

    console.print(Panel(
        f"平台: {platform}\n书籍ID: {book_id or 'URL指定'}\n"
        f"起始章节: {start_chapter}\n最大章节: {max_chapters or '全部'}\n"
        f"输出: {output}",
        title="网文爬虫", border_style="blue"
    ))

    # 获取书籍信息
    console.print("\n[bold]获取书籍信息...[/bold]")
    book_info = crawler.get_book_info(book_id=book_id, url=url) if hasattr(crawler, 'get_book_info') else {"id": book_id, "title": "未知", "author": "未知", "url": url}
    console.print(f"  书名: {book_info['title']}")
    console.print(f"  作者: {book_info['author']}")

    # 获取章节列表
    console.print("\n[bold]获取章节列表...[/bold]")
    chapters = crawler.get_chapter_list(book_id=book_id, url=url) if hasattr(crawler, 'get_chapter_list') else []
    console.print(f"  共 {len(chapters)} 章")

    if not chapters:
        console.print("[red]未获取到章节，请检查书籍ID或Cookie[/red]")
        sys.exit(1)

    # 筛选章节范围
    chapters = chapters[start_chapter-1:]
    if max_chapters > 0:
        chapters = chapters[:max_chapters]

    console.print(f"  实际爬取: {len(chapters)} 章")

    # 爬取章节内容
    console.print("\n[bold]开始爬取章节内容...[/bold]")
    results = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        console=console
    ) as progress:
        task = progress.add_task("爬取中...", total=len(chapters))

        for ch in chapters:
            progress.update(task, description=f"{ch['title'][:30]}...")
            content = crawler.get_chapter_content(ch["url"])
            ch["content"] = content
            results.append(ch)
            progress.advance(task)

            if delay > 0:
                time.sleep(delay + random.uniform(0, delay))

    # 统计
    total_words = sum(len(ch["content"]) for ch in results)
    console.print(f"\n[green]爬取完成！共 {len(results)} 章，{total_words} 字[/green]")

    # 保存
    fmt = output.split('.')[-1].lower() if '.' in output else 'txt'
    if fmt == 'epub':
        save_as_epub(results, book_info, output)
    elif fmt == 'jsonl':
        save_as_jsonl(results, book_info, output)
    else:
        save_as_txt(results, book_info, output)


if __name__ == "__main__":
    main()
