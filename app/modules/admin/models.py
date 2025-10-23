
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, BigInteger, ForeignKey, DateTime
from datetime import datetime, timedelta, timezone
from app.db.base import Base, TimestampMixin

class InviteToken(Base, TimestampMixin):
    __tablename__ = "invite_tokens"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    email_hint: Mapped[str | None] = mapped_column(String(200), nullable=True, index=True)
    mentor_name_hint: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_by_user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc) + timedelta(days=7))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    used_by_user_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
