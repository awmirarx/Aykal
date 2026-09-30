"""
مدل‌های دیتابیس طبق سند فنی iCall
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, DateTime, Text, ForeignKey, Index, Float
)
from sqlalchemy.orm import relationship
from app.database import Base


class Lead(Base):
    """سرنخ — یه کاربر اینستاگرام که با پیج ما تعامل داشته"""
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    instagram_id = Column(String(64), unique=True, index=True, nullable=False)
    username = Column(String(128), nullable=True, index=True)
    full_name = Column(String(255), nullable=True)

    # تحلیل AI
    intent = Column(String(64), default="unknown", index=True)
    lead_score = Column(Integer, default=0, index=True)

    # وضعیت چرخه عمر
    status = Column(String(32), default="active", index=True)
    # active | engaged | warm | hot | cold | converted | lost

    # آمار تعامل
    total_interactions = Column(Integer, default=0)
    last_interaction_at = Column(DateTime, nullable=True)
    first_seen_at = Column(DateTime, default=datetime.utcnow)

    # زمان‌ها
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    interactions = relationship("Interaction", back_populates="lead", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_lead_score_status", "lead_score", "status"),
    )

    def __repr__(self):
        return f"<Lead @{self.username} score={self.lead_score} intent={self.intent}>"


class Interaction(Base):
    """یه تعامل (کامنت / دایرکت / لایک / منشن)"""
    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id", ondelete="CASCADE"), nullable=False)
    instagram_id = Column(String(64), nullable=False, index=True)

    interaction_type = Column(String(32), nullable=False, index=True)
    # comment | direct | like | mention | story_reply

    content = Column(Text, nullable=True)
    media_id = Column(String(64), nullable=True)
    comment_id = Column(String(64), nullable=True, index=True)

    # تحلیل
    detected_intent = Column(String(64), nullable=True)
    intent_score = Column(Integer, default=0)

    # metadata اضافی
    meta_json = Column(Text, nullable=True)  # JSON string

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    lead = relationship("Lead", back_populates="interactions")

    __table_args__ = (
        Index("ix_interaction_lead_created", "lead_id", "created_at"),
    )

    def __repr__(self):
        return f"<Interaction {self.interaction_type} from={self.instagram_id}>"