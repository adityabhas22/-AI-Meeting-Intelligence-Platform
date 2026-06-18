"""SQLAlchemy ORM models. One Postgres holds the lot: relational rows for the
transcript and analytics, a pgvector column for semantic search, and a generated
tsvector for keyword search. Segments are the single source of truth for the
transcript; the full labelled text is rebuilt in memory when needed."""

import uuid
from datetime import datetime
from enum import StrEnum

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    Computed,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

EMBED_DIM = 1536


class Base(DeclarativeBase):
    pass


class UUIDMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )


class MeetingStatus(StrEnum):
    uploaded = "uploaded"
    transcribing = "transcribing"
    extracting = "extracting"
    indexing = "indexing"
    done = "done"
    failed = "failed"


class Meeting(UUIDMixin, Base):
    __tablename__ = "meetings"

    title: Mapped[str] = mapped_column(String(500))
    filename: Mapped[str] = mapped_column(String(500))
    audio_uri: Mapped[str | None] = mapped_column(String(1000))  # seam for object storage
    duration_sec: Mapped[float | None] = mapped_column(Float)
    language: Mapped[str | None] = mapped_column(String(20))
    status: Mapped[MeetingStatus] = mapped_column(
        Enum(MeetingStatus, native_enum=False, length=20),
        default=MeetingStatus.uploaded,
        server_default=MeetingStatus.uploaded.value,
    )
    error: Mapped[str | None] = mapped_column(Text)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    speakers: Mapped[list["Speaker"]] = relationship(
        back_populates="meeting", cascade="all, delete-orphan"
    )
    segments: Mapped[list["Segment"]] = relationship(
        back_populates="meeting", cascade="all, delete-orphan", order_by="Segment.idx"
    )
    summary: Mapped["Summary | None"] = relationship(
        back_populates="meeting", cascade="all, delete-orphan", uselist=False
    )
    action_items: Mapped[list["ActionItem"]] = relationship(
        back_populates="meeting", cascade="all, delete-orphan", order_by="ActionItem.idx"
    )
    chunks: Mapped[list["TranscriptChunk"]] = relationship(
        back_populates="meeting", cascade="all, delete-orphan"
    )
    topics: Mapped[list["MeetingTopic"]] = relationship(
        back_populates="meeting", cascade="all, delete-orphan"
    )


class Speaker(UUIDMixin, Base):
    __tablename__ = "speakers"
    __table_args__ = (UniqueConstraint("meeting_id", "label", name="uq_speaker_meeting_label"),)

    meeting_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("meetings.id", ondelete="CASCADE"), index=True
    )
    label: Mapped[int] = mapped_column(Integer)
    display_name: Mapped[str | None] = mapped_column(String(200))

    meeting: Mapped["Meeting"] = relationship(back_populates="speakers")


class Segment(UUIDMixin, Base):
    __tablename__ = "segments"

    meeting_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("meetings.id", ondelete="CASCADE"), index=True
    )
    idx: Mapped[int] = mapped_column(Integer)
    speaker_label: Mapped[int] = mapped_column(Integer)
    start_sec: Mapped[float] = mapped_column(Float)
    end_sec: Mapped[float] = mapped_column(Float)
    text: Mapped[str] = mapped_column(Text)

    meeting: Mapped["Meeting"] = relationship(back_populates="segments")


class Summary(UUIDMixin, Base):
    __tablename__ = "summaries"

    meeting_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("meetings.id", ondelete="CASCADE"), unique=True
    )
    overview: Mapped[str] = mapped_column(Text, default="", server_default="")
    attendees: Mapped[list[str]] = mapped_column(
        JSONB, default=list, server_default=text("'[]'::jsonb")
    )
    key_decisions: Mapped[list[str]] = mapped_column(
        JSONB, default=list, server_default=text("'[]'::jsonb")
    )
    discussion_points: Mapped[list[str]] = mapped_column(
        JSONB, default=list, server_default=text("'[]'::jsonb")
    )
    open_questions: Mapped[list[str]] = mapped_column(
        JSONB, default=list, server_default=text("'[]'::jsonb")
    )
    next_steps: Mapped[list[str]] = mapped_column(
        JSONB, default=list, server_default=text("'[]'::jsonb")
    )

    meeting: Mapped["Meeting"] = relationship(back_populates="summary")


class ActionItem(UUIDMixin, Base):
    __tablename__ = "action_items"

    meeting_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("meetings.id", ondelete="CASCADE"), index=True
    )
    idx: Mapped[int] = mapped_column(Integer)
    task: Mapped[str] = mapped_column(Text)
    owner: Mapped[str | None] = mapped_column(String(200))
    due: Mapped[str | None] = mapped_column(String(200))  # free text: "next Friday" survives
    completed: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    meeting: Mapped["Meeting"] = relationship(back_populates="action_items")


class TranscriptChunk(UUIDMixin, Base):
    __tablename__ = "transcript_chunks"
    __table_args__ = (
        Index(
            "ix_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        Index("ix_chunks_ts", "ts", postgresql_using="gin"),
    )

    meeting_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("meetings.id", ondelete="CASCADE"), index=True
    )
    idx: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    start_sec: Mapped[float] = mapped_column(Float)
    end_sec: Mapped[float] = mapped_column(Float)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBED_DIM))
    ts: Mapped[str | None] = mapped_column(
        TSVECTOR, Computed("to_tsvector('english', text)", persisted=True)
    )

    meeting: Mapped["Meeting"] = relationship(back_populates="chunks")


class MeetingTopic(UUIDMixin, Base):
    __tablename__ = "meeting_topics"

    meeting_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("meetings.id", ondelete="CASCADE"), index=True
    )
    idx: Mapped[int] = mapped_column(Integer)
    topic: Mapped[str] = mapped_column(String(200), index=True)

    meeting: Mapped["Meeting"] = relationship(back_populates="topics")
