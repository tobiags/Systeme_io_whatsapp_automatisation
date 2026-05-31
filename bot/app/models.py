"""SQLAlchemy models — mirrors the platform DB schema (read/write on same Postgres).

The bot only touches:
  - contacts         (read)
  - campaign_enrollments (read)
  - challenge_editions   (read)
  - score_events         (write: replied_message, asked_question, offer_interest_detected)
  - inbound_messages     (write: audit every inbound + AI reply)
"""
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, JSON, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Contact(Base):
    __tablename__ = "contacts"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    phone: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class CampaignEnrollment(Base):
    __tablename__ = "campaign_enrollments"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    contact_id: Mapped[str] = mapped_column(String(32), index=True)
    campaign_key: Mapped[str] = mapped_column(String(128))
    edition_key: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    current_step: Mapped[str] = mapped_column(String(64))
    cohort: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ChallengeEdition(Base):
    __tablename__ = "challenge_editions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    campaign_key: Mapped[str] = mapped_column(String(128))
    edition_key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    cohort: Mapped[str] = mapped_column(String(16))
    edition_date: Mapped[str] = mapped_column(String(32))
    streamyard_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    day1_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    day2_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    day3_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    payment_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    closer_booking_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class InboundMessage(Base):
    __tablename__ = "inbound_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    phone: Mapped[str] = mapped_column(String(32), index=True)
    contact_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    text: Mapped[str] = mapped_column(String(4096))
    ai_reply: Mapped[str | None] = mapped_column(String(4096), nullable=True)
    needs_human: Mapped[bool] = mapped_column(Boolean, default=False)
    intent: Mapped[str] = mapped_column(String(64), default="default")
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class LearnedKBRule(Base):
    """Mirror of platform learned_kb_rules — bot reads active rules at startup."""
    __tablename__ = "learned_kb_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    intent: Mapped[str] = mapped_column(String(128))
    keywords: Mapped[list] = mapped_column(JSON, default=list)
    suggested_reply: Mapped[str] = mapped_column(String(1024))
    frequency: Mapped[int] = mapped_column(Integer, default=1)
    active: Mapped[bool] = mapped_column(Boolean, default=False)
    needs_human: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ScoreEvent(Base):
    __tablename__ = "score_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    contact_id: Mapped[str] = mapped_column(String(32), index=True)
    event_type: Mapped[str] = mapped_column(String(64))
    points: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
