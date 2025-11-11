from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime
from database import Base

class Material(Base):
    __tablename__ = "materials"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200))
    audio_path: Mapped[str] = mapped_column(String(400), nullable=True)
    transcript: Mapped[str] = mapped_column(Text)

class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200))
    material_id: Mapped[int] = mapped_column(ForeignKey("materials.id"))
    modes: Mapped[str] = mapped_column(String(100))  # e.g. "shadowing,dictation,retell,summary"
    difficulty: Mapped[str] = mapped_column(String(10), default="A2")

class Sentence(Base):
    __tablename__ = "sentences"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("materials.id"))
    order: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)

class Submission(Base):
    __tablename__ = "submissions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String(64))
    task_id: Mapped[int] = mapped_column(Integer)
    type: Mapped[str] = mapped_column(String(20))  # dictation/shadowing/retell/summary
    sentence_id: Mapped[int] = mapped_column(Integer, nullable=True)
    payload: Mapped[str] = mapped_column(Text)  # JSON string for raw input
    score: Mapped[float] = mapped_column(Integer, default=0)
    created_at: Mapped[DateTime] = mapped_column(DateTime, default=datetime.utcnow)