import logging
from datetime import datetime, timedelta
from database import get_db, User, UserStats

logger = logging.getLogger(__name__)


class StatsService:
    """Service for managing user statistics"""

    @staticmethod
    def update_user_activity(user: User) -> None:
        """
        Update user activity statistics

        Args:
            user: User object
        """
        with get_db() as db:
            user = db.merge(user)

            stats = db.query(UserStats).filter(UserStats.user_id == user.id).first()

            if not stats:
                stats = UserStats(user_id=user.id)
                db.add(stats)

            # Increment total messages
            stats.total_messages += 1

            # Update streak and active days
            today = datetime.utcnow().date()
            last_active_date = stats.last_active.date() if stats.last_active else None

            if last_active_date is None:
                # First activity
                stats.active_days = 1
                stats.current_streak = 1
            elif last_active_date == today:
                # Same day, no changes to active_days or streak
                pass
            elif last_active_date == today - timedelta(days=1):
                # Consecutive day
                stats.active_days += 1
                stats.current_streak += 1
            else:
                # Streak broken
                stats.active_days += 1
                stats.current_streak = 1

            stats.last_active = datetime.utcnow()
            db.commit()
            logger.info(f"Updated stats for user {user.telegram_id}")

    @staticmethod
    def get_user_stats(user: User) -> dict:
        """
        Get user statistics

        Args:
            user: User object

        Returns:
            Dictionary with user statistics
        """
        with get_db() as db:
            user = db.merge(user)
            stats = db.query(UserStats).filter(UserStats.user_id == user.id).first()

            if not stats:
                return {
                    "total_messages": 0,
                    "active_days": 0,
                    "current_streak": 0,
                    "last_active": None
                }

            return {
                "total_messages": stats.total_messages,
                "active_days": stats.active_days,
                "current_streak": stats.current_streak,
                "last_active": stats.last_active
            }

    @staticmethod
    def format_stats_message(stats: dict, user_level: str) -> str:
        """
        Format statistics into a readable message

        Args:
            stats: Statistics dictionary
            user_level: User's English level

        Returns:
            Formatted statistics message
        """
        last_active = "Never" if not stats["last_active"] else stats["last_active"].strftime("%Y-%m-%d %H:%M")

        message = f"""📊 Your Learning Statistics

🎯 Level: {user_level}
💬 Total messages: {stats['total_messages']}
📅 Active days: {stats['active_days']}
🔥 Current streak: {stats['current_streak']} day(s)
⏰ Last active: {last_active}

Keep up the great work! 🎉"""

        return message
