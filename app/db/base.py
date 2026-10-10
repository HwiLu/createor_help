"""SQLAlchemy 声明式基类与跨数据库兼容类型。"""
from __future__ import annotations

from sqlalchemy import BigInteger, Integer
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# SQLite 中 BIGINT 主键不会自动自增，因此用 INTEGER 变体兼容；
# MySQL 生产环境仍使用 BIGINT。
BigInt = BigInteger().with_variant(Integer, "sqlite")
