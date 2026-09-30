"""
تسک‌های async برای پردازش webhook
"""
import logging
from app.tasks.celery_app import celery_app
from app.database import SessionLocal
from app.schemas import IncomingInteraction, InteractionType
from app.services.lead_harvester import process_interaction, mark_inactive_leads

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.webhook_tasks.process_interaction_task", bind=True, max_retries=3)
def process_interaction_task(self, payload: dict):
    """
    پردازش یه تعامل در پس‌زمینه.
    اگه خطا داد، تا ۳ بار retry می‌کنه (با backoff).
    """
    db = SessionLocal()
    try:
        data = IncomingInteraction(
            instagram_id=payload["instagram_id"],
            username=payload.get("username"),
            interaction_type=InteractionType(payload["interaction_type"]),
            text_content=payload.get("text_content"),
            media_id=payload.get("media_id"),
            comment_id=payload.get("comment_id"),
        )
        lead = process_interaction(db, data)
        logger.info("Processed interaction for @%s (score=%d)", lead.username, lead.lead_score)
        return {"status": "ok", "lead_id": lead.id, "score": lead.lead_score}

    except Exception as exc:
        logger.exception("Failed to process interaction")
        db.rollback()
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
    finally:
        db.close()


@celery_app.task(name="app.tasks.webhook_tasks.mark_inactive_leads_task")
def mark_inactive_leads_task():
    """تسک دوره‌ای برای علامت‌گذاری کاربران غیرفعال"""
    db = SessionLocal()
    try:
        return mark_inactive_leads(db)
    finally:
        db.close()
