#!/usr/bin/env python3
"""
DeepSeek 代码生成工具
支持：代码生成、代码解释、多语言输出、批量生成
"""

import os
import sys
import json
import click
import requests
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

load_dotenv()
console = Console()

DEFAULT_BASE_URL = "https://api.deepseek.com"
DEFAULT_MODEL = "deepseek-coder"


def get_api_key():
    key = os.getenv("DEEPSEEK_API_KEY")
    if not key:
        console.print("[red]错误: 未设置 DEEPSEEK_API_KEY 环境变量[/red]")
        console.print("请运行: export DEEPSEEK_API_KEY='your-api-key'")
        sys.exit(1)
    return key


def call_deepseek(messages, model=None, temperature=0.7, max_tokens=4096):
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
        "max_tokens": max_tokens,
        "stream": False
    }

    try:
        resp = requests.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=120
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except requests.exceptions.RequestException as e:
        console.print(f"[red]API 请求失败: {e}[/red]")
        if hasattr(e, 'response') and e.response is not None:
            console.print(f"[red]响应: {e.response.text}[/red]")
        sys.exit(1)


@click.group()
def cli():
    """DeepSeek 代码生成工具"""
    pass


@cli.command()
@click.option('--prompt', '-p', required=True, help='代码生成描述')
@click.option('--language', '-l', default='python', help='目标编程语言')
@click.option('--model', '-m', default=None, help='模型名称')
@click.option('--output', '-o', default=None, help='输出文件路径')
@click.option('--temperature', '-t', default=0.7, type=float, help='生成温度')
def generate(prompt, language, model, output, temperature):
    """根据描述生成代码"""
    console.print(Panel(f"[bold]生成 {language} 代码[/bold]\n描述: {prompt}",
                        title="代码生成", border_style="blue"))

    messages = [
        {"role": "system", "content": f"你是一位资深 {language} 开发工程师。"
         "请根据用户需求生成高质量、可运行、带注释的代码。"
         "只输出代码，不要多余解释。"},
        {"role": "user", "content": prompt}
    ]

    with console.status("[bold green]正在生成代码..."):
        code = call_deepseek(messages, model=model, temperature=temperature)

    # 清理代码块标记
    code = code.strip()
    if code.startswith("```"):
        lines = code.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        code = "\n".join(lines)

    console.print(Panel(Syntax(code, language, theme="monokai", line_numbers=True),
                        title="生成结果", border_style="green"))

    if output:
        with open(output, 'w', encoding='utf-8') as f:
            f.write(code)
        console.print(f"[green]代码已保存到: {output}[/green]")

    return code


@cli.command()
@click.option('--file', '-f', required=True, help='要解释的代码文件')
@click.option('--model', '-m', default=None, help='模型名称')
def explain(file, model):
    """解释代码逻辑"""
    if not os.path.exists(file):
        console.print(f"[red]文件不存在: {file}[/red]")
        sys.exit(1)

    with open(file, 'r', encoding='utf-8') as f:
        code = f.read()

    ext = os.path.splitext(file)[1].lstrip('.') or 'text'

    console.print(Panel(f"文件: {file}\n语言: {ext}", title="代码解释", border_style="blue"))

    messages = [
        {"role": "system", "content": "你是一位资深软件架构师。请详细解释以下代码的逻辑、"
         "算法思路、关键设计决策，并指出潜在的改进点。用中文回答，结构清晰。"},
        {"role": "user", "content": f"请解释以下 {ext} 代码：\n\n```\n{code}\n```"}
    ]

    with console.status("[bold green]正在分析代码..."):
        explanation = call_deepseek(messages, model=model, max_tokens=8192)

    console.print(Panel(explanation, title="代码解释", border_style="green"))
    return explanation


@cli.command()
@click.option('--file', '-f', required=True, help='要重构的代码文件')
@click.option('--model', '-m', default=None, help='模型名称')
@click.option('--output', '-o', default=None, help='输出文件路径')
def refactor(file, model, output):
    """代码重构建议"""
    if not os.path.exists(file):
        console.print(f"[red]文件不存在: {file}[/red]")
        sys.exit(1)

    with open(file, 'r', encoding='utf-8') as f:
        code = f.read()

    ext = os.path.splitext(file)[1].lstrip('.') or 'text'

    messages = [
        {"role": "system", "content": "你是一位代码重构专家。请分析以下代码，给出重构方案，"
         "包括：1.代码异味识别 2.重构建议 3.重构后的完整代码。用中文回答。"},
        {"role": "user", "content": f"请重构以下 {ext} 代码：\n\n```\n{code}\n```"}
    ]

    with console.status("[bold green]正在分析重构方案..."):
        result = call_deepseek(messages, model=model, max_tokens=8192)

    console.print(Panel(result, title="重构方案", border_style="yellow"))

    if output:
        with open(output, 'w', encoding='utf-8') as f:
            f.write(result)
        console.print(f"[green]重构报告已保存到: {output}[/green]")

    return result


if __name__ == "__main__":
    cli()
