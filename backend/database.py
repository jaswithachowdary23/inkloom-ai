from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

DATABASE_URL = "sqlite:///./inkloom.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class BrandWorkspace(Base):
    __tablename__ = "brand_workspaces"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    guidelines = relationship("Guideline", back_populates="workspace", cascade="all, delete-orphan")
    drafts = relationship("Draft", back_populates="workspace", cascade="all, delete-orphan")


class Guideline(Base):
    __tablename__ = "guidelines"
    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("brand_workspaces.id"))
    category = Column(String(100), nullable=False)  # terminology, claim, tone, prohibited, preferred
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    severity = Column(String(50), default="medium")  # low, medium, high, critical
    is_exact_match = Column(Boolean, default=False)  # for deterministic checks
    created_at = Column(DateTime, default=datetime.utcnow)
    
    workspace = relationship("BrandWorkspace", back_populates="guidelines")


class Draft(Base):
    __tablename__ = "drafts"
    id = Column(Integer, primary_key=True, index=True)
    workspace_id = Column(Integer, ForeignKey("brand_workspaces.id"))
    title = Column(String(300), default="Untitled Draft")
    content = Column(Text, nullable=False)
    channel = Column(String(100), default="social")  # social, ad, campaign, email
    status = Column(String(50), default="draft")  # draft, under_review, approved, changes_requested
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    workspace = relationship("BrandWorkspace", back_populates="drafts")
    findings = relationship("Finding", back_populates="draft", cascade="all, delete-orphan")
    revisions = relationship("Revision", back_populates="draft", cascade="all, delete-orphan")


class Finding(Base):
    __tablename__ = "findings"
    id = Column(Integer, primary_key=True, index=True)
    draft_id = Column(Integer, ForeignKey("drafts.id"))
    category = Column(String(100))
    severity = Column(String(50))
    title = Column(String(300))
    explanation = Column(Text)
    original_text = Column(Text)
    suggested_text = Column(Text, nullable=True)
    guideline_id = Column(Integer, ForeignKey("guidelines.id"), nullable=True)
    is_rule_based = Column(Boolean, default=True)
    confidence = Column(Float, default=1.0)
    status = Column(String(50), default="open")  # open, accepted, rejected, modified
    created_at = Column(DateTime, default=datetime.utcnow)
    
    draft = relationship("Draft", back_populates="findings")


class Revision(Base):
    __tablename__ = "revisions"
    id = Column(Integer, primary_key=True, index=True)
    draft_id = Column(Integer, ForeignKey("drafts.id"))
    content = Column(Text)
    comment = Column(Text, default="")
    action = Column(String(100))  # created, edited, submitted, approved, changes_requested
    created_at = Column(DateTime, default=datetime.utcnow)
    
    draft = relationship("Draft", back_populates="revisions")


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()