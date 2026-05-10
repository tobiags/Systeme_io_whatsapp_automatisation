from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from shared.db.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Contact(Base):
    __tablename__ = "contacts"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    phone: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Consent(Base):
    __tablename__ = "consents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    contact_id: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(32))
    proof_source: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    contact_id: Mapped[str] = mapped_column(String(32), index=True)
    template_key: Mapped[str] = mapped_column(String(128))
    variables: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(32), default="queued")
    provider: Mapped[str] = mapped_column(String(64), default="mock")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ChallengeEdition(Base):
    """One occurrence of the Challenge Amazon FBA (bi-monthly, 3-day event).

    Each live day has its own StreamYard registration URL (day1_url / day2_url /
    day3_url).  `streamyard_url` is kept for backward-compatibility and used as
    a fallback when the per-day URL is not set.
    """
    __tablename__ = "challenge_editions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    campaign_key: Mapped[str] = mapped_column(String(128))
    edition_key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    cohort: Mapped[str] = mapped_column(String(16))           # EU | US-CA
    edition_date: Mapped[str] = mapped_column(String(32))     # "2026-05-07"
    streamyard_url: Mapped[str | None] = mapped_column(String(512), nullable=True)  # fallback
    day1_url: Mapped[str | None] = mapped_column(String(512), nullable=True)  # Jour 1 inscription
    day2_url: Mapped[str | None] = mapped_column(String(512), nullable=True)  # Jour 2 inscription
    day3_url: Mapped[str | None] = mapped_column(String(512), nullable=True)  # Jour 3 inscription
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


class Score(Base):
    __tablename__ = "scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    contact_id: Mapped[str] = mapped_column(String(32), index=True)
    events: Mapped[list] = mapped_column(JSON, default=list)
    score: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


# Running total score per contact (upserted on each event)
class ContactScore(Base):
    __tablename__ = "contact_scores"
    __table_args__ = (UniqueConstraint("contact_id", name="uq_contact_scores_contact_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    contact_id: Mapped[str] = mapped_column(String(32), index=True)
    total_score: Mapped[int] = mapped_column(Integer, default=0)
    last_updated: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


# Individual engagement events (immutable log)
class ScoreEvent(Base):
    __tablename__ = "score_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    contact_id: Mapped[str] = mapped_column(String(32), index=True)
    event_type: Mapped[str] = mapped_column(String(64))
    points: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Segment(Base):
    __tablename__ = "segments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    contact_id: Mapped[str] = mapped_column(String(32), index=True)
    segment: Mapped[str] = mapped_column(String(32))
    score: Mapped[int] = mapped_column(Integer)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), index=True)
    aggregate_id: Mapped[str] = mapped_column(String(128), index=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    version: Mapped[int] = mapped_column(Integer, default=1)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class LabEvaluation(Base):
    __tablename__ = "lab_evaluations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    candidate_id: Mapped[str] = mapped_column(String(128))
    candidate_type: Mapped[str] = mapped_column(String(64))
    score: Mapped[float] = mapped_column(Float)
    recommended: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(32), default="pending_human_review")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


# Inbound WhatsApp messages (from contacts via Wati)
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
