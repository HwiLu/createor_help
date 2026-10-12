# CreatorHub 自媒体互助社区

一个面向中国大陆自媒体创作者的互助社区 Web/H5 应用。创作者可以发布互关/互赞/互评互助帖子，其他创作者评论申请、上传关注证据，发帖人核验证据并回关，申请者确认完成后形成可追溯的诚信记录。

> 本平台**不**自动操作抖音、小红书、B 站、微信等第三方平台的关注行为，也不声称能够自动验证第三方关注关系。所有关注/回关行为均由用户在对应平台自主完成，平台只负责组织流程、记录双方确认状态和维护社区秩序。

---

## 目录

- [核心业务闭环](#核心业务闭环)
- [薅羊毛活动社区](#薅羊毛活动社区)
- [意见反馈与邮件通知](#意见反馈与邮件通知)
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

## 薅羊毛活动社区

面向用户的公开活动展示与互动社区，覆盖邀请助力、拼人头、组队、集卡类活动。

### 功能要点

- **首页精选板块**：首页展示 4–6 个可配置精选活动（仅已发布且未软删除），提供「查看更多」入口。
- **活动列表页**（`/activities`）：按平台、类型、展示状态筛选，关键字搜索，按发布时间/截止时间排序，分页展示。
- **活动详情页**（`/activities/{id}`）：封面、富文本详情、参与入口（二维码/链接）、来源链接、风险提示/免责声明、评论区。
- **评论与举报**：登录用户可发表一级评论与一层回复，可对评论/回复举报；公开接口只返回已审核评论，评论数来自真实记录。
- **可配置字典**：活动平台（`ActivityPlatform`）与活动类型（`ActivityType`）为后台维护字典，不硬编码；启动时幂等初始化预设项。

### 状态双轨制（防状态造假）

- **管理状态** `status`：`DRAFT`（草稿）/ `PUBLISHED`（发布）/ `OFFLINE`（下架）。
- **展示态** `display_status`：由 `status + start_at + end_at` 实时计算为 `ONGOING` / `UPCOMING` / `ENDED`，不在数据库存储展示态，已结束活动绝不可能显示为进行中。
- 约束：`end_at` 早于 `start_at` 禁止保存；精选仅对已发布活动生效；下架/删除/未发布活动不进入首页与公开列表。

### 参与入口如实展示

参与入口支持 `QR_IMAGE`（二维码图片）与 `LINK`（跳转链接）两种类型。二维码未配置、已过期、被禁用或图片加载失败时，页面如实显示禁用态/提示，**不伪造可用状态**。

---

## 意见反馈与邮件通知

用户意见反馈与「新活动提交」入口，写入数据库并通过 SMTP 邮件通知管理员。

### 功能要点

- **反馈分类**：`FeedbackCategory` 可配置字典，含「功能建议」「问题反馈」「新活动提交」等预设项。
- **新活动提交**（方式 A）：选择该分类后动态展开活动名称、平台、活动介绍、官方链接、群入口线索、截止时间、推荐理由等字段，校验后存入 `extra_data`（JSON）。
- **状态流转**：`PENDING` → `PROCESSING` → `RESOLVED` / `REJECTED`，记录处理人、处理时间与管理员备注；终态不可再流转。
- **邮件通知解耦**：反馈提交先写库，数据库成功才提示「反馈已保存」；邮件发送失败**不回滚反馈**，如实提示「邮件通知失败」，管理员可在后台重试。

### 邮件可靠性与安全

- 使用 Python 标准库 `smtplib` 发送；SMTP 密码仅从环境变量读取，**不入源码、不入数据库、不返回前端**。
- 每次发送写入 `email_delivery_logs`，记录状态（`PENDING`/`SENT`/`FAILED`）、尝试次数、最后错误、发送时间。
- `system_settings` 表保存反馈接收邮箱、邮件开关、主题前缀等**非敏感**配置；邮件开关默认关闭，避免未配置 SMTP 时误报成功。
- 重试受 `MAX_EMAIL_RETRY` 上限约束，重试前校验邮件开关与接收邮箱配置。
- 反馈提交接口按用户做轻量频率限制（默认 30 秒），防止刷接口。

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
│   ├── models/                 # SQLAlchemy 模型（用户/互助/活动/评论/反馈/邮件日志/系统设置等）
│   ├── schemas/                # Pydantic 请求/响应模型
│   ├── services/               # 业务服务层（状态机、活动、Markdown、反馈、邮件、审计等）
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

### 数据库模型

**互助核心（原 10 张表）**

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

**薅羊毛活动（新增 6 张表）**

- `activities`：活动主表（软删除 `deleted_at`）
- `activity_platforms`：活动平台字典
- `activity_types`：活动类型字典
- `activity_entries`：参与入口（二维码/链接）
- `activity_comments`：活动评论（一层回复，软删除）
- `activity_reports`：活动评论举报

**意见反馈与邮件（新增 4 张表）**

- `feedbacks`：反馈主表（`extra_data` JSON）
- `feedback_categories`：反馈分类字典
- `email_delivery_logs`：邮件投递日志
- `system_settings`：key/value 非敏感配置表

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

**互助核心**
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

**薅羊毛活动**
- 非管理员不可访问后台活动管理接口
- 草稿不进入公开列表、发布后可见、展示态按起止时间实时计算（进行中/即将开始/已结束）
- `end_at` 早于 `start_at` 禁止保存
- 评论/一层回复/举报/评论审核（隐藏后公开列表不再返回）

**意见反馈与邮件**
- 反馈提交与 `extra_data` 校验（新活动提交缺必填字段返回 400）
- 反馈提交频率限制（30 秒内重复提交返回 429）
- 后台反馈状态流转（终态不可再流转）
- 系统设置读写与白名单校验（敏感项不可通过后台写入）
- 邮件发送成功/失败投递日志、失败不回滚反馈、邮件重试（关闭开关时重试返回 400）

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

**活动（公开）**
- `GET  /activities`（筛选/搜索/分页）
- `GET  /activities/{id}`（详情，含展示态计算）
- `GET  /activities/{id}/comments`、`POST /activities/{id}/comments`
- `POST /activities/{id}/comments/{comment_id}/reports`
- `GET  /activity-images/{id}`（活动入口二维码读取）

**意见反馈（公开）**
- `GET  /feedback/categories`
- `POST /feedback`（提交反馈，含「新活动提交」动态字段校验）

**活动管理（后台）**
- `GET/POST /admin/activities`、`GET/PATCH/DELETE /admin/activities/{id}`
- `POST /admin/activities/{id}/publish`、`/offline`、`/feature`、`/unfeature`
- `GET/POST /admin/activity-platforms`、`PATCH/DELETE /admin/activity-platforms/{id}`
- `GET/POST /admin/activity-types`、`PATCH/DELETE /admin/activity-types/{id}`
- `GET/POST /admin/activities/{id}/entries`、`PATCH/DELETE /admin/activity-entries/{id}`
- `GET /admin/activity-comments`、`POST /admin/activity-comments/{id}/moderate`
- `GET /admin/activity-reports`、`POST /admin/activity-reports/{id}/resolve`

**反馈管理与系统设置（后台）**
- `GET  /admin/feedback`、`POST /admin/feedback/{id}/status`
- `GET  /admin/email-logs`、`POST /admin/email-logs/{id}/retry`
- `GET  /admin/settings`、`POST /admin/settings`（仅限非敏感白名单项）

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
2. 如需意见反馈邮件通知，填写 `SMTP_HOST`/`SMTP_USERNAME`/`SMTP_PASSWORD`/`SMTP_FROM_EMAIL`；反馈接收邮箱与邮件开关可在后台「系统设置」配置，或直接留空邮件功能（默认关闭，不误报成功）。
3. 修改 `docker-compose.yml` 中的 MySQL 密码为强随机值（或改为通过 `.env` 注入）。
4. 构建并启动：

```bash
docker compose up -d --build
```

5. 容器启动时会自动执行 `alembic upgrade head` 再启动应用（见 `Dockerfile`）。
6. 初始化管理员：

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
- SMTP：密码仅从环境变量读取，不入源码/数据库/前端；后台系统设置仅开放非敏感白名单项。
- 审计：管理员关键操作写入 `audit_logs`，普通用户不可修改。
- 越权：所有资源接口校验属主关系，避免 IDOR。
- 活动：展示态由服务层实时计算，防状态造假；后台活动写操作全部写审计。
- Markdown：受限安全子集渲染，先 HTML 转义再渲染，链接强制 `rel=nofollow`，阻断脚本注入。
- 反馈：提交按用户做频率限制；邮件发送失败不回滚反馈，如实区分「已保存」与「邮件通知失败」。
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
| 反馈提交后提示「邮件通知失败」 | 属正常如实提示：反馈已保存，但 SMTP 未配置或发送失败；到后台「邮件日志」查看 `last_error` 并手动重试 |
| 邮件重试返回 400「开关已关闭」 | 先在后台「系统设置」开启「邮件通知」并配置接收邮箱，再重试 |
| 邮件始终 `FAILED` 且提示 SMTP 未配置 | 检查 `.env` 的 `SMTP_HOST`/`SMTP_USERNAME` 是否已填（密码只从环境变量读取） |
| 反馈提交 429「过于频繁」 | 触发反馈频率限制（默认 30 秒），属预期防护，稍后重试 |
| 后台「系统设置」无法写入 `SMTP_PASSWORD` | 属预期：敏感项仅通过环境变量注入，后台仅开放非敏感白名单项 |

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
| 阶段 6 | 薅羊毛活动社区、活动评论举报、意见反馈、邮件通知与系统设置 | ✅ |
