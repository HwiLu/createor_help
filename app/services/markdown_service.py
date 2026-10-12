"""受限安全 Markdown 渲染。

仅支持一个安全子集（标题、列表、引用、粗体、斜体、链接、段落换行）。
实现策略：先整体 HTML 转义，再做块级/行内替换；链接只允许 http/https，
并强制 rel="nofollow noopener" + target="_blank"，杜绝 XSS 与脚本注入。
"""
from __future__ import annotations

import html
import re
from urllib.parse import urlparse

_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
_BOLD_RE = re.compile(r"\*\*([^*]+)\*\*")
_ITALIC_RE = re.compile(r"(?<!\*)\*([^*]+)\*(?!\*)")


def _safe_url(url: str) -> str | None:
    scheme = urlparse(url.strip()).scheme.lower()
    if scheme in ("http", "https"):
        return url.strip()
    return None


def _safe_image_url(url: str) -> str | None:
    """图片地址：允许 http/https 外链，以及站内相对路径（如 /api/v1/activity-images/xxx）。"""
    u = url.strip()
    if u.startswith("/") and not u.startswith("//"):
        return u
    return _safe_url(u)


def _render_inline(text: str) -> str:
    """在已转义的文本上处理行内图片、链接、粗体、斜体。"""
    def _img_sub(match: re.Match) -> str:
        alt = match.group(1)
        url = _safe_image_url(match.group(2))
        if url is None:
            return match.group(0)
        return (
            f'<img src="{html.escape(url, quote=True)}" '
            f'alt="{html.escape(alt, quote=True)}" loading="lazy">'
        )

    def _link_sub(match: re.Match) -> str:
        label = match.group(1)
        url = _safe_url(match.group(2))
        if url is None:
            return match.group(0)
        return (
            f'<a href="{html.escape(url, quote=True)}" '
            f'target="_blank" rel="nofollow noopener">{label}</a>'
        )

    # 先处理图片，避免其 `[]()` 部分被链接规则吞掉
    text = _IMAGE_RE.sub(_img_sub, text)
    text = _LINK_RE.sub(_link_sub, text)
    text = _BOLD_RE.sub(r"<strong>\1</strong>", text)
    text = _ITALIC_RE.sub(r"<em>\1</em>", text)
    return text


def render_markdown(markdown: str | None) -> str:
    """把受限 Markdown 文本渲染为安全 HTML 片段（不含 <p> 包裹的外层）。"""
    if not markdown:
        return ""

    escaped = html.escape(markdown, quote=False)
    lines = escaped.split("\n")
    out: list[str] = []
    in_ul = False

    def close_ul() -> None:
        nonlocal in_ul
        if in_ul:
            out.append("</ul>")
            in_ul = False

    for raw in lines:
        line = raw.rstrip()
        # 空行结束列表
        if not line.strip():
            close_ul()
            continue

        # 无序列表项
        if line.lstrip().startswith(("- ", "* ")):
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            content = line.lstrip()[2:]
            out.append(f"<li>{_render_inline(content)}</li>")
            continue

        close_ul()

        # 标题（# / ## / ###）
        if line.startswith("### "):
            out.append(f"<h5>{_render_inline(line[4:])}</h5>")
            continue
        if line.startswith("## "):
            out.append(f"<h4>{_render_inline(line[3:])}</h4>")
            continue
        if line.startswith("# "):
            out.append(f"<h3>{_render_inline(line[2:])}</h3>")
            continue

        # 引用
        if line.startswith("> "):
            out.append(f"<blockquote>{_render_inline(line[2:])}</blockquote>")
            continue

        # 普通段落
        out.append(f"<p>{_render_inline(line)}</p>")

    close_ul()
    return "\n".join(out)
