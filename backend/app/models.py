from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True); email: Mapped[str] = mapped_column(String(255), unique=True, index=True); password_hash: Mapped[str] = mapped_column(String(255)); created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
class Video(Base):
    __tablename__ = "videos"
    id: Mapped[int] = mapped_column(primary_key=True); owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True); filename: Mapped[str] = mapped_column(String(255)); stored_path: Mapped[str] = mapped_column(String(500)); duration: Mapped[float] = mapped_column(Float, default=0); fps: Mapped[float] = mapped_column(Float, default=0); width: Mapped[int] = mapped_column(Integer, default=0); height: Mapped[int] = mapped_column(Integer, default=0); created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
class ProcessingJob(Base):
    __tablename__ = "processing_jobs"
    id: Mapped[int] = mapped_column(primary_key=True); video_id: Mapped[int] = mapped_column(ForeignKey("videos.id"), index=True); status: Mapped[str] = mapped_column(String(40), default="queued"); stage: Mapped[str] = mapped_column(String(80), default="queued"); progress: Mapped[float] = mapped_column(Float, default=0); detail: Mapped[str] = mapped_column(Text, default=""); error: Mapped[str | None] = mapped_column(Text, nullable=True); created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow); completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
class Frame(Base):
    __tablename__ = "frames"; __table_args__ = (UniqueConstraint("video_id", "frame_number"),)
    id: Mapped[int] = mapped_column(primary_key=True); video_id: Mapped[int] = mapped_column(ForeignKey("videos.id"), index=True); frame_number: Mapped[int] = mapped_column(Integer); timestamp: Mapped[float] = mapped_column(Float, index=True); image_path: Mapped[str] = mapped_column(String(500))
class Detection(Base):
    __tablename__ = "detections"; __table_args__ = (UniqueConstraint("frame_id", "track_id"),)
    id: Mapped[int] = mapped_column(primary_key=True); frame_id: Mapped[int] = mapped_column(ForeignKey("frames.id"), index=True); video_id: Mapped[int] = mapped_column(ForeignKey("videos.id"), index=True); track_id: Mapped[int] = mapped_column(Integer, index=True); label: Mapped[str] = mapped_column(String(80)); confidence: Mapped[float] = mapped_column(Float); x1: Mapped[float] = mapped_column(Float); y1: Mapped[float] = mapped_column(Float); x2: Mapped[float] = mapped_column(Float); y2: Mapped[float] = mapped_column(Float)
class Track(Base):
    __tablename__ = "tracks"; __table_args__ = (UniqueConstraint("video_id", "track_id"),)
    id: Mapped[int] = mapped_column(primary_key=True); video_id: Mapped[int] = mapped_column(ForeignKey("videos.id"), index=True); track_id: Mapped[int] = mapped_column(Integer, index=True); first_timestamp: Mapped[float] = mapped_column(Float); last_timestamp: Mapped[float] = mapped_column(Float); detection_count: Mapped[int] = mapped_column(Integer, default=0)
class PersonAttribute(Base):
    __tablename__ = "person_attributes"
    id: Mapped[int] = mapped_column(primary_key=True); video_id: Mapped[int] = mapped_column(ForeignKey("videos.id"), index=True); track_id: Mapped[int] = mapped_column(Integer, index=True); gender: Mapped[str] = mapped_column(String(30), default="unknown", index=True); upper_type: Mapped[str] = mapped_column(String(50), default="unknown"); upper_color: Mapped[str] = mapped_column(String(50), default="unknown", index=True); lower_type: Mapped[str] = mapped_column(String(50), default="unknown"); lower_color: Mapped[str] = mapped_column(String(50), default="unknown"); accessories: Mapped[str] = mapped_column(Text, default="[]"); objects_held: Mapped[str] = mapped_column(Text, default="[]"); confidence: Mapped[float] = mapped_column(Float, default=0); source: Mapped[str] = mapped_column(String(30), default="qwen")
class AttributeAudit(Base):
    """Raw model output is retained separately so malformed Qwen replies never erase a track."""
    __tablename__ = "attribute_audits"
    id: Mapped[int] = mapped_column(primary_key=True); video_id: Mapped[int] = mapped_column(ForeignKey("videos.id"), index=True); track_id: Mapped[int] = mapped_column(Integer, index=True); raw_response: Mapped[str] = mapped_column(Text, default=""); parse_error: Mapped[str | None] = mapped_column(Text, nullable=True); created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
class ObjectObservation(Base):
    """Frame-level non-person YOLO evidence. Objects intentionally do not share person track IDs."""
    __tablename__ = "object_observations"; __table_args__ = (UniqueConstraint("frame_id", "label", "x1", "y1", "x2", "y2"),)
    id: Mapped[int] = mapped_column(primary_key=True); frame_id: Mapped[int] = mapped_column(ForeignKey("frames.id"), index=True); video_id: Mapped[int] = mapped_column(ForeignKey("videos.id"), index=True); label: Mapped[str] = mapped_column(String(80), index=True); confidence: Mapped[float] = mapped_column(Float); x1: Mapped[float] = mapped_column(Float); y1: Mapped[float] = mapped_column(Float); x2: Mapped[float] = mapped_column(Float); y2: Mapped[float] = mapped_column(Float)
class ObjectRelationship(Base):
    """A measured same-frame person/object association, never a global-video co-occurrence."""
    __tablename__ = "object_relationships"; __table_args__ = (UniqueConstraint("person_detection_id", "object_id"),)
    id: Mapped[int] = mapped_column(primary_key=True); video_id: Mapped[int] = mapped_column(ForeignKey("videos.id"), index=True); frame_id: Mapped[int] = mapped_column(ForeignKey("frames.id"), index=True); person_detection_id: Mapped[int] = mapped_column(ForeignKey("detections.id"), index=True); object_id: Mapped[int] = mapped_column(ForeignKey("object_observations.id"), index=True); relationship: Mapped[str] = mapped_column(String(50), default="associated_with", index=True); score: Mapped[float] = mapped_column(Float); normalized_distance: Mapped[float] = mapped_column(Float); overlap: Mapped[float] = mapped_column(Float)
class Action(Base):
    __tablename__ = "actions"
    id: Mapped[int] = mapped_column(primary_key=True); video_id: Mapped[int] = mapped_column(ForeignKey("videos.id"), index=True); track_id: Mapped[int] = mapped_column(Integer, index=True); action: Mapped[str] = mapped_column(String(50), index=True); start_timestamp: Mapped[float] = mapped_column(Float); end_timestamp: Mapped[float] = mapped_column(Float); confidence: Mapped[float] = mapped_column(Float)
class SearchQuery(Base):
    __tablename__ = "search_queries"
    id: Mapped[int] = mapped_column(primary_key=True); owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True); text: Mapped[str] = mapped_column(Text); parsed_json: Mapped[str] = mapped_column(Text); created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
class EvidenceVideo(Base):
    __tablename__ = "evidence_videos"
    id: Mapped[int] = mapped_column(primary_key=True); video_id: Mapped[int] = mapped_column(ForeignKey("videos.id")); track_id: Mapped[int] = mapped_column(Integer); path: Mapped[str] = mapped_column(String(500)); created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
