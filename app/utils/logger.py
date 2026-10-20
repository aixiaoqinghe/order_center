import logging
import os
from datetime import datetime

from app.config import settings

_configured = False


class _Formatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created)
        return dt.strftime("%Y-%m-%d %H:%M:%S,") + f"{int(record.msecs):03d}"


def setup_logging(log_filename: str = "app.log") -> None:
    """
    统一日志配置: 控制台 + 单文件, 幂等(进程内只配一次，传参仅首次生效)。
    log_filename: 落盘文件名, 默认 app.log; 独立进程(如 consumer_dlx)可传自己的。
    """
    global _configured
    if _configured:
        return

    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, log_filename)

    fmt = _Formatter(
        "%(asctime)s %(levelname)s %(name)s [%(lineno)d]: %(message)s"
    )

    root = logging.getLogger()
    root.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))

    # 清理掉可能已存在的 handler, 保证幂等 + 不被 basicConfig 残留干扰
    root.handlers.clear()

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    root.addHandler(console)

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)

    # httpx INFO 噪音治理(known_issues 第 10 条)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    _configured = True