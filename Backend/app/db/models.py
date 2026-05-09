"""
ORM models (database table definitions).

These are SQLAlchemy mapped classes — do NOT use them directly in API
responses. Use the Pydantic schemas in app/models.py for that.
"""

from datetime import datetime

from sqlalchemy import DateTime, Float, String, func, Enum
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.enums import PackageStatus


class PackageRecord(Base):
    """Represents a registered warehouse package."""

    __tablename__ = "packages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sku: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False
    )
    sender: Mapped[str] = mapped_column(String(200), nullable=False)
    recipient: Mapped[str] = mapped_column(String(200), nullable=False)
    contents: Mapped[str] = mapped_column(String(500), nullable=False)
    weight_kg: Mapped[float] = mapped_column(Float, nullable=False)
    destination: Mapped[str] = mapped_column(String(200), nullable=False)
    routing_zone: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[PackageStatus] = mapped_column(
        Enum(PackageStatus, native_enum=False, length=50),
        default=PackageStatus.REGISTERED,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<PackageRecord sku={self.sku!r} sender={self.sender!r}>"
