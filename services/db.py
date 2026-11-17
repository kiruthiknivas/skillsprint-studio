import os
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()

from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, Float, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, scoped_session

Base = declarative_base()

def get_database_url() -> str:
    """
    Get database URL from environment or fallback to local SQLite.
    Supports Supabase, Neon, ElephantSQL, Render PostgreSQL out of the box.
    """
    url = os.environ.get("DATABASE_URL", "").strip()
    if url:
        # Normalize postgres:// to postgresql:// for SQLAlchemy
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+psycopg://", 1)
        elif url.startswith("postgresql://") and not url.startswith("postgresql+psycopg://"):
            url = url.replace("postgresql://", "postgresql+psycopg://", 1)
        return url
    
    # Default to local SQLite database in project directory
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "interview_hub.db")
    return f"sqlite:///{db_path}"


# Initialize engine and session
db_url = get_database_url()
connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}
engine = create_engine(db_url, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_verified = Column(Boolean, default=False)
    otp_code = Column(String(10), nullable=True)
    otp_created_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Profile information
    primary_skill = Column(String(100), default=".NET Core / C#")
    secondary_skill = Column(String(100), default="Angular")
    years_experience = Column(Float, default=2.0)
    resume_text = Column(Text, nullable=True)
    
    # Relationships
    quiz_histories = relationship("QuizHistory", back_populates="user", cascade="all, delete-orphan")
    ats_reviews = relationship("ATSReview", back_populates="user", cascade="all, delete-orphan")
    study_plans = relationship("StudyPlan", back_populates="user", cascade="all, delete-orphan")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "is_verified": self.is_verified,
            "primary_skill": self.primary_skill or "",
            "secondary_skill": self.secondary_skill or "",
            "years_experience": self.years_experience or 2.0,
            "has_resume": bool(self.resume_text and len(self.resume_text.strip()) > 20),
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class QuizHistory(Base):
    __tablename__ = "quiz_histories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    quiz_title = Column(String(200), nullable=False)
    quiz_type = Column(String(50), default="skill_quiz") # "skill_quiz" or "company_targeted"
    company_name = Column(String(100), nullable=True)
    difficulty = Column(String(50), default="Intermediate")
    total_questions = Column(Integer, default=30)
    correct_count = Column(Integer, default=0)
    percentage = Column(Float, default=0.0)
    verdict = Column(String(100), nullable=True)
    topic_stats_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="quiz_histories")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "quiz_title": self.quiz_title,
            "quiz_type": self.quiz_type,
            "company_name": self.company_name or "General",
            "difficulty": self.difficulty,
            "total_questions": self.total_questions,
            "correct_count": self.correct_count,
            "percentage": self.percentage,
            "verdict": self.verdict,
            "topic_stats": json.loads(self.topic_stats_json) if self.topic_stats_json else {},
            "created_at": self.created_at.strftime("%b %d, %Y - %I:%M %p") if self.created_at else ""
        }


class ATSReview(Base):
    __tablename__ = "ats_reviews"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    target_role = Column(String(150), default="Software Engineer")
    company_name = Column(String(100), nullable=True)
    overall_score = Column(Integer, default=75)
    analysis_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="ats_reviews")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "target_role": self.target_role,
            "company_name": self.company_name or "General Industry",
            "overall_score": self.overall_score,
            "analysis": json.loads(self.analysis_json) if self.analysis_json else {},
            "created_at": self.created_at.strftime("%b %d, %Y - %I:%M %p") if self.created_at else ""
        }


class StudyPlan(Base):
    __tablename__ = "study_plans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    target_role = Column(String(150), nullable=False)
    company_name = Column(String(100), nullable=True)
    plan_title = Column(String(200), nullable=False)
    plan_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="study_plans")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "target_role": self.target_role,
            "company_name": self.company_name or "General",
            "plan_title": self.plan_title,
            "plan": json.loads(self.plan_json) if self.plan_json else {},
            "created_at": self.created_at.strftime("%b %d, %Y - %I:%M %p") if self.created_at else ""
        }


def init_db():
    """Create tables if they don't exist."""
    Base.metadata.create_all(bind=engine)
    print(f"[DB] Initialized database using {db_url.split('@')[-1] if '@' in db_url else db_url}")


def get_db():
    """Dependency session generator."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
