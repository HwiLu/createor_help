"""安全初始化管理员：将指定微信用户（或开发 Mock 用户）提升为管理员。

用法：
  python scripts/create_admin.py --openid <wechat_openid>
  python scripts/create_admin.py --mock --openid admin_mock_user
"""
from __future__ import annotations

import argparse

from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.enums import UserRole, UserStatus
from app.models.user import User
import app.models  # noqa: F401


def make_admin(openid: str, nickname: str = "管理员") -> User:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.wechat_openid == openid).first()
        if user is None:
            user = User(
                wechat_openid=openid,
                nickname=nickname,
                role=UserRole.ADMIN.value,
                status=UserStatus.ACTIVE.value,
            )
            db.add(user)
        else:
            user.role = UserRole.ADMIN.value
            if nickname:
                user.nickname = nickname
        db.commit()
        db.refresh(user)
        print(f"管理员已就绪: id={user.id} openid={user.wechat_openid} role={user.role}")
        return user
    finally:
        db.close()


def main() -> None:
    Base.metadata.create_all(bind=engine)
    parser = argparse.ArgumentParser()
    parser.add_argument("--openid", required=True, help="微信 openid（Mock 模式下为任意字符串）")
    parser.add_argument("--nickname", default="管理员")
    args = parser.parse_args()
    make_admin(args.openid, args.nickname)


if __name__ == "__main__":
    main()
