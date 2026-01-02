"""Subscription-related scheduled tasks."""

import asyncio
import logging
from datetime import datetime
from typing import Any

from aiogram import Bot

from src.core.config import settings
from src.db.session import get_session
from src.services.notification_service import NotificationService
from src.services.subscription_service import SubscriptionService

logger = logging.getLogger(__name__)

# Global scheduler instance
_scheduler: Any = None


async def run_expiry_notification_task(bot: Bot) -> dict[int, list[int]]:
    """Task to send expiry notifications for subscriptions.

    Checks for subscriptions expiring within configured days
    and sends notifications to users.

    Args:
        bot: Telegram bot instance

    Returns:
        Dict mapping days_left to list of notified user IDs
    """
    logger.info("Running expiry notification task at %s", datetime.utcnow())

    async with get_session() as session:
        notification_service = NotificationService(bot)
        subscription_service = SubscriptionService(session, notification_service)

        result = await subscription_service.check_expiring_subscriptions()

        total_notified = sum(len(users) for users in result.values())
        logger.info("Expiry notification task complete: %d notifications sent", total_notified)

        return result


async def run_auto_renewal_task(bot: Bot) -> dict[str, list[int]]:
    """Task to process auto-renewals for expiring subscriptions.

    Attempts to renew subscriptions for users with:
    - auto_renew enabled
    - subscription expiring today or already expired
    - sufficient token balance

    Args:
        bot: Telegram bot instance

    Returns:
        Dict with 'success' and 'failed' user ID lists
    """
    logger.info("Running auto-renewal task at %s", datetime.utcnow())

    async with get_session() as session:
        notification_service = NotificationService(bot)
        subscription_service = SubscriptionService(session, notification_service)

        result = await subscription_service.process_all_auto_renewals()

        logger.info(
            "Auto-renewal task complete: %d success, %d failed",
            len(result["success"]),
            len(result["failed"]),
        )
        return result


async def run_expire_subscriptions_task(bot: Bot) -> list[int]:
    """Task to notify users about expired subscriptions.

    Finds users with expired subscriptions and sends notifications.

    Args:
        bot: Telegram bot instance

    Returns:
        List of user IDs that were notified
    """
    logger.info("Running expire subscriptions task at %s", datetime.utcnow())

    async with get_session() as session:
        notification_service = NotificationService(bot)
        subscription_service = SubscriptionService(session, notification_service)

        expired_users = await subscription_service.expire_subscriptions()

        logger.info(
            "Expire subscriptions task complete: %d users expired",
            len(expired_users),
        )
        return expired_users


def setup_scheduler(bot: Bot) -> Any:
    """Set up APScheduler for subscription tasks.

    Args:
        bot: Telegram bot instance for notifications

    Returns:
        Configured scheduler instance
    """
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        logger.warning(
            "APScheduler not installed. Scheduled tasks will not run. "
            "Install with: pip install apscheduler"
        )
        return None

    global _scheduler

    scheduler = AsyncIOScheduler()

    # Task 1: Check expiring subscriptions and send notifications (every 6 hours)
    scheduler.add_job(
        run_expiry_notification_task,
        CronTrigger(hour="*/6"),
        args=[bot],
        id="expiry_notifications",
        name="Send subscription expiry notifications",
        replace_existing=True,
    )

    # Task 2: Process auto-renewals (daily at 00:05)
    scheduler.add_job(
        run_auto_renewal_task,
        CronTrigger(hour=0, minute=5),
        args=[bot],
        id="auto_renewals",
        name="Process subscription auto-renewals",
        replace_existing=True,
    )

    # Task 3: Notify about expired subscriptions (daily at 10:00)
    scheduler.add_job(
        run_expire_subscriptions_task,
        CronTrigger(hour=10, minute=0),
        args=[bot],
        id="expire_subscriptions",
        name="Notify about expired subscriptions",
        replace_existing=True,
    )

    _scheduler = scheduler
    logger.info("Subscription scheduler configured with %d jobs", len(scheduler.get_jobs()))

    return scheduler


def start_scheduler() -> None:
    """Start the global scheduler if configured."""
    global _scheduler
    if _scheduler is not None and not _scheduler.running:
        _scheduler.start()
        logger.info("Subscription scheduler started")


def stop_scheduler() -> None:
    """Stop the global scheduler if running."""
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Subscription scheduler stopped")


async def run_all_tasks_once(bot: Bot) -> dict:
    """Run all subscription tasks once (for testing/manual execution).

    Args:
        bot: Telegram bot instance

    Returns:
        Combined results from all tasks
    """
    logger.info("Running all subscription tasks manually at %s", datetime.utcnow())

    notifications = await run_expiry_notification_task(bot)
    renewals = await run_auto_renewal_task(bot)
    expired = await run_expire_subscriptions_task(bot)

    return {
        "notifications": notifications,
        "renewals": renewals,
        "expired": expired,
    }
