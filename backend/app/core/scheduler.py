import asyncio
import logging

from backend.app.services.notification_service import run_all_checks

logger = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 60 * 60  # every hour


async def periodic_notification_check():
    while True:
        try:
            run_all_checks()
            logger.info("Notification/auto-delete check completed")
        except Exception as e:
            logger.error(f"Notification check failed: {e}")

        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
