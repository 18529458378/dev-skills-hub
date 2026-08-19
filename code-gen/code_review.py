#!/usr/bin/env python3
"""
代码审查工具
支持：单文件审查、目录批量审查、安全漏洞检测、性能分析、规范检查
输出：Markdown 格式审查报告
"""

import os
import sys
import json
import click
import requests
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from datetime import datetime

load_dotenv()
console = Console()

DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-coder"

# 支持的代码文件扩展名
CODE_EXTENSIONS = {
    '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.c', '.cpp', '.h',
    '.go', '.rs', '.rb', '.php', '.swift', '.kt', '.scala', '.sh',
    '.sql', '.html', '.css', '.scss', '.vue', '.svelte'
}


def get_api_key():
    key = os.getenv("DEEPSEEK_API_KEY")
    if not key:
        console.print("[red]错误: 未设置 DEEPSEEK_API_KEY[/red]")
        sys.exit(1)
    return key


def call_deepseek(messages, model=None, temperature=0.3, max_tokens=8192):
    """调用 DeepSeek API"""
    api_key = get_api_key()
    base_url = os.getenv("DEEPSEEK_BASE_URL", DEFAULT_BASE_URL)
    model = model or os.getenv("DEEPSEEK_MODEL", DEFAULT_MODEL)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens
    }

    try:
        resp = requests.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=180
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
    except requests.exceptions.RequestException as e:
        console.print(f"[red]API 请求失败: {e}[/red]")
        return None


def review_file(filepath, model=None):
    """审查单个文件"""
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        code = f.read()

    if not code.strip():
        return None

    ext = os.path.splitext(filepath)[1]
    language = ext.lstrip('.') if ext else 'text'

    system_prompt = """你是一位资深代码审查专家，擅长发现安全漏洞、性能问题和代码缺陷。
请对以下代码进行严格审查，按以下格式输出（JSON）：

{
  "security": [{"issue": "问题描述", "severity": "high/medium/low", "line": "行号", "fix": "修复建议"}],
  "performance": [{"issue": "问题描述", "severity": "high/medium/low", "fix": "修复建议"}],
  "quality": [{"issue": "问题描述", "severity": "high/medium/low", "fix": "修复建议"}],
  "summary": "总体评价",
  "score": 0-100
}

只输出JSON，不要其他内容。"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"文件: {filepath}\n语言: {language}\n\n代码:\n```\n{code}\n```"}
    ]

    result = call_deepseek(messages, model=model)
    if not result:
        return None

    # 尝试解析JSON
    try:
        # 清理可能的代码块标记
        result = result.strip()
        if result.startswith("```"):
            result = result.split("\n", 1)[1]
            if result.endswith("```"):
                result = result.rsplit("```", 1)[0]
        return json.loads(result.strip())
    except json.JSONDecodeError:
        return {"raw": result, "summary": "解析失败，原始输出", "score": 0}


def generate_markdown_report(results, output_path):
    """生成 Markdown 格式审查报告"""
    total_files = len(results)
    avg_score = sum(r.get('score', 0) for r in results if r) / max(total_files, 1)

    md = f"""# 代码审查报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**审查文件数**: {total_files}
**平均评分**: {avg_score:.1f}/100

---

## 总览

| 指标 | 数量 |
|------|------|
| 高危安全问题 | {sum(len(r.get('security', [])) for r in results if r and 'security' in r)} |
| 性能问题 | {sum(len(r.get('performance', [])) for r in results if r and 'performance' in r)} |
| 代码质量问题 | {sum(len(r.get('quality', [])) for r in results if r and 'quality' in r)} |

---

"""

    for i, (filepath, result) in enumerate(results.items(), 1):
        if not result:
            continue
        md += f"## {i}. `{filepath}`\n\n"
        md += f"**评分**: {result.get('score', 'N/A')}/100\n\n"
        md += f"**总结**: {result.get('summary', '无')}\n\n"

        for category, title, emoji in [
            ('security', '安全问题', '🔒'),
            ('performance', '性能问题', '⚡'),
            ('quality', '代码质量', '📝')
        ]:
            issues = result.get(category, [])
            if issues:
                md += f"### {emoji} {title}\n\n"
                for issue in issues:
                    severity = issue.get('severity', 'unknown')
                    severity_icon = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(severity, '⚪')
                    md += f"- {severity_icon} **[{severity.upper()}]** {issue.get('issue', '未知问题')}"
                    if issue.get('line'):
                        md += f" (行 {issue['line']})"
                    md += "\n"
                    if issue.get('fix'):
                        md += f"  - 修复: {issue['fix']}\n"
                md += "\n"

        md += "---\n\n"

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(md)

    return md


@click.command()
@click.option('--file', '-f', help='审查单个文件')
@click.option('--dir', '-d', help='审查目录下所有代码文件')
@click.option('--output', '-o', default='code-review-report.md', help='报告输出路径')
@click.option('--model', '-m', default=None, help='模型名称')
@click.option('--recursive/--no-recursive', default=True, help='是否递归子目录')
def main(file, dir, output, model, recursive):
    """代码审查工具"""
    if not file and not dir:
        console.print("[red]错误: 请指定 --file 或 --dir[/red]")
        sys.exit(1)

    files_to_review = []

    if file:
        if os.path.exists(file):
            files_to_review.append(file)
        else:
            console.print(f"[red]文件不存在: {file}[/red]")
            sys.exit(1)

    if dir:
        if not os.path.isdir(dir):
            console.print(f"[red]目录不存在: {dir}[/red]")
            sys.exit(1)
        for root, _, filenames in os.walk(dir):
            if not recursive and root != dir:
                continue
            for fname in filenames:
                ext = os.path.splitext(fname)[1].lower()
                if ext in CODE_EXTENSIONS:
                    files_to_review.append(os.path.join(root, fname))

    if not files_to_review:
        console.print("[yellow]未找到可审查的代码文件[/yellow]")
        sys.exit(0)

    console.print(Panel(f"待审查文件: {len(files_to_review)} 个",
                        title="代码审查", border_style="blue"))

    results = {}
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("审查中...", total=len(files_to_review))
        for filepath in files_to_review:
            progress.update(task, description=f"审查: {os.path.basename(filepath)}")
            result = review_file(filepath, model=model)
            results[filepath] = result
            progress.advance(task)

    console.print("\n[green]审查完成！[/green]")

    # 生成报告
    md = generate_markdown_report(results, output)
    console.print(f"[green]报告已保存到: {output}[/green]")

    # 显示摘要
    console.print(Panel(md[:2000] + ("..." if len(md) > 2000 else ""),
                        title="审查摘要", border_style="green"))


if __name__ == "__main__":
    main()
