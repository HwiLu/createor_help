# CreatorHub 自媒体互助社区

一个面向中国大陆自媒体创作者的互助社区 Web/H5 应用。创作者可以发布互关/互赞/互评互助帖子，其他创作者评论申请、上传关注证据，发帖人核验证据并回关，申请者确认完成后形成可追溯的诚信记录。

> 本平台**不**自动操作抖音、小红书、B 站、微信等第三方平台的关注行为，也不声称能够自动验证第三方关注关系。所有关注/回关行为均由用户在对应平台自主完成，平台只负责组织流程、记录双方确认状态和维护社区秩序。

---

## 目录

- [核心业务闭环](#核心业务闭环)
- [技术架构](#技术架构)
- [目录结构](#目录结构)
- [本地开发快速开始](#本地开发快速开始)
- [数据库与迁移](#数据库与迁移)
- [微信扫码登录接入](#微信扫码登录接入)
- [管理员初始化](#管理员初始化)
- [自动化测试](#自动化测试)
- [API 接口文档](#api-接口文档)
- [生产部署](#生产部署)
- [安全清单](#安全清单)
- [常见故障排查](#常见故障排查)
- [用户协议与隐私政策](#用户协议与隐私政策)
- [开发阶段说明](#开发阶段说明)

---

## 核心业务闭环

完整可运行的业务闭环：

```
发布互助帖 → 评论申请 → 上传证据 → 发帖人核验 → 发帖人回关 → 申请者确认 → 完成记录
```

互助申请采用严格状态机（见 `app/models/enums.py`）：

| 状态 | 说明 | 允许的后续状态 |
|---|---|---|
| `PENDING_REVIEW` | 待核验证据 | `WAITING_RETURN`、`EVIDENCE_REJECTED`、`CANCELLED` |
| `EVIDENCE_REJECTED` | 证据被拒绝 | `PENDING_REVIEW`、`CANCELLED` |
| `WAITING_RETURN` | 证据已接受，等待回关 | `RETURNED_PENDING_CONFIRMATION`、`DISPUTED` |
| `RETURNED_PENDING_CONFIRMATION` | 已声明回关，待确认 | `COMPLETED`、`DISPUTED` |
| `COMPLETED` | 双方确认完成 | 终态 |
| `DISPUTED` | 争议处理中 | `COMPLETED`、`CANCELLED`（管理员处理） |
| `CANCELLED` | 已取消 | 终态 |

所有状态转换**只能**通过服务层（`app/services/mutual_service.py`）校验，每次转换都写入 `mutual_request_events` 审计事件，普通用户无法通过 API 直接传入任意状态。

---

## 技术架构

- **后端**：Python 3.8+ / FastAPI / SQLAlchemy 2.x / Pydantic v2
- **数据库**：SQLite（本地开发/测试）、MySQL 8（生产，Docker Compose）
- **迁移**：Alembic
- **模板**：Jinja2 + Bootstrap 5（服务端渲染 + 少量 JS，PC/H5 响应式）
- **登录**：微信开放平台网站应用 OAuth 扫码登录 + 显式开启的开发 Mock 登录
- **会话**：`itsdangerous` 签名的 HttpOnly Cookie
- **测试**：pytest + FastAPI TestClient
- **部署**：Docker / Docker Compose（MySQL + App）

项目采用单体架构，业务规则集中在 `app/services/`，API 层只做参数校验、鉴权和调用服务，数据库变更统一走 Alembic 迁移。

---

## 目录结构

```
helpEachother/
├── app/
│   ├── main.py                 # FastAPI 入口、路由挂载、健康检查
│   ├── core/
│   │   ├── config.py           # 配置（读取 .env / 环境变量）
│   │   ├── security.py         # 会话签名、state 生成
│   │   ├── logging.py          # 请求日志中间件
│   │   ├── deps.py             # 当前用户 / 管理员依赖
│   │   └── permissions.py      # 对象级权限辅助
│   ├── db/
│   │   ├── base.py             # 声明式基类、跨库 BigInt 类型
│   │   └── session.py          # engine / Session
│   ├── models/                 # SQLAlchemy 模型（9 张表）
│   ├── schemas/                # Pydantic 请求/响应模型
│   ├── services/               # 业务服务层（状态机、权限、通知、审计等）
│   ├── api/                    # REST 路由（/api/v1）
│   └── web/                    # Jinja2 页面路由
├── templates/                  # 页面模板
├── static/                     # CSS / JS
├── alembic/                    # 数据库迁移
├── scripts/create_admin.py     # 安全初始化管理员
├── tests/                      # 自动化测试
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

---

## 本地开发快速开始

### 1. 环境要求

- Python 3.8 及以上（推荐 3.10+）
- （可选）Docker / Docker Compose

### 2. 安装依赖

```bash
# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
# 复制示例配置
copy .env.example .env        # Windows
# cp .env.example .env        # Linux/macOS
```

本地开发关键配置（`APP_ENV=development`）：

```ini
APP_ENV=development
APP_SECRET_KEY=dev-only-change-me
DATABASE_URL=sqlite:///./creatorhub.db
MOCK_LOGIN_ENABLED=true        # 仅本地开发开启，生产环境强制禁用
```

### 4. 初始化数据库

```bash
python -m alembic upgrade head
```

> 开发模式下应用启动时也会自动 `create_all` 建表（`app/main.py` 的 lifespan），但生产环境请始终使用 Alembic 迁移。

### 5. 启动应用

```bash
uvicorn app.main:app --reload
```

打开 http://localhost:8000 ：

- 首页/互助广场：`/`
- 登录页：`/login`
- 交互式 API 文档：`/docs`
- 健康检查：`/healthz`

### 6. 本地 Mock 登录测试

由于尚未配置微信开放平台，本地可通过登录页底部的「开发 Mock 登录」按钮，或直接访问：

```bash
# 以 Mock 用户 A 登录
curl -X POST "http://localhost:8000/api/v1/auth/mock-login?openid=alice&nickname=Alice" -c cookies.txt
# 以 Mock 用户 B 登录（换一个 Cookie 文件即可模拟两个用户跑完整闭环）
curl -X POST "http://localhost:8000/api/v1/auth/mock-login?openid=bob&nickname=Bob" -c cookies_b.txt
```

Mock 登录**仅**在 `APP_ENV != production` 且 `MOCK_LOGIN_ENABLED=true` 时可用；生产环境即使误设也会被 `mock_login_available` 强制禁用。

---

## 数据库与迁移

### 数据库模型（9 张表）

- `users`：微信用户（openid 唯一索引）
- `creator_accounts`：用户绑定的自媒体账号
- `posts`：互助帖子
- `comments`：评论
- `mutual_requests`：互助申请（含完整状态字段）
- `mutual_request_events`：状态转换审计
- `evidence_files`：证据文件（私有存储）
- `notifications`：站内通知
- `reports`：举报
- `audit_logs`：管理员操作审计

> ID 采用跨库兼容类型 `BigInt = BigInteger().with_variant(Integer, "sqlite")`，SQLite 下使用 `INTEGER`（保证自增），MySQL 下使用 `BIGINT`。

### 常用迁移命令

```bash
# 生成迁移
python -m alembic revision --autogenerate -m "描述"
# 应用迁移
python -m alembic upgrade head
# 回退一步
python -m alembic downgrade -1
# 查看当前版本
python -m alembic current
```

---

## 微信扫码登录接入

本项目使用微信**开放平台网站应用**的 OAuth 2.0 扫码登录（`snsapi_login`），不伪造二维码，也不模拟授权结果。

### 1. 在微信开放平台创建网站应用

1. 登录 [微信开放平台](https://open.weixin.qq.com/)，创建「网站应用」。
2. 提交审核，获取 `AppID` 与 `AppSecret`。
3. 在应用详情中配置**授权回调域**（域名需与 `WECHAT_REDIRECT_URI` 的主机一致）。

### 2. 配置环境变量

```ini
WECHAT_APP_ID=你的AppID
WECHAT_APP_SECRET=你的AppSecret
WECHAT_REDIRECT_URI=https://你的域名/api/v1/auth/wechat/callback
```

> `AppSecret` 只在后端使用，绝不暴露给前端。

### 3. 登录流程

1. 前端调用 `GET /api/v1/auth/wechat/start` 获取带随机 `state` 的授权 URL。
2. 前端用该 URL 生成二维码（登录页已内置 `qrcodejs`）。
3. 用户扫码授权后，微信回调 `GET /api/v1/auth/wechat/callback?code=...&state=...`。
4. 后端校验 `state`（一次性、10 分钟有效），用 `code` 换取 `openid`，查找或创建用户，签发会话 Cookie 后重定向首页。

### 4. 重要说明

- 未配置 `WECHAT_APP_ID` 时，`/api/v1/auth/wechat/start` 返回 503 并提示「微信登录尚未配置」，**不会**静默回退到 Mock。
- PC 端使用扫码登录；微信内 H5 需另外开通「公众号网页授权」并按场景配置，本项目当前默认实现网站应用扫码场景。

---

## 管理员初始化

通过脚本安全提升指定微信用户（或 Mock 用户）为管理员，不硬编码管理员账号：

```bash
# 正式微信用户
python scripts/create_admin.py --openid <wechat_openid> --nickname "管理员"

# 开发 Mock 用户（需先在 Mock 登录中创建该 openid）
python scripts/create_admin.py --openid alice --nickname "管理员"
```

管理员可访问 `/admin` 后台与 `/api/v1/admin/*` 接口；所有关键管理操作都会写入 `audit_logs`。

---

## 自动化测试

```bash
python -m pytest tests -q
```

已覆盖的验收场景包括：

- 未登录不可发布/评论/申请
- 用户可创建多个自媒体账号、不能修改他人账号
- 不能申请自己的帖子
- 已关闭/过期帖子不能申请
- 重复申请被拒绝
- 证据图片校验（伪装格式、错误扩展名、合法 PNG）
- 证据对象级权限（仅申请者/发帖人/管理员可访问）
- 完整闭环：申请 → 上传证据 → 核验通过 → 声明回关 → 确认完成
- 证据拒绝与重新提交
- 争议流程
- 管理员越权与审计

---

## API 接口文档

统一前缀 `/api/v1`，返回 JSON，统一错误结构 `{"detail": "..."}`。

- 交互式文档：启动后访问 `/docs`（Swagger UI）或 `/redoc`。

主要接口：

**登录**
- `GET  /auth/wechat/start`
- `GET  /auth/wechat/callback`
- `GET  /auth/me`
- `POST /auth/logout`
- `POST /auth/mock-login`（仅开发）

**用户与账号**
- `GET  /users/me`、`PATCH /users/me`
- `GET  /users/{user_id}`
- `GET  /accounts`、`POST /accounts`、`PATCH /accounts/{id}`、`DELETE /accounts/{id}`

**帖子**
- `GET  /posts`、`POST /posts`
- `GET  /posts/{id}`、`PATCH /posts/{id}`
- `POST /posts/{id}/close`、`DELETE /posts/{id}`
- `GET  /posts/{id}/comments`、`POST /posts/{id}/comments`

**互助申请**
- `POST /posts/{post_id}/applications`
- `GET  /mutual-requests`、`GET /mutual-requests/{id}`
- `POST /mutual-requests/{id}/cancel`
- `POST /mutual-requests/{id}/review-evidence`
- `POST /mutual-requests/{id}/declare-returned`
- `POST /mutual-requests/{id}/confirm-completion`
- `POST /mutual-requests/{id}/dispute`

**证据**
- `POST /mutual-requests/{id}/evidence`
- `GET  /mutual-requests/{id}/evidence`
- `GET  /evidence/{evidence_id}/file`（对象级权限校验）
- `POST /mutual-requests/{id}/resubmit`

**通知与管理**
- `GET  /notifications`、`POST /notifications/{id}/read`
- `GET  /admin/dashboard`、`GET /admin/reports`
- `POST /admin/reports/{id}/resolve`
- `POST /admin/users/{id}/restrict`、`POST /admin/users/{id}/ban`
- `GET  /admin/users`、`GET /admin/audit-logs`
- `POST /admin/mutual-requests/{id}/resolve`

---

## 生产部署

### 方式一：Docker Compose（推荐）

1. 准备 `.env`（从 `.env.example` 复制），填写真实 `APP_SECRET_KEY`、微信配置，`MOCK_LOGIN_ENABLED=false`。
2. 修改 `docker-compose.yml` 中的 MySQL 密码为强随机值（或改为通过 `.env` 注入）。
3. 构建并启动：

```bash
docker compose up -d --build
```

4. 容器启动时会自动执行 `alembic upgrade head` 再启动应用（见 `Dockerfile`）。
5. 初始化管理员：

```bash
docker compose exec app python scripts/create_admin.py --openid <openid>
```

### 方式二：Linux VPS + Nginx

推荐架构：

```
Nginx(HTTPS 反向代理) → FastAPI(Uvicorn) → MySQL
                                        → 本地私有目录存放证据图片
```

1. 安装 Python 3.10+、MySQL 8，配置 `DATABASE_URL=mysql+pymysql://user:pass@host:3306/creatorhub?charset=utf8mb4`。
2. 执行 `pip install -r requirements.txt`、`alembic upgrade head`。
3. 用 `uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2` 启动（可用 systemd/supervisor 守护）。
4. 配置 Nginx：启用 HTTPS，代理到 `127.0.0.1:8000`。
5. 生产环境必须设置 `SESSION_COOKIE_SECURE=true`、`APP_ENV=production`、`MOCK_LOGIN_ENABLED=false`。

### 备份

- 数据库：定期 `mysqldump` 或使用托管备份。
- 证据图片：备份 `UPLOAD_DIR`（默认 `/app/uploads`）。

> 证据图片目录**不得**作为 Nginx 静态公开目录暴露，只能通过带权限校验的 `/api/v1/evidence/{id}/file` 访问。

---

## 安全清单

- 微信登录：真实 OAuth 回调，`state` 随机/一次性/有效期校验，`AppSecret` 仅后端使用。
- 会话：`itsdangerous` 签名 HttpOnly Cookie；生产启用 `Secure` + `SameSite=Lax`。
- Mock 登录：仅非生产且显式开启，生产强制禁用。
- 状态机：所有互助状态转换经服务层校验并写审计事件。
- 证据权限：仅申请者、发帖人、管理员可访问（对象级校验）。
- 上传：白名单格式（JPEG/PNG/WebP）、文件签名校验、随机存储名、大小/分辨率限制。
- 密钥：全部通过环境变量/`.env` 注入，无硬编码生产密钥。
- 审计：管理员关键操作写入 `audit_logs`，普通用户不可修改。
- 越权：所有资源接口校验属主关系，避免 IDOR。
- 常见 Web 风险：SQLAlchemy 参数化查询防 SQL 注入；Jinja2 默认转义防 XSS；错误响应不暴露堆栈。

> 补充建议（生产上线前）：接入限流（登录/上传/评论/申请/举报）、CSRF 校验（当前 Cookie 使用 `SameSite=Lax` 作为等效缓解）、HTTPS 强制、内容审核与敏感词过滤、用户协议/隐私政策与 ICP 备案按实际部署地区完善。

---

## 常见故障排查

| 现象 | 排查方向 |
|---|---|
| 启动报 `KeyError: 'request_id'` | 日志格式与中间件不一致，已修复；确认使用当前 `app/core/logging.py` |
| SQLite 报 `NOT NULL constraint failed: users.id` | 主键类型未用 `BigInt` 兼容类型；确认模型 ID 使用 `BigInt` 且执行了迁移 |
| Alembic 生成空迁移 | 数据库已存在同结构表；先删除开发库再 `revision --autogenerate` |
| `AttributeError: module 'asyncio' has no attribute 'to_thread'` | Python 3.8 不支持 `asyncio.to_thread`，已改为同步端点在线程池运行 |
| Windows 下 Alembic `UnicodeDecodeError` | `alembic.ini` 中不要使用中文注释（GBK 编码问题） |
| 微信登录 503「尚未配置」 | 未配置 `WECHAT_APP_ID`/`WECHAT_APP_SECRET`，属正常提示，非错误 |
| Mock 登录无效 | 检查 `APP_ENV` 是否为 `production`、`MOCK_LOGIN_ENABLED` 是否为 `true` |
| 证据上传 403 | 上传者必须是该申请的申请者本人 |
| 状态转换 409「非法状态转换」 | 业务顺序不正确，参考状态机表；不能跳过中间状态 |

---

## 用户协议与隐私政策

- 页面：`/agreement`（用户协议）、`/privacy`（隐私政策）
- 模板：`templates/legal.html`，当前为初始占位内容。

正式上线前请根据实际服务内容、部署地区及适用法律法规补充完善，并按需完成 ICP 备案等手续。

---

## 开发阶段说明

| 阶段 | 内容 | 状态 |
|---|---|---|
| 阶段 1 | 项目骨架、SQLAlchemy 模型、Alembic、Docker Compose、Mock 登录 | ✅ |
| 阶段 2 | 微信 OAuth 登录、用户资料、自媒体账号管理 | ✅ |
| 阶段 3 | 互助广场、帖子发布/编辑/关闭、评论与申请 | ✅ |
| 阶段 4 | 证据上传/私有存储、核验、回关、确认、争议、状态日志与通知 | ✅ |
| 阶段 5 | 后台管理、审计日志、生产部署、自动化测试 | ✅ |
