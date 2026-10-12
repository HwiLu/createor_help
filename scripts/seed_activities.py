"""薅羊毛活动 —— 示例数据种子脚本。

说明：
  以下为「示例数据」，用于演示活动列表 / 详情 / 首页精选效果。
  活动名称、奖励、起止时间、参与链接均为示意值，封面图为脚本用
  Pillow 生成的占位纯色图，并非真实可参与的活动。
  如需接入真实活动，请在后台管理面板录入，或替换本脚本数据后重跑。

运行（在项目根目录）：
  python scripts/seed_activities.py
"""

from __future__ import annotations

import io
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from app.db.base import Base  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.models import utcnow  # noqa: E402
from app.models.activity import Activity, ActivityEntry, ActivityPlatform, ActivityType  # noqa: E402
from app.models.enums import ActivityEntryType, ActivityStatus, UserRole, UserStatus  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services import activity_service  # noqa: E402
from app.services.activity_image_service import save_activity_image  # noqa: E402
import app.models  # noqa: F401, E402

# 种子数据专属用户：脚本以此用户为 created_by，重跑时先清理该用户创建的活动
SEED_OPENID = "seed_activity_bot"

# 平台编码 -> 品牌色（封面占位用）
PLATFORM_COLORS = {
    "PDD": (224, 46, 36),      # 拼多多红
    "ALIPAY": (22, 119, 255),  # 支付宝蓝
    "CMB": (196, 18, 48),      # 招商银行红
    "JD": (225, 37, 27),       # 京东红
    "TAOBAO": (255, 80, 0),    # 淘宝橙
    "DOUYIN": (0, 0, 0),       # 抖音黑
    "WECHAT": (7, 193, 96),    # 微信绿
}

# 10 条示例活动。
# 字段：title / platform / atype / summary / content(列表) / start_days / end_days /
#       featured / featured_sort / entry_url
# start_days/end_days 为相对运行时刻的天数偏移，保证任何时间运行都能展示出
# 「进行中 / 即将开始 / 已结束」的完整分布。
SEED_ACTIVITIES = [
    {
        "title": "拼多多砍价免费拿 · 百亿补贴专场",
        "platform": "PDD",
        "atype": "BARGAIN",
        "summary": "邀请好友助力砍价，最低 0 元拿商品，每日可发起一次。",
        "content": [
            "## 活动介绍",
            "在拼多多发起砍价，邀请好友助力，**砍到 0 元即可免费领走商品**。",
            "## 参与方式",
            "- 在拼多多 App 内选择心仪商品发起砍价",
            "- 将助力链接分享给好友，好友点击即完成一次助力",
            "- 新用户助力通常可砍下更高金额",
            "## 注意事项",
            "> 每件商品砍价有 24 小时时效，超时需重新发起；砍价结果以平台最终判定为准。",
        ],
        "start_days": -3,
        "end_days": 7,
        "featured": True,
        "featured_sort": 1,
        "entry_url": "https://www.pinduoduo.com/",
    },
    {
        "title": "支付宝集五福 · 新春集卡领红包",
        "platform": "ALIPAY",
        "atype": "CARD_COLLECTION",
        "summary": "集齐五张福卡即可瓜分现金红包，缺卡可向好友求助或交换。",
        "content": [
            "## 活动介绍",
            "集齐「爱国福、富强福、和谐福、友善福、敬业福」五张福卡，即可参与现金红包瓜分。",
            "## 参与方式",
            "- 每日通过扫福、写福、AR 扫福等任务获得福卡",
            "- 缺卡可向好友求赠，多余福卡可转赠他人",
            "## 奖励说明",
            "红包金额随机，集齐后于活动结束统一开奖，奖励**以实际到账为准**。",
        ],
        "start_days": -5,
        "end_days": 3,
        "featured": True,
        "featured_sort": 2,
        "entry_url": "https://www.alipay.com/",
    },
    {
        "title": "京东拉新 · 邀请好友各得红包",
        "platform": "JD",
        "atype": "INVITE",
        "summary": "邀请新用户下单，邀请人与被邀请人各得无门槛红包。",
        "content": [
            "## 活动介绍",
            "通过邀请链接邀请好友注册并完成首单，双方均可获得无门槛红包奖励。",
            "## 参与方式",
            "- 生成个人专属邀请链接并分享",
            "- 好友通过链接完成注册与首单",
            "- 奖励自动发放至京东账户",
            "## 注意事项",
            "> 邀请奖励按人数阶梯发放，具体金额以活动页面实时规则为准。",
        ],
        "start_days": -1,
        "end_days": 14,
        "featured": True,
        "featured_sort": 3,
        "entry_url": "https://www.jd.com/",
    },
    {
        "title": "招商银行 10 元风暴 · 限时福利",
        "platform": "CMB",
        "atype": "LIMITED_OFFER",
        "summary": "达标消费享 10 元风暴兑好礼，每日限量，先到先得。",
        "content": [
            "## 活动介绍",
            "活动期间累计消费达标，即可兑换优惠券、实物礼品等福利。",
            "## 参与方式",
            "- 使用招商银行信用卡或储蓄卡完成达标消费",
            "- 登录掌上生活 App 领取兑换资格",
            "## 注意事项",
            "> 名额有限，先到先得；部分礼品需额外支付少量现金兑换。",
        ],
        "start_days": -10,
        "end_days": 5,
        "featured": True,
        "featured_sort": 4,
        "entry_url": "https://www.cmbchina.com/",
    },
    {
        "title": "淘宝/天猫 双11 抽奖 · 转盘赢好礼",
        "platform": "TAOBAO",
        "atype": "LOTTERY",
        "summary": "完成浏览/加购任务即可抽奖，红包、优惠券、实物好礼等你拿。",
        "content": [
            "## 活动介绍",
            "活动期间完成指定任务可获得抽奖机会，奖品含红包、优惠券及实物礼品。",
            "## 参与方式",
            "- 在淘宝 App 内完成浏览、收藏、加购等任务",
            "- 每完成一项任务获得一次抽奖机会",
            "- 每日最多可抽 3 次",
            "## 奖励说明",
            "中奖后奖品发放至账户，优惠券自动到账，实物奖品需填写收货地址。",
        ],
        "start_days": -2,
        "end_days": 2,
        "featured": True,
        "featured_sort": 5,
        "entry_url": "https://www.taobao.com/",
    },
    {
        "title": "抖音组队瓜分 · 邀好友一起领流量",
        "platform": "DOUYIN",
        "atype": "TEAM",
        "summary": "组队攒能量，队伍满员即可瓜分流量包与现金奖励。",
        "content": [
            "## 活动介绍",
            "组建或加入战队，通过做任务为队伍攒能量，活动结束按队伍能量瓜分奖励。",
            "## 参与方式",
            "- 创建战队并邀请好友加入",
            "- 队员每日完成任务为队伍贡献能量",
            "- 队伍人数与能量越多，奖励越高",
            "## 注意事项",
            "> 临近截止，请尽快完成今日任务；奖励于活动结束后 3 个工作日内发放。",
        ],
        "start_days": -7,
        "end_days": 1,
        "featured": True,
        "featured_sort": 6,
        "entry_url": "https://www.douyin.com/",
    },
    {
        "title": "微信支付周末摇一摇 · 集卡赢立减金",
        "platform": "WECHAT",
        "atype": "CARD_COLLECTION",
        "summary": "周末消费集卡，集齐指定卡片赢微信支付立减金。",
        "content": [
            "## 活动介绍",
            "活动即将开启：周末使用微信支付消费，可随机获得卡片，集齐即得立减金。",
            "## 参与方式",
            "- 周末通过微信支付完成任意消费",
            "- 每笔消费可获得一张随机卡片",
            "- 集齐一套卡片兑换立减金",
            "## 注意事项",
            "> 活动尚未开始，请关注开启时间；卡片不可交易，仅限本人账户使用。",
        ],
        "start_days": 2,
        "end_days": 12,
        "featured": False,
        "featured_sort": 0,
        "entry_url": "https://pay.weixin.qq.com/",
    },
    {
        "title": "拼多多天天领现金 · 转盘抽奖",
        "platform": "PDD",
        "atype": "LOTTERY",
        "summary": "每日签到抽奖，连续签到奖励翻倍，最高赢现金。",
        "content": [
            "## 活动介绍",
            "活动即将开启：每日签到即可参与转盘抽奖，连续签到天数越多奖励越丰厚。",
            "## 参与方式",
            "- 每日登录拼多多 App 完成签到",
            "- 签到后获得一次抽奖机会",
            "- 连续签到 7 天可额外获得翻倍机会",
            "## 注意事项",
            "> 活动尚未开始，具体规则以活动正式上线页面为准。",
        ],
        "start_days": 1,
        "end_days": 6,
        "featured": False,
        "featured_sort": 0,
        "entry_url": "https://www.pinduoduo.com/",
    },
    {
        "title": "支付宝邀请有礼 · 老带新得红包",
        "platform": "ALIPAY",
        "atype": "INVITE",
        "summary": "邀请好友开通指定服务，双方各得现金红包（已结束）。",
        "content": [
            "## 活动介绍",
            "本活动已结束：邀请好友开通指定服务即可获得现金红包奖励。",
            "## 回顾说明",
            "- 邀请人与被邀请人各得红包",
            "- 奖励实时发放至支付宝余额",
            "## 注意事项",
            "> 该活动已结束，入口已不可参与；请关注平台后续同类活动。",
        ],
        "start_days": -20,
        "end_days": -3,
        "featured": False,
        "featured_sort": 0,
        "entry_url": None,
    },
    {
        "title": "京东砍价 · 好友助力砍好价",
        "platform": "JD",
        "atype": "BARGAIN",
        "summary": "邀请好友助力砍价，砍至目标价即可购买（已结束）。",
        "content": [
            "## 活动介绍",
            "本活动已结束：邀请好友助力，将商品价格砍至目标价即可下单。",
            "## 回顾说明",
            "- 每位好友可为商品砍价一次",
            "- 砍至目标价后 24 小时内下单有效",
            "## 注意事项",
            "> 该活动已结束，入口已不可参与；请关注平台后续同类活动。",
        ],
        "start_days": -15,
        "end_days": -1,
        "featured": False,
        "featured_sort": 0,
        "entry_url": None,
    },
]


def _load_font(size: int) -> ImageFont.ImageFont | ImageFont.FreeTypeFont:
    candidates = [
        "C:/Windows/Fonts/msyh.ttc",       # 微软雅黑 (Windows)
        "C:/Windows/Fonts/msyhbd.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/simsun.ttc",
        "/System/Library/Fonts/PingFang.ttc",          # macOS
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux
    ]
    for path in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:  # noqa: BLE001
                continue
    return ImageFont.load_default()


def _make_cover(title: str, color: tuple[int, int, int]) -> str:
    """生成 800x450 纯色占位封面，居中绘制标题，返回存储 key。"""
    img = Image.new("RGB", (800, 450), color)
    draw = ImageDraw.Draw(img)
    # 顶部浅色装饰条
    draw.rectangle([0, 0, 800, 6], fill=(255, 255, 255))
    font = _load_font(44)
    text = title[:14]
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    draw.text(((800 - w) // 2, (450 - h) // 2), text, fill=(255, 255, 255), font=font)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=88)
    return save_activity_image(buf.getvalue(), "cover.jpg")


def _get_code_map(db, model, key: str = "code") -> dict[str, int]:
    return {getattr(row, key): row.id for row in db.query(model).all()}


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # 1) 幂等初始化平台/类型字典
        activity_service.ensure_activity_dictionaries(db)
        platform_ids = _get_code_map(db, ActivityPlatform)
        type_ids = _get_code_map(db, ActivityType)

        # 2) 种子用户（created_by 外键）
        user = db.query(User).filter(User.wechat_openid == SEED_OPENID).first()
        if user is None:
            user = User(
                wechat_openid=SEED_OPENID,
                nickname="活动示例数据",
                role=UserRole.ADMIN.value,
                status=UserStatus.ACTIVE.value,
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        # 3) 清理旧种子数据（该用户创建的活动及其入口）
        old_ids = [row.id for row in db.query(Activity.id).filter(Activity.created_by == user.id).all()]
        if old_ids:
            db.query(ActivityEntry).filter(ActivityEntry.activity_id.in_(old_ids)).delete(synchronize_session=False)
            db.query(Activity).filter(Activity.id.in_(old_ids)).delete(synchronize_session=False)
            db.commit()

        # 4) 生成示例活动
        now = utcnow()
        created = 0
        for i, item in enumerate(SEED_ACTIVITIES, start=1):
            platform_id = platform_ids[item["platform"]]
            type_id = type_ids[item["atype"]]
            cover_key = _make_cover(item["title"], PLATFORM_COLORS.get(item["platform"], (100, 100, 100)))

            activity = Activity(
                title=item["title"],
                cover_image_key=cover_key,
                platform_id=platform_id,
                activity_type_id=type_id,
                summary=item["summary"],
                content="\n".join(item["content"]),
                start_at=now + timedelta(days=item["start_days"]),
                end_at=now + timedelta(days=item["end_days"]),
                status=ActivityStatus.PUBLISHED.value,
                is_featured=item["featured"],
                featured_sort=item["featured_sort"],
                display_sort=i,
                source_url=item["entry_url"],
                risk_notice="本条目为示例数据，活动规则与奖励以对应平台官方页面实时展示为准，请理性参与、谨防诈骗。",
                created_by=user.id,
            )
            db.add(activity)
            db.flush()  # 拿到 activity.id 供入口使用

            if item["entry_url"]:
                db.add(
                    ActivityEntry(
                        activity_id=activity.id,
                        title="参与入口",
                        entry_type=ActivityEntryType.LINK.value,
                        target_url=item["entry_url"],
                        description="示例入口，跳转至对应平台（正式环境请替换为真实活动链接）。",
                        sort_order=0,
                        is_enabled=True,
                    )
                )
            created += 1

        db.commit()

        total = db.query(Activity).filter(Activity.created_by == user.id).count()
        featured = db.query(Activity).filter(Activity.created_by == user.id, Activity.is_featured.is_(True)).count()
        print(f"[OK] 已生成 {created} 条薅羊毛示例活动（共 {total} 条，其中精选 {featured} 条）。")
        print("     访问 /activities 查看列表，首页查看精选板块。")
    finally:
        db.close()


if __name__ == "__main__":
    main()
