from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from .config import get_settings

def _url() -> str:
    url = get_settings().database_url
    return url if url.startswith("sqlite:///") and url != "sqlite:///./ai_detective.db" else f"sqlite:///{get_settings().root / 'ai_detective.db'}"
engine = create_engine(_url(), connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
class Base(DeclarativeBase): pass
def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

