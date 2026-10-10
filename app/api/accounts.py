from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.creator_account import CreatorAccount
from app.models.enums import CreatorAccountStatus
from app.models.user import User
from app.schemas import AccountCreate, AccountUpdate

router = APIRouter(prefix="/accounts", tags=["accounts"])


def _json(a: CreatorAccount) -> dict:
    return {
        "id": a.id,
        "platform": a.platform,
        "account_name": a.account_name,
        "profile_url": a.profile_url,
        "bio": a.bio,
        "category": a.category,
        "follower_range": a.follower_range,
        "status": a.status,
    }


@router.get("")
def list_accounts(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    accounts = (
        db.query(CreatorAccount)
        .filter(CreatorAccount.user_id == user.id, CreatorAccount.status == CreatorAccountStatus.ACTIVE.value)
        .all()
    )
    return [_json(a) for a in accounts]


@router.post("")
def create_account(data: AccountCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    account = CreatorAccount(
        user_id=user.id,
        platform=data.platform.value,
        account_name=data.account_name.strip(),
        profile_url=data.profile_url,
        bio=data.bio,
        category=data.category,
        follower_range=data.follower_range,
        status=CreatorAccountStatus.ACTIVE.value,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return _json(account)


@router.patch("/{account_id}")
def update_account(
    account_id: int,
    data: AccountUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    account = db.get(CreatorAccount, account_id)
    if account is None or account.user_id != user.id or account.status == CreatorAccountStatus.DELETED.value:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="账号不存在")

    for field in ("platform", "account_name", "profile_url", "bio", "category", "follower_range"):
        val = getattr(data, field, None)
        if val is not None:
            setattr(account, field, val.value if field == "platform" else (val.strip() if isinstance(val, str) else val))
    db.commit()
    db.refresh(account)
    return _json(account)


@router.delete("/{account_id}")
def delete_account(account_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    account = db.get(CreatorAccount, account_id)
    if account is None or account.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="账号不存在")
    account.status = CreatorAccountStatus.DELETED.value
    db.commit()
    return {"ok": True}
