"""小红书优秀博主数据采集脚本（半自动 / 学习参考）。

⚠️ 重要说明
────────────
小红书有严格的接口签名（x-s / x-t / x-sign）与登录态校验，并对未授权
抓取进行风控。自动抓取「各板块粉丝 Top10」在技术上需要逆向签名算法并
持续维护登录态，且可能违反平台用户协议与相关法律法规。

因此本脚本**不提供**可稳定运行的自动爬虫，而是提供两条路径：

1. fetch_with_cookie()
   需要你从浏览器手动复制登录后的 Cookie，脚本尝试请求公开搜索接口。
   由于缺少签名，大概率会被拦截并打印提示——仅作技术学习参考。

2. import_from_json(path)
   将你手动整理（或经官方渠道导出）的博主数据从 JSON 导入数据库。
   这条路径稳定可用，是推荐的接入方式。

日常演示请直接使用：python scripts/seed_top_creators.py
"""

import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.base import Base  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.models import TopCreator  # noqa: E402
from app.models.enums import CreatorCategory, Platform  # noqa: E402

SEARCH_URL = "https://www.xiaohongshu.com/search_result"


def fetch_with_cookie(keyword: str, cookie: str) -> None:
    """半自动抓取（学习参考）：尝试用登录 Cookie 请求小红书搜索页。

    小红书接口需要 x-s/x-t 签名，仅凭 Cookie 通常无法通过校验，
    该方法大概率会失败，失败时会打印原因与替代建议。
    """
    url = f"{SEARCH_URL}?keyword={urllib.parse.quote(keyword)}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0 Safari/537.36"
            ),
            "Cookie": cookie,
            "Referer": "https://www.xiaohongshu.com/",
        },
    )
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        print(f"HTTP {resp.status}，返回内容长度 {len(resp.read())} 字节")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")[:200]
        print(f"请求被拦截：HTTP {e.code}")
        print(f"  响应片段：{body!r}")
        print("  原因：小红书接口需要 x-s/x-t 签名与完整登录态，")
        print("       仅凭 Cookie 无法通过校验。")
        print("  建议：改用 import_from_json() 导入手动整理的数据，")
        print("       或运行 seed_top_creators.py 使用示例数据。")


def import_from_json(path: str) -> None:
    """从 JSON 文件导入博主数据（稳定可用）。

    JSON 结构（数组）：
    [
      {
        "category": "美妆",            # 必填：美妆/健身/生活/足球/工作/旅游/游戏
        "username": "程十安an",        # 必填
        "nickname": "程十安",          # 可选
        "follower_count": 12000000,    # 可选，整数
        "avatar_url": "",              # 可选
        "profile_url": "https://...",  # 可选
        "platform": "XIAOHONGSHU"      # 可选，默认小红书
      }
    ]
    """
    label_to_category = {
        v: k.value for k, v in {
            CreatorCategory.BEAUTY: "美妆",
            CreatorCategory.FITNESS: "健身",
            CreatorCategory.LIFESTYLE: "生活",
            CreatorCategory.FOOTBALL: "足球",
            CreatorCategory.WORK: "工作",
            CreatorCategory.TRAVEL: "旅游",
            CreatorCategory.GAMING: "游戏",
        }.items()
    }

    with open(path, "r", encoding="utf-8") as f:
        rows = json.load(f)

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        imported = 0
        for row in rows:
            cat_label = row.get("category", "")
            if cat_label not in label_to_category:
                print(f"跳过未知类目：{row}")
                continue
            creator = TopCreator(
                platform=row.get("platform", Platform.XIAOHONGSHU.value),
                category=label_to_category[cat_label],
                username=row["username"],
                nickname=row.get("nickname"),
                avatar_url=row.get("avatar_url") or None,
                profile_url=row.get("profile_url") or (
                    f"https://www.xiaohongshu.com/search_result?keyword={row['username']}"
                ),
                follower_count=int(row.get("follower_count", 0)),
                follower_display=row.get("follower_display"),
                rank=int(row.get("rank", 0)),
                is_featured=True,
                status="ACTIVE",
            )
            db.add(creator)
            imported += 1
        db.commit()
        print(f"[OK] 已从 {path} 导入 {imported} 位博主。")
    finally:
        db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="小红书博主数据采集（半自动/导入）")
    parser.add_argument("--json", help="从 JSON 文件导入博主数据")
    parser.add_argument("--keyword", help="半自动抓取：搜索关键词")
    parser.add_argument("--cookie", help="半自动抓取：浏览器登录 Cookie")
    args = parser.parse_args()

    if args.json:
        import_from_json(args.json)
    elif args.keyword and args.cookie:
        fetch_with_cookie(args.keyword, args.cookie)
    else:
        parser.print_help()
