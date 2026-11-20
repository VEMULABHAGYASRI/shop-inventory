from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models._common import utcnow


class LoginSession(Base):
    """One logged-in browser. Deleting the row logs that browser out."""

    __tablename__ = "login_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    # A fingerprint (SHA-256) of the token, never the token itself: someone
    # who gets a copy of the database file still can't log in with it.
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    expires_at: Mapped[datetime]

    user = relationship("User")
