# Word 文档智能审查系统

基于大语言模型（LLM）的 Word 文档智能审查系统。需求文档见 `require.md`（已 gitignore）。

## 核心功能

1. **错别字审查**：错别字、标点误用、多字漏字等
2. **格式审查**：业务人员自定义格式规范（字体/字号/首行缩进/行距/对齐等），逐段比对
3. **专有名词补齐**：词库维护（全称 ↔ 简称），自动补全为规范全称
4. **句意优化**：语句不通、冗余、口语化等改写建议

每条建议支持 **接受 / 拒绝 / 自行修改**，确认后导出修订版 docx（require.md 3.2）。

## 技术栈

- 后端：FastAPI + Uvicorn + LangChain
- 数据库：SQLAlchemy 2.0 + Alembic（开发 SQLite → 生产 PostgreSQL，仅改连接串，见 require.md 5.5）
- 运行环境：uv + Python 3.14（.venv）
- 文档处理：python-docx

## 快速开始

```bash
# 1. 安装依赖（已装好可跳过）
uv pip install -r requirements.txt --python .venv/bin/python

# 2. 初始化数据库（建表）
cp .env.example .env          # 按需修改配置
.venv/bin/alembic upgrade head

# 3. 启动服务（mock 模式，无需 API Key 即可体验全流程）
.venv/bin/uvicorn app.main:app --reload --port 8000

# 4. 访问
# 接口文档：http://127.0.0.1:8000/docs
# 健康检查：http://127.0.0.1:8000/health
```

首次启动自动写入默认格式规范模板与内置专有名词（幂等）。

## 接入真实 LLM

当前已配置 **DeepSeek**（`.env` 中 `LLM_PROVIDER=deepseek` + API Key 已填入），默认即走真实模型。

如需切换：

```bash
LLM_PROVIDER=deepseek        # deepseek | openai | tongyi | ollama | mock
DEEPSEEK_API_KEY=sk-xxx      # 对应 provider 的密钥
```

未配置密钥时自动降级为 mock 模式（内置规则引擎），流程不中断。

> 说明：DeepSeek 等 OpenAI 兼容 API 不支持 `response_format=json_schema`，
> 代码中已显式使用 `with_structured_output(..., method="function_calling")` 获取结构化输出。

## 演示与测试

```bash
# 生成带典型问题的示例文档 + 全流程冒烟测试（上传→审查→处理→导出）
.venv/bin/python -m app.scripts.smoke_test                 # 按 .env 配置走 DeepSeek
LLM_PROVIDER=mock .venv/bin/python -m app.scripts.smoke_test  # 强制 mock（确定性强断言）
```

## 项目结构

```
app/
├── main.py                 # FastAPI 入口（CORS、生命周期、路由挂载）
├── core/                   # 配置（config.py）、数据库（database.py）
├── models/                 # 7 张表 ORM 模型
├── schemas/                # Pydantic 请求/响应模型
├── api/v1/                 # 路由：documents/templates/terms/tasks/suggestions
├── services/
│   ├── docx_parser.py      # docx 解析（文本 + 样式信息）
│   ├── docx_applier.py     # 导出修订版 docx
│   ├── chunker.py          # 长文本分块
│   └── review/             # LangChain 审查链 + 编排器
│       ├── provider.py     # 模型工厂（多供应商可切换）
│       ├── typo_chain.py   # 错别字链
│       ├── format_chain.py # 格式链（确定性规则引擎）
│       ├── term_chain.py   # 专有名词链（词库匹配）
│       ├── polish_chain.py # 句意优化链
│       └── orchestrator.py # 审查任务编排
└── scripts/                # seed / make_sample_docx / smoke_test
alembic/                    # 数据库迁移
data/                       # sqlite、上传、导出（gitignore）
```

## 关键接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/documents/upload | 上传 docx（可指定规范模板） |
| GET | /api/v1/documents/{id}/preview | 预览文档内容（结构化段落文本+格式信息） |
| POST | /api/v1/tasks | 创建审查任务（选类型，后台异步执行） |
| GET | /api/v1/tasks/{id} | 任务状态与进度 |
| GET | /api/v1/suggestions?task_id= | 建议清单（可筛类型/状态） |
| PATCH | /api/v1/suggestions/{id} | 接受/拒绝/自行修改 |
| POST | /api/v1/suggestions/batch | 批量处理 |
| POST | /api/v1/tasks/{id}/export | 导出修订版 docx |
| CRUD | /api/v1/templates、/api/v1/terms | 规范模板与专有名词库 |
