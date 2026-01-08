from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    level = Column(String(10), default='B1')
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    conversations = relationship("Conversation", back_populates="user")
    stats = relationship("UserStats", back_populates="user", uselist=False)

    def __repr__(self):
        return f"<User(telegram_id={self.telegram_id}, level={self.level})>"


class Conversation(Base):
    __tablename__ = 'conversations'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    topic = Column(String(100), nullable=True)

    # Relationships
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Conversation(id={self.id}, topic={self.topic})>"


class Message(Base):
    __tablename__ = 'messages'

    id = Column(Integer, primary_key=True)
    conversation_id = Column(Integer, ForeignKey('conversations.id'), nullable=False)
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    text_content = Column(Text, nullable=False)
    audio_file_id = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")

    def __repr__(self):
        return f"<Message(id={self.id}, role={self.role})>"


class UserStats(Base):
    __tablename__ = 'user_stats'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), unique=True, nullable=False)
    total_messages = Column(Integer, default=0)
    active_days = Column(Integer, default=0)
    current_streak = Column(Integer, default=0)
    last_active = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="stats")

    def __repr__(self):
        return f"<UserStats(user_id={self.user_id}, total_messages={self.total_messages})>"
