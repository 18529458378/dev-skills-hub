# 代码生成与推理模块

基于 DeepSeek API 的代码生成、审查、推理工具集。

## 功能

- **代码生成**：根据自然语言描述生成多语言代码
- **代码审查**：自动分析代码质量、安全漏洞、性能问题
- **代码推理**：解释代码逻辑、生成文档、重构建议
- **批量处理**：支持目录级别的批量代码审查

## 安装

```bash
pip install -r requirements.txt
```

## 配置

设置环境变量：

```bash
export DEEPSEEK_API_KEY="your-api-key"
export DEEPSEEK_BASE_URL="https://api.deepseek.com"  # 可选，默认官方地址
```

或创建 `.env` 文件：

```
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxx
DEEPSEEK_MODEL=deepseek-coder
```

## 使用

### 1. 代码生成

```bash
python deepseek_code_gen.py --prompt "用Python写一个快速排序函数" --language python
```

### 2. 代码审查

```bash
# 审查单个文件
python code_review.py --file path/to/your/code.py

# 审查整个目录
python code_review.py --dir ./src --output report.md
```

### 3. 代码解释

```bash
python deepseek_code_gen.py --explain --file path/to/code.py
```

## 支持的模型

- `deepseek-coder` - 代码专用模型
- `deepseek-chat` - 通用对话模型
- `deepseek-reasoner` - 推理模型（R1）

## 输出示例

代码审查报告会包含：
- 安全漏洞（SQL注入、XSS、硬编码密钥等）
- 性能问题（时间复杂度、内存泄漏）
- 代码规范（命名、注释、结构）
- 改进建议（带代码示例）
