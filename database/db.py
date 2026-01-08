from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
import config
from database.models import Base, User, UserStats

# Create engine
engine = create_engine(config.DATABASE_URL, echo=False)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialize database and create all tables"""
    Base.metadata.create_all(bind=engine)
    print("Database initialized successfully")


@contextmanager
def get_db() -> Session:
    """Context manager for database sessions"""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_or_create_user(telegram_id: int) -> User:
    """Get existing user or create a new one"""
    with get_db() as db:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()

        if not user:
            user = User(telegram_id=telegram_id)
            db.add(user)
            db.flush()

            # Create stats for the new user
            stats = UserStats(user_id=user.id)
            db.add(stats)
            db.commit()
            db.refresh(user)

        # Load all attributes before session closes
        _ = user.id
        _ = user.telegram_id
        _ = user.level
        _ = user.created_at

        # Make a detached copy to avoid session issues
        db.expunge(user)

        return user
