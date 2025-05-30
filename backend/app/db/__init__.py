from sqlalchemy import create_engine, Column, String, DateTime, Text, Float, Integer, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

# Database URL - use SQLite for now, easy to switch to PostgreSQL later
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./timesheet_magic.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class SavedReport(Base):
    __tablename__ = "saved_reports"
    
    id = Column(String, primary_key=True, index=True)  # UUID
    original_filename = Column(String, nullable=False)
    manager_name = Column(String, nullable=True)
    manager_email = Column(String, nullable=True)
    manager_phone = Column(String, nullable=True)
    store_name = Column(String, nullable=True)
    store_address = Column(String, nullable=True)
    
    # Report data (stored as JSON)
    report_data = Column(Text, nullable=False)  # JSON string of FinalAnalysisReport
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    file_size = Column(Integer, nullable=True)
    file_type = Column(String, nullable=True)
    
    # Quick access fields for listing/filtering
    employee_count = Column(Integer, nullable=True)
    total_violations = Column(Integer, nullable=True)
    total_hours = Column(Float, nullable=True)
    overtime_cost = Column(Float, nullable=True)

class Lead(Base):
    __tablename__ = "leads"
    
    id = Column(String, primary_key=True, index=True)  # UUID
    analysis_id = Column(String, nullable=False, index=True)  # Link to report
    manager_name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    store_name = Column(String, nullable=False)
    store_address = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

# Create tables
def create_tables():
    Base.metadata.create_all(bind=engine)

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
