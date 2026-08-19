#!/usr/bin/env python3
"""
多搜索引擎自动化搜索工具
基于 Playwright，支持 Google/Bing/百度/DuckDuckGo/搜狗
"""

import os
import sys
import json
import time
import random
import csv
from datetime import datetime
from urllib.parse import quote_plus

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

console = Console()

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
except ImportError:
    console.print("[red]错误: 请先安装 playwright[/red]")
    console.print("运行: pip install playwright && playwright install chromium")
    sys.exit(1)


# 搜索引擎配置
ENGINES = {
    "google": {
        "url": "https://www.google.com/search?q={query}&num={num}",
        "selectors": {
            "result": "div.g",
            "title": "h3",
            "url": "a",
            "snippet": "div.VwiC3b, div.IsZvec"
        },
        "name": "Google"
    },
    "bing": {
        "url": "https://www.bing.com/search?q={query}&count={num}",
        "selectors": {
            "result": "li.b_algo",
            "title": "h2",
            "url": "h2 a",
            "snippet": "div.b_caption p, p.b_lineclamp4"
        },
        "name": "Bing"
    },
    "baidu": {
        "url": "https://www.baidu.com/s?wd={query}&rn={num}",
        "selectors": {
            "result": "div.result, div.c-container",
            "title": "h3 a",
            "url": "h3 a",
            "snippet": "div.c-abstract, span.content-right_8Zs40"
        },
        "name": "百度"
    },
    "duckduckgo": {
        "url": "https://html.duckduckgo.com/html/?q={query}",
        "selectors": {
            "result": "div.result",
            "title": "a.result__a",
            "url": "a.result__a",
            "snippet": "a.result__snippet"
        },
        "name": "DuckDuckGo"
    },
    "sogou": {
        "url": "https://www.sogou.com/web?query={query}&num={num}",
        "selectors": {
            "result": "div.results div.vrwrap, div.rb",
            "title": "h3 a",
            "url": "h3 a",
            "snippet": "div.ft, p.str-text_info"
        },
        "name": "搜狗"
    }
}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


def random_delay(base_delay=2, randomize=True):
    """随机延迟"""
    if randomize:
        delay = base_delay + random.uniform(0, base_delay)
    else:
        delay = base_delay
    time.sleep(delay)


def search_engine(engine_name, query, num_results=10, headless=True, proxy=None,
                  delay=2, random_delay_flag=True, timeout=30000):
    """搜索单个搜索引擎"""
    if engine_name not in ENGINES:
        console.print(f"[red]不支持的搜索引擎: {engine_name}[/red]")
        return []

    config = ENGINES[engine_name]
    url = config["url"].format(query=quote_plus(query), num=num_results)
    selectors = config["selectors"]

    results = []
    user_agent = random.choice(USER_AGENTS)

    try:
        with sync_playwright() as p:
            browser_args = {
                "headless": headless,
                "args": [
                    "--no-sandbox",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                ]
            }
            if proxy:
                browser_args["proxy"] = {"server": proxy}

            browser = p.chromium.launch(**browser_args)
            context = browser.new_context(
                user_agent=user_agent,
                viewport={"width": 1920, "height": 1080},
                locale="zh-CN"
            )
            # 隐藏 webdriver 特征
            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                window.chrome = { runtime: {} };
            """)

            page = context.new_page()
            page.set_default_timeout(timeout)

            console.print(f"  [{config['name']}] 正在搜索: {query}")
            page.goto(url, wait_until="domcontentloaded")

            # 等待结果加载
            try:
                page.wait_for_selector(selectors["result"], timeout=10000)
            except PlaywrightTimeout:
                console.print(f"  [yellow][{config['name']}] 未找到结果元素，可能被反爬[/yellow]")
                browser.close()
                return []

            # 滚动加载更多结果
            for _ in range(3):
                page.evaluate("window.scrollBy(0, window.innerHeight)")
                time.sleep(0.5)

            # 提取结果
            elements = page.query_selector_all(selectors["result"])
            for rank, elem in enumerate(elements[:num_results], 1):
                try:
                    title_elem = elem.query_selector(selectors["title"])
                    url_elem = elem.query_selector(selectors["url"])
                    snippet_elem = elem.query_selector(selectors["snippet"])

                    title = title_elem.inner_text().strip() if title_elem else ""
                    link = url_elem.get_attribute("href") if url_elem else ""
                    snippet = snippet_elem.inner_text().strip() if snippet_elem else ""

                    # 处理百度跳转链接
                    if engine_name == "baidu" and link and "link?url=" in link:
                        link = "https://www.baidu.com" + link if link.startswith("/") else link

                    if title and link:
                        results.append({
                            "rank": rank,
                            "title": title,
                            "url": link,
                            "snippet": snippet[:500] if snippet else "",
                            "engine": engine_name,
                            "query": query
                        })
                except Exception as e:
                    continue

            browser.close()
            console.print(f"  [green][{config['name']}] 获取到 {len(results)} 条结果[/green]")

    except Exception as e:
        console.print(f"  [red][{config['name']}] 搜索失败: {e}[/red]")

    return results


def save_results(results, output_path, format="json"):
    """保存搜索结果"""
    if not results:
        console.print("[yellow]没有结果可保存[/yellow]")
        return

    if format == "json" or output_path.endswith(".json"):
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "total": len(results),
                "results": results
            }, f, ensure_ascii=False, indent=2)

    elif format == "csv" or output_path.endswith(".csv"):
        fieldnames = ["rank", "title", "url", "snippet", "engine", "query"]
        with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)

    elif format == "md" or output_path.endswith(".md"):
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"# 搜索结果\n\n")
            f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**结果数量**: {len(results)}\n\n---\n\n")
            current_engine = ""
            for r in results:
                if r["engine"] != current_engine:
                    current_engine = r["engine"]
                    f.write(f"\n## {ENGINES.get(current_engine, {}).get('name', current_engine)}\n\n")
                f.write(f"### {r['rank']}. {r['title']}\n")
                f.write(f"- **链接**: {r['url']}\n")
                if r['snippet']:
                    f.write(f"- **摘要**: {r['snippet']}\n")
                f.write("\n")

    console.print(f"[green]结果已保存到: {output_path}[/green]")


@click.command()
@click.option('--query', '-q', help='搜索关键词')
@click.option('--file', '-f', help='从文件读取关键词（每行一个）')
@click.option('--engine', '-e', default='baidu',
              type=click.Choice(['google', 'bing', 'baidu', 'duckduckgo', 'sogou', 'all']),
              help='搜索引擎 (默认: baidu)')
@click.option('--num-results', '-n', default=10, type=int, help='每个引擎结果数量')
@click.option('--output', '-o', default=None, help='输出文件路径 (.json/.csv/.md)')
@click.option('--headless/--no-headless', default=True, help='无头模式 (默认: 开启)')
@click.option('--proxy', default=None, help='代理地址，如 http://127.0.0.1:7890')
@click.option('--delay', '-d', default=2, type=float, help='请求延迟秒数')
@click.option('--random-delay/--no-random-delay', default=True, help='随机延迟')
def main(query, file, engine, num_results, output, headless, proxy, delay, random_delay):
    """多搜索引擎自动化搜索工具"""

    # 收集关键词
    queries = []
    if query:
        queries.append(query)
    if file:
        if os.path.exists(file):
            with open(file, 'r', encoding='utf-8') as f:
                queries.extend([line.strip() for line in f if line.strip()])
        else:
            console.print(f"[red]文件不存在: {file}[/red]")
            sys.exit(1)

    if not queries:
        console.print("[red]错误: 请指定 --query 或 --file[/red]")
        sys.exit(1)

    # 确定搜索引擎列表
    if engine == "all":
        engines_to_use = list(ENGINES.keys())
    else:
        engines_to_use = [engine]

    console.print(Panel(
        f"关键词: {len(queries)} 个\n引擎: {', '.join(ENGINES[e]['name'] for e in engines_to_use)}\n"
        f"模式: {'无头' if headless else '有头'}\n代理: {proxy or '无'}",
        title="浏览器搜索", border_style="blue"
    ))

    all_results = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        console=console
    ) as progress:
        total = len(queries) * len(engines_to_use)
        task = progress.add_task("搜索中...", total=total)

        for q in queries:
            for eng in engines_to_use:
                progress.update(task, description=f"{ENGINES[eng]['name']}: {q[:30]}...")
                results = search_engine(
                    eng, q, num_results=num_results, headless=headless,
                    proxy=proxy, delay=delay, random_delay_flag=random_delay
                )
                all_results.extend(results)
                progress.advance(task)

                # 引擎间延迟
                if len(engines_to_use) > 1:
                    random_delay(delay, random_delay)

    console.print(f"\n[bold green]搜索完成！共获取 {len(all_results)} 条结果[/bold green]")

    # 保存结果
    if output:
        fmt = output.split('.')[-1] if '.' in output else 'json'
        save_results(all_results, output, format=fmt)
    else:
        # 显示前10条结果
        console.print("\n[bold]前10条结果:[/bold]")
        for r in all_results[:10]:
            engine_name = ENGINES.get(r['engine'], {}).get('name', r['engine'])
            console.print(f"  [{engine_name}] {r['rank']}. [cyan]{r['title']}[/cyan]")
            console.print(f"     {r['url']}")
            if r['snippet']:
                console.print(f"     [gray]{r['snippet'][:100]}...[/gray]")
            console.print()


if __name__ == "__main__":
    main()
