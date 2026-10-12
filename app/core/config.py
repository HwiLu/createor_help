"""应用配置：从环境变量 / .env 读取，禁止硬编码密钥。"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_ENV: str = "development"
    APP_NAME: str = "CreatorHub"
    APP_SECRET_KEY: str = "change-me-to-a-long-random-string"

    DATABASE_URL: str = "sqlite:///./creatorhub.db"

    WECHAT_APP_ID: str = ""
    WECHAT_APP_SECRET: str = ""
    WECHAT_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/wechat/callback"

    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE: int = 5 * 1024 * 1024  # 5 MB

    SESSION_COOKIE_SECURE: bool = False
    SESSION_COOKIE_SAMESITE: str = "lax"
    SESSION_COOKIE_NAME: str = "creatorhub_session"

    MOCK_LOGIN_ENABLED: bool = False

    # 管理员账号密码登录（管理后台入口）
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin"

    # SMTP 邮件发送（密码只从环境变量读取，绝不写入源码/前端/数据库）
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_USE_TLS: bool = True
    SMTP_FROM_EMAIL: str = ""

    # 业务默认值（管理员可在后台配置，此处为初始默认）
    MAX_EVIDENCE_RESUBMIT: int = 2
    MAX_EVIDENCE_FILES: int = 3
    CONFIRM_TIMEOUT_DAYS: int = 7

    # 薅羊毛模块默认值
    HOME_FEATURED_ACTIVITIES: int = 6  # 首页精选活动展示数量
    MAX_EMAIL_RETRY: int = 3  # 邮件单次重试上限
    FEEDBACK_RATE_LIMIT_SECONDS: int = 30  # 反馈提交最小间隔（秒）

    @property
    def smtp_configured(self) -> bool:
        """SMTP 是否已配置（用于如实判断邮件是否可发送）。"""
        return bool(self.SMTP_HOST and self.SMTP_USERNAME)

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def is_test(self) -> bool:
        return self.APP_ENV == "test"

    @property
    def mock_login_available(self) -> bool:
        """Mock 登录仅在非生产环境且显式开启时可用。"""
        return (not self.is_production) and self.MOCK_LOGIN_ENABLED

    @property
    def admin_password_login_available(self) -> bool:
        """账号密码登录：非生产环境始终可用；生产环境禁止使用默认弱密码。"""
        if self.is_production and self.ADMIN_PASSWORD == "admin":
            return False
        return True

    @property
    def wechat_configured(self) -> bool:
        return bool(self.WECHAT_APP_ID and self.WECHAT_APP_SECRET)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
