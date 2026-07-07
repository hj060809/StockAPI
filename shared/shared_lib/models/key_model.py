from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from shared.shared_lib.models.base import Base

class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # 실제 저장되는 건 해시값 — 평문은 발급 시 딱 한 번만 보여줌
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)

    # 사용자에게 보여주는 식별용 prefix (예: "sk-abc12...")
    key_prefix: Mapped[str] = mapped_column(String(12), nullable=False)

    name: Mapped[str] = mapped_column(String(100), nullable=False)       # 키 별칭 (예: "iOS 앱용")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # None = 무기한
