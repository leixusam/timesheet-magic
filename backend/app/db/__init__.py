from sqlalchemy import create_engine, Column, String, DateTime, Text, Float, Integer, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
import pathlib

# Database URL - use SQLite for now, easy to switch to PostgreSQL later
# Get absolute path to ensure database is created in backend directory
BACKEND_DIR = pathlib.Path(__file__).parent.parent.parent  # Go up from app/db/ to backend/
DB_PATH = BACKEND_DIR / "timesheet_magic.db"

# Check if DATABASE_URL is set and handle relative paths
env_db_url = os.getenv("DATABASE_URL")
if env_db_url and env_db_url.startswith("sqlite:///"):
    # Extract the path part after sqlite:///
    db_file_path = env_db_url[10:]  # Remove "sqlite:///"
    
    # Handle the specific case where .env.local incorrectly includes './backend/'
    if db_file_path.startswith("./backend/"):
        db_file_path = db_file_path[10:]  # Remove './backend/'
    elif db_file_path.startswith("./"):
        db_file_path = db_file_path[2:]  # Remove './'
    
    # If it's still a relative path, make it absolute relative to backend directory
    if not db_file_path.startswith("/"):
        abs_db_path = BACKEND_DIR / db_file_path
        DATABASE_URL = f"sqlite:///{abs_db_path}"
    else:
        DATABASE_URL = env_db_url
else:
    DATABASE_URL = env_db_url or f"sqlite:///{DB_PATH}"

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
