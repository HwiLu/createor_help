"""轻量进程内限流器（固定窗口 + 线程安全）。

适用于单进程部署（本地开发 / SQLite）。生产多进程部署建议替换为
基于 Redis 的分布式限流，本实现作为无外部依赖的兜底。
"""
from __future__ import annotations

import threading
import time


class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: int) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        """窗口内是否允许本次请求；允许则记录并返回 True。"""
        now = time.monotonic()
        with self._lock:
            hits = [t for t in self._hits.get(key, []) if now - t < self.window_seconds]
            if len(hits) >= self.max_requests:
                self._hits[key] = hits
                return False
            hits.append(now)
            self._hits[key] = hits
            # 防止 key 无限增长导致内存泄漏
            if len(self._hits) > 10000:
                cutoff = now - self.window_seconds
                self._hits = {k: v for k, v in self._hits.items() if v and v[-1] >= cutoff}
            return True


# 登录限流：按 IP 计数，防暴力破解（5 次/分钟）
login_limiter = RateLimiter(max_requests=5, window_seconds=60)
# 发帖限流：按用户计数（5 次/分钟）
post_limiter = RateLimiter(max_requests=5, window_seconds=60)
# 评论/互关申请/回关限流：按用户计数（10 次/分钟）
comment_limiter = RateLimiter(max_requests=10, window_seconds=60)
