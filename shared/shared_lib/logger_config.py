# logger_config.py
from loguru import logger
import sys

logger.remove()  # 기본 핸들러 제거

# 콘솔 출력 (Docker logs로 확인 가능)
logger.add(
    sys.stdout,
    level="INFO",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | {message}",
)

# 파일 저장 (컨테이너 재시작해도 남음, 볼륨 마운트 시)
logger.add(
    "logs/app.log",
    rotation="1 day",       # 하루마다 새 파일
    retention="7 days",     # 7일 지난 로그 자동 삭제
    level="INFO",
    encoding="utf-8",
)

# 에러만 따로 (문제 생겼을 때 이 파일만 보면 됨)
logger.add(
    "logs/error.log",
    rotation="1 day",
    retention="30 days",
    level="ERROR",
)