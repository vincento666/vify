# Hify 项目开发规范

## 项目概览

Hify 是一个简化版内部 AI Agent 平台，基于 Dify 思路设计。

- **团队规模**：1 人开发，20-50 人内部使用，本地部署
- **技术栈**：Python 3.12 + FastAPI + SQLAlchemy 2.0 + Alembic + Vue + MySQL 8.x + Redis + PostgreSQL + pgvector
- **架构模式**：模块化单体（Modular Monolith），代码边界清晰，可平滑拆分为微服务

### 后端版本基线

以下版本以 Python 3.12 兼容为硬约束，使用当前稳定兼容的小版本线，升级时只在同一小版本线内滚动，并先跑完整测试。

```toml
[project]
requires-python = ">=3.12,<3.13"
dependencies = [
    "fastapi>=0.136,<0.137",
    "uvicorn[standard]>=0.48,<0.49",
    "pydantic>=2.13,<2.14",
    "pydantic-settings>=2.14,<2.15",
    "sqlalchemy>=2.0,<2.1",
    "alembic>=1.18,<1.19",
    "PyMySQL>=1.2,<1.3",
    "psycopg[binary]>=3.3,<3.4",
    "pgvector>=0.4,<0.5",
    "redis>=8.0,<8.1",
    "httpx>=0.28,<0.29",
    "tenacity>=9.1,<9.2",
    "orjson>=3.11,<3.12",
    "structlog>=25.5,<26",
]

[dependency-groups]
dev = [
    "pytest>=9.0,<9.1",
    "pytest-asyncio>=1.4,<1.5",
    "ruff>=0.15,<0.16",
    "mypy>=2.1,<2.2",
]
```

约束：

- 运行时固定 Python 3.12，不使用 Python 3.13/3.14 才支持的语法或标准库能力。
- MySQL 主库采用 SQLAlchemy 2.0 同步 Session + PyMySQL，优先选择稳定驱动。
- LLM、MCP、外部 HTTP 调用使用 `httpx.AsyncClient`，避免阻塞事件循环。
- PostgreSQL + pgvector 只用于向量存储，使用 `psycopg` 和 `pgvector` Python 包。
- 依赖版本写入 lock file，生产环境严格按 lock file 构建。

### Spec Kit + TDD 迁移门禁

迁移按 Spec Kit 规格推进，规格文件位于 `specs/`。每个 feature spec 拆成若干
vertical slice，必须按 `RED -> GREEN -> REFACTOR` 串行推进。

- 先完成 `000-current-boundary-inventory`，再进入 `001-backend-foundation`。
- `001` 到 `008` 只做当前功能边界换壳复刻，保持 Mock 行为和前端 API 兼容。
- `009` 再把知识库 Mock 替换为真实 pgvector RAG。
- `010` 再实现真实 tool calling 和 MCP 工具执行。
- 每个 slice 必须通过：红测证据、单测、集成/契约测试、E2E、浏览器 UAT、文档更新。
- 一个 slice 未通过全部门禁，不得进入下一个 slice。

门禁细则见 `docs/testing/acceptance-gates.md`。

---

## 核心功能模块（MVP 范围）

| 模块 | 说明 |
|------|------|
| 模型管理 (model) | 管理 OpenAI / Claude / Gemini / Ollama 等 LLM 提供商配置，支持连通性测试 |
| Agent 配置 (agent) | 配置 Agent 名称、系统提示词、绑定模型、关联知识库和 MCP 工具 |
| 对话引擎 (conversation) | 多轮对话、历史记录、SSE 流式响应 |
| 知识库 RAG (knowledge) | 文档上传 -> 异步向量化 -> pgvector 余弦搜索 -> 注入 LLM 上下文 |
| 简版工作流 (workflow) | 顺序节点执行：开始 -> LLM -> 条件分支 -> 工具调用 -> 结束 |
| MCP 工具接入 (mcp) | 接入外部 MCP 工具，供 Agent 和工作流调用 |

**砍掉的功能**：多租户、自定义插件市场、实时协作、企业 SSO、精细化权限控制、数据集版本管理。

---

## 代码组织规范

### 包结构

```text
app/
├── main.py                         # FastAPI 应用入口，注册 lifespan、router、exception handler
├── core/
│   ├── config.py                   # Pydantic Settings，读取环境变量
│   ├── database.py                 # SQLAlchemy engine、SessionLocal、事务工具
│   ├── vector_database.py          # PostgreSQL/pgvector 连接与会话工具
│   ├── errors.py                   # BizError、ErrorCode
│   ├── exception_handlers.py       # FastAPI 全局异常处理
│   ├── responses.py                # Result、PageResult、统一响应模型
│   ├── pagination.py               # 游标分页工具
│   ├── logging.py                  # structlog/logging 配置
│   ├── concurrency.py              # anyio CapacityLimiter、后台任务约束
│   └── circuit_breaker.py          # LLM Provider 熔断状态机
├── modules/
│   ├── model/                      # LLM 提供商管理
│   ├── agent/                      # Agent 配置
│   ├── conversation/               # 对话引擎
│   ├── knowledge/                  # 知识库 RAG
│   ├── workflow/                   # 简版工作流
│   └── mcp/                        # MCP 工具接入
└── tests/
    ├── unit/
    ├── integration/
    └── fixtures/
```

每个业务模块内部保持四层结构：

```text
app/modules/{module}/
├── api/
│   ├── __init__.py
│   ├── facade.py                   # 对其他模块暴露的 Facade/Protocol
│   └── schemas.py                  # 跨模块 DTO，只放稳定契约
├── domain/
│   ├── service.py                  # 业务逻辑与事务编排
│   ├── entities.py                 # 领域对象和值对象
│   └── repository.py               # Repository Protocol
├── infra/
│   ├── orm.py                      # SQLAlchemy ORM Model
│   ├── repository.py               # SQLAlchemy Repository 实现
│   ├── clients.py                  # 外部 API / LLM / MCP 客户端
│   └── tasks.py                    # 后台任务入口
└── web/
    ├── router.py                   # FastAPI APIRouter，只处理 HTTP 层
    └── schemas.py                  # Request / Response 模型
```

### 各层职责边界

| 层 | 职责 | 禁止 |
|----|------|------|
| web/ | 接收请求、依赖注入、Pydantic 校验、调用本模块 api/domain 入口、返回响应 | 直接操作数据库、直接 import 其他模块 domain/infra、写业务规则 |
| api/ | 定义跨模块 Facade/Protocol 和 DTO，作为模块稳定契约 | 包含数据库访问、包含 HTTP 请求对象、泄漏 ORM Model |
| domain/ | 业务逻辑、领域对象、事务边界、调用 Repository Protocol 和其他模块 api | 依赖 FastAPI、依赖 infra 具体实现、直接写 SQL |
| infra/ | SQLAlchemy ORM、Repository 实现、外部客户端、缓存和任务实现 | 包含业务决策、返回 ORM Model 给 web/api 层 |

### 跨模块调用规则

- **只能**通过目标模块的 `api/` Facade 调用，禁止直接 import 其他模块的 `domain/` 或 `infra/`。
- 跨模块传递使用 `api/schemas.py` 下定义的 DTO，不传递 ORM Model 或内部领域对象。
- 循环依赖视为架构错误，立即重构。
- Python 接口使用 `typing.Protocol` 表达契约，具体实现通过依赖工厂或应用装配层注入。

```python
# app/modules/model/api/facade.py
from typing import Protocol

from app.modules.model.api.schemas import ModelConfigDto


class ModelFacade(Protocol):
    def get_model_config(self, model_id: int) -> ModelConfigDto: ...
```

```python
# app/modules/agent/domain/service.py
from app.modules.agent.domain.repository import AgentRepository
from app.modules.model.api.facade import ModelFacade


class AgentService:
    def __init__(self, agent_repo: AgentRepository, model_facade: ModelFacade) -> None:
        self._agent_repo = agent_repo
        self._model_facade = model_facade

    def create_agent(self, command: CreateAgentCommand) -> Agent:
        model_config = self._model_facade.get_model_config(command.model_id)
        agent = Agent.create(command=command, model_config=model_config)
        return self._agent_repo.save(agent)
```

---

## LLM 调用规范

### 并发隔离

LLM 调用不使用全局无界并发。非流式和流式请求必须使用不同的 `anyio.CapacityLimiter`，避免长连接拖垮普通接口。

```python
# app/core/concurrency.py
import anyio

llm_limiter = anyio.CapacityLimiter(50)          # 非流式调用
llm_stream_limiter = anyio.CapacityLimiter(80)   # SSE 流式调用
embedding_limiter = anyio.CapacityLimiter(20)    # 向量化任务
```

- 非流式请求满载时最多等待 3s，超时后返回 503。
- 流式 SSE 请求满载时直接拒绝，由上层返回 503。
- 后台向量化任务必须有独立 limiter，禁止与在线聊天请求抢占同一并发池。

### HTTPX Client 配置

应用启动时在 FastAPI lifespan 中创建长生命周期 `httpx.AsyncClient`，关闭时统一 `aclose()`。

```python
# 非流式：有 read timeout
standard_llm_client = httpx.AsyncClient(
    timeout=httpx.Timeout(connect=5.0, read=120.0, write=30.0, pool=5.0),
    limits=httpx.Limits(max_connections=50, max_keepalive_connections=20),
    http2=True,
)

# 流式：read timeout 设为 None，SSE 不能有固定读超时
stream_llm_client = httpx.AsyncClient(
    timeout=httpx.Timeout(connect=5.0, read=None, write=30.0, pool=5.0),
    limits=httpx.Limits(max_connections=100, max_keepalive_connections=40),
    http2=True,
)
```

### 超时层次（三层保护）

1. HTTPX connect timeout = 5s（TCP/TLS 握手超时）
2. HTTPX read timeout = 120s（单次读取超时，仅非流式）
3. `anyio.fail_after(90)`（总体超时兜底，仅非流式）

```python
import anyio


async def call_llm_with_deadline() -> LlmResponse:
    with anyio.fail_after(90):
        async with llm_limiter:
            return await llm_client.chat(...)
```

### 重试策略（Tenacity）

- 普通 LLM：最多 3 次，初始等待 500ms，指数退避 2x，最大等待 10s。
- Ollama（本地）：最多 5 次，初始等待 2s。
- 仅对网络异常、超时和 5xx 重试，4xx（参数错误、鉴权错误、额度不足）不重试。
- 流式 SSE 已经开始向客户端发送 token 后，不做透明重试，只记录失败事件。

```python
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential


@retry(
    retry=retry_if_exception(is_retryable_llm_error),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=10),
    reraise=True,
)
async def call_standard_llm(request: LlmRequest) -> LlmResponse:
    ...
```

### 熔断器配置

按 provider 维度维护熔断状态，存储在进程内内存；多副本部署时每个副本独立熔断即可，MVP 阶段不引入分布式熔断。

```yaml
# COUNT_BASED 滑动窗口，20 次请求内失败率 >50% 触发熔断
# 慢调用（>30s）超过 80% 也触发熔断
failure_rate_threshold: 50
slow_call_duration_threshold: 30s
slow_call_rate_threshold: 80
wait_duration_in_open_state: 30s
permitted_calls_in_half_open_state: 5
```

### Fallback 路由

```yaml
hify:
  llm:
    fallback:
      openai: ollama
      claude: openai
      gemini: ollama
```

主 Provider 熔断或异常时自动切换 fallback，fallback 失败则抛出 `BizError(ErrorCode.LLM_PROVIDER_UNAVAILABLE)`。

---

## FastAPI 接口规范

### Router 约定

- 每个模块只在 `web/router.py` 暴露 `router = APIRouter(prefix="/agents", tags=["agents"])`。
- 路由函数只做 HTTP 层工作：参数接收、依赖注入、调用 service/facade、状态码和响应模型。
- 不在路由函数中写 SQL、拼接 LLM prompt、编排复杂业务流程。
- 同步 SQLAlchemy Session 对应的普通 CRUD 路由优先写成 `def`，由 FastAPI 线程池承载。
- SSE、WebSocket、LLM streaming 路由写成 `async def`，进入流式阶段前完成必要的短事务读取，流式期间不持有数据库 Session。

```python
router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("", response_model=Result[AgentResponse], status_code=201)
def create_agent(
    request: AgentCreateRequest,
    service: AgentService = Depends(get_agent_service),
) -> Result[AgentResponse]:
    agent = service.create_agent(request.to_command())
    return Result(data=AgentResponse.from_entity(agent))
```

### Pydantic Schema 约定

- Request / Response 模型放在 `web/schemas.py`。
- 跨模块 DTO 放在 `api/schemas.py`。
- 使用 Pydantic v2 写法：`ConfigDict(from_attributes=True)`、`field_validator`、`model_validate()`。
- 字段约束写在类型上，优先使用 `Annotated` 和 `Field`。

```python
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class AgentCreateRequest(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=64)]
    model_id: Annotated[int, Field(gt=0)]
    system_prompt: Annotated[str, Field(min_length=1, max_length=8000)]


class AgentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    model_id: int
```

---

## 部署架构

```text
用户浏览器
    |
    v
Ingress Nginx（L7 负载均衡 + SSL 终止 + SSE 支持）
    |
    |---> hify-frontend（Vue SPA，Nginx 静态文件服务，2 副本）
    |
    `---> hify-backend（FastAPI + Uvicorn，2 副本）
              |
              |---> MySQL 8.x（主数据存储）
              |---> Redis（Session / 缓存 / 限流）
              `---> PostgreSQL + pgvector（向量存储）
```

**Ingress 关键配置（SSE 必须）**：

```yaml
nginx.ingress.kubernetes.io/proxy-read-timeout: "300"
nginx.ingress.kubernetes.io/proxy-buffering: "off"
nginx.ingress.kubernetes.io/limit-rps: "20"
```

**Backend 容器规格**：requests 512Mi/250m，limits 1Gi/1000m，replicas=2

**Uvicorn 启动命令**：

```dockerfile
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers ${WEB_CONCURRENCY:-2} --proxy-headers --forwarded-allow-ips='*'"]
```

约束：

- 每个 worker 都是独立进程，连接池和 limiter 都按进程计算。
- 1 CPU limit 下 `WEB_CONCURRENCY` 默认 1-2，不盲目增加 worker。
- 健康检查暴露 `/healthz`（进程存活）和 `/readyz`（数据库、Redis 基础连通性）。
- Kubernetes 优雅下线时间不少于 30s，确保 SSE 连接和后台任务有机会收尾。

---

## 数据库规范

### MySQL 通用字段约定

每张业务表必须包含以下字段：

```sql
id          BIGINT          NOT NULL AUTO_INCREMENT,
created_at  DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
updated_at  DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
deleted     TINYINT(1)      NOT NULL DEFAULT 0,
PRIMARY KEY (id)
```

SQLAlchemy ORM 基类统一定义这些字段：

```python
from datetime import datetime

from sqlalchemy import BigInteger, text
from sqlalchemy.dialects.mysql import DATETIME, TINYINT
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(
        DATETIME(fsp=3),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP(3)"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DATETIME(fsp=3),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3)"),
    )
    deleted: Mapped[bool] = mapped_column(
        TINYINT(1),
        nullable=False,
        server_default=text("0"),
    )
```

- 字符集：`utf8mb4`，排序规则：`utf8mb4_unicode_ci`。
- 禁用 `VARCHAR` 无长度约束，text 类 content 字段用 `MEDIUMTEXT`。
- 金额用 `DECIMAL(19,4)`，禁止 `FLOAT/DOUBLE`。
- 布尔字段在 Python 中用 `bool`，MySQL 落库用 `TINYINT(1)`。
- 所有 schema 变更必须走 Alembic migration，禁止手工改库后不提交迁移文件。

### SQLAlchemy Session 规范

- Session 生命周期为一次请求或一个后台任务，禁止全局复用 Session。
- `SessionLocal` 使用 `expire_on_commit=False`、`autoflush=False`。
- 事务边界放在 service 层，Repository 不主动 commit。
- Repository 返回领域对象或 DTO，不向 web/api 层泄漏 ORM Model。
- 查询必须使用 SQLAlchemy 2.0 风格 `select()`，禁止遗留 `session.query()`。

```python
with session.begin():
    agent = agent_repo.get_for_update(agent_id)
    agent.rename(new_name)
    agent_repo.save(agent)
```

连接池基线：

```python
engine = create_engine(
    settings.mysql_url,
    pool_size=20,
    max_overflow=10,
    pool_timeout=3,
    pool_recycle=1800,
    pool_pre_ping=True,
)
```

### 索引设计原则

1. **区分度低的字段不单独建索引**（如 `deleted`、`status` 枚举），必须与高区分度字段组合。
2. **组合索引遵循最左前缀**：等值查询字段在左，范围查询字段在右。
3. **查询条件中含 `deleted`**，必须将 `deleted` 纳入索引。
4. **每表索引不超过 5 个**（含主键），写多读少的表控制在 3 个以内。
5. **禁止在 `TEXT/BLOB` 类型字段上建普通索引**，需要时建前缀索引或全文索引。

```sql
-- 正确示例：conversation_id 高区分度在左，deleted 次之，created_at 范围在右
INDEX idx_conv_created (conversation_id, deleted, created_at)
```

### 大表处理策略

判断为大表的阈值：行数 > 500 万 或 数据量 > 2GB

| 场景 | 策略 |
|------|------|
| t_message | 按 conversation_id 分区，或按月归档冷数据 |
| 知识库向量表 | ivfflat 索引，lists = sqrt(行数) |
| 日志类表 | 只保留 90 天，定期 DELETE + OPTIMIZE TABLE |

### 分页查询规范

- **禁止** `LIMIT offset, size` 深分页（offset > 1000 全表扫描）。
- 对话记录类使用**游标分页**：

```sql
SELECT id, role, content, created_at FROM t_message
WHERE conversation_id = ?
  AND deleted = 0
  AND (created_at < ? OR (created_at = ? AND id < ?))
ORDER BY created_at DESC, id DESC
LIMIT 20;
```

- 管理后台必须分页时，用 `WHERE id > last_id LIMIT size` 替代 offset。

### pgvector 索引规范

```sql
-- 余弦相似度索引，lists 值 = sqrt(总行数)，行数 <10 万时 lists=100
CREATE INDEX idx_embedding_ivfflat ON knowledge_embedding
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- 查询时设置 probes，精度和速度平衡
SET ivfflat.probes = 10;
SELECT * FROM knowledge_embedding
ORDER BY embedding <=> '[...]'::vector LIMIT 5;
```

### 索引检测措施

**开发阶段**：SQLAlchemy 事件钩子记录执行时间，超过 10ms 的查询打印 SQL 和参数摘要；疑似全表扫描的关键查询必须手动 EXPLAIN。

**CI 阶段**：关键查询写集成测试，执行 `EXPLAIN`，出现 `type=ALL` 且无合理豁免时测试失败。

**生产阶段**：定期查询 `performance_schema.events_statements_summary_by_digest`，找出 `sum_no_index_used > 0` 的 SQL。

```sql
SELECT digest_text, count_star AS 执行次数, sum_no_index_used AS 未用索引次数
FROM performance_schema.events_statements_summary_by_digest
WHERE sum_no_index_used > 0
ORDER BY sum_no_index_used DESC LIMIT 20;
```

---

## 编码规范（Python + FastAPI）

### 命名

1. **模块名、文件名、函数名、变量名用 snake_case**，类名用 PascalCase，常量用 UPPER_SNAKE_CASE。
2. **禁止用拼音或拼音缩写**命名，禁止单字母变量（循环变量 `i/j/k` 除外）。
3. **函数名体现动词**：查询用 `get/list/query`，修改用 `update`，删除用 `delete/remove`，新增用 `create/add`，布尔返回值用 `is_/has_/can_`。
4. **接口契约用 Protocol 或 Facade 命名**，不使用 `I` 前缀，不使用 `Impl` 后缀；具体实现体现技术细节，如 `SqlAlchemyAgentRepository`。
5. **数据库表名用 `t_` 前缀**，列名用 snake_case；ORM 类不用 `Po` 后缀，Pydantic 模型用 `Dto`/`Request`/`Response` 后缀。
6. **Router 文件固定为 `web/router.py`**，模块对外依赖入口固定为 `api/facade.py`。

### 类型与格式化

7. 所有新代码必须有类型标注，公共函数必须标注返回值。
8. 使用 Ruff 负责 lint 和 format，禁止手工维护不一致的 import 顺序。
9. 使用 mypy 检查核心业务模块，不能为绕过类型错误滥用 `Any` 或 `# type: ignore`。
10. Pydantic v2 模型使用 `model_validate()`、`model_dump()`，禁止使用 v1 风格 `dict()`、`parse_obj()`。

### 异常处理

11. **禁止裸 `except`、空 `except` 和吞异常**，必须记录日志或向上抛出。
12. **业务异常统一抛 `BizError(ErrorCode)`**，不用 `ValueError`/`RuntimeError` 传递业务语义。
13. **只在顶层 FastAPI exception handler 转换 HTTP 响应**，中间层不捕获再包装。
14. `finally` 中不写 `return`，不在 `finally` 中抛出新异常。
15. 返回值优先返回空集合而非 `None`；可空值必须在类型上显式写 `T | None`。

### 日志

16. **使用标准 `logging` + `structlog`**，禁止用 `print()` 输出业务日志。
17. **禁止在循环体内打高频日志**，高频路径只在异常分支或采样后记录。
18. 结构化日志使用键值字段，避免在热路径用 f-string 拼日志。
19. **日志分级约定**：DEBUG=详细调试，INFO=关键业务节点，WARN=可恢复异常或配置缺失，ERROR=需人工介入的故障。生产环境 INFO 级别，日志文件按天滚动，保留 30 天。
20. **LLM 调用必须记录**：provider、model、耗时、token 数、是否命中缓存，便于成本分析。

```python
logger.info(
    "llm_call_finished",
    provider=provider,
    model=model,
    elapsed_ms=elapsed_ms,
    prompt_tokens=prompt_tokens,
    completion_tokens=completion_tokens,
    cache_hit=cache_hit,
)
```

### 并发

21. `async def` 路由中禁止调用阻塞 I/O：不能直接使用同步 HTTP 客户端、`time.sleep()` 或长时间 CPU 计算。
22. 同步 SQLAlchemy Session 不在流式 async 路由中长时间持有；SSE 开始前完成 DB 读取，流式过程中只做异步 I/O。
23. 需要执行阻塞任务时使用 `anyio.to_thread.run_sync()` 或 FastAPI 的线程池能力，并设置并发上限。
24. `asyncio.create_task()` 创建的任务必须被追踪、等待或交给明确的后台任务管理器，禁止无主后台任务。
25. 共享状态必须有锁或封装在单线程任务队列中；请求上下文使用 `contextvars`，不使用全局可变变量保存请求状态。

---

## 性能瓶颈优先级（一期处理清单）

| 级别 | 瓶颈 | 一期处理方式 |
|------|------|-------------|
| P0 | LLM API 延迟高（3-30s） | anyio 并发隔离 + 熔断 + Fallback（已设计） |
| P0 | 向量检索无索引全表扫描 | 建 ivfflat 索引（建表时必须创建） |
| P1 | 对话消息深分页 | 游标分页（禁止 LIMIT offset） |
| P1 | N+1 查询 | SQLAlchemy `selectinload` / 批量查询，禁止循环单查 |
| P2 | 连接池耗尽 | SQLAlchemy pool_size=20，max_overflow=10，pool_timeout=3s |
| 延后 | 静态资源未压缩 | Nginx gzip，流量大时处理 |
| 延后 | Python worker 调优 | 根据 CPU、SSE 连接数和 p95 延迟压测后再调整 |
