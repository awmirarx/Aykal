"""
ماژول Lead Harvester — طبق سند فنی iCall:
- ثبت تعاملات
- خوشه‌بندی خودکار کاربران بر اساس امتیاز
- به‌روزرسانی وضعیت چرخه عمر (lifecycle)
"""
import json
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models import Lead, Interaction
from app.schemas import IncomingInteraction, LeadStatus
from app.services.intent_classifier import classify_intent

logger = logging.getLogger(__name__)


# ============================================================
# آستانه‌های خوشه‌بندی (طبق سند فنی: پنجره‌های ۳ تا ۳۰ روزه)
# ============================================================

SCORE_THRESHOLDS = {
    "hot": 15,       # آماده خرید
    "warm": 10,      # علاقه‌مند
    "engaged": 5,    # فعال
}

INACTIVITY_WINDOWS = {
    "cold": 30,      # ۳۰ روز غیرفعال → سرد
    "lost": 90,      # ۹۰ روز غیرفعال → از دست رفته
}


# ============================================================
# پردازش تعامل جدید
# ============================================================

def process_interaction(db: Session, data: IncomingInteraction) -> Lead:
    """
    یه تعامل جدید رو پردازش می‌کنه:
    1. تحلیل نیت
    2. ثبت Interaction
    3. به‌روزرسانی یا ایجاد Lead
    4. به‌روزرسانی امتیاز و وضعیت
    """
    # ۱. تحلیل نیت
    intent, score = classify_intent(data.text_content, data.interaction_type)

    # ۲. پیدا کردن یا ساختن Lead
    lead = db.query(Lead).filter(Lead.instagram_id == data.instagram_id).first()

    if lead is None:
        lead = Lead(
            instagram_id=data.instagram_id,
            username=data.username,
            intent=intent.value,
            lead_score=score,
            status=LeadStatus.ACTIVE.value,
            total_interactions=0,
            first_seen_at=datetime.utcnow(),
        )
        db.add(lead)
        db.flush()  # برای گرفتن id
        logger.info("Created new lead @%s (id=%s)", data.username, lead.id)
    else:
        # به‌روزرسانی
        if data.username and not lead.username:
            lead.username = data.username

        # امتیاز انباشته می‌شه (نه فقط max) چون تعامل بیشتر = علاقه بیشتر
        lead.lead_score += score

        # آخرین نیت، مهم‌ترین نیت رو نگه دار (اگه امتیازش بالاتر بود)
        if score >= lead.lead_score - score:  # اگه نیت جدید قابل توجه بود
            lead.intent = intent.value

    # ۳. ثبت Interaction
    interaction = Interaction(
        lead_id=lead.id,
        instagram_id=data.instagram_id,
        interaction_type=data.interaction_type.value,
        content=data.text_content,
        media_id=data.media_id,
        comment_id=data.comment_id,
        detected_intent=intent.value,
        intent_score=score,
    )
    db.add(interaction)

    # ۴. به‌روزرسانی آمار Lead
    lead.total_interactions += 1
    lead.last_interaction_at = datetime.utcnow()
    lead.updated_at = datetime.utcnow()

    # ۵. به‌روزرسانی وضعیت بر اساس امتیاز
    lead.status = _determine_status(lead)

    db.commit()
    db.refresh(lead)
    return lead


def _determine_status(lead: Lead) -> str:
    """وضعیت چرخه عمر کاربر رو بر اساس امتیاز تعیین می‌کنه"""
    score = lead.lead_score

    if score >= SCORE_THRESHOLDS["hot"]:
        return LeadStatus.HOT.value
    elif score >= SCORE_THRESHOLDS["warm"]:
        return LeadStatus.WARM.value
    elif score >= SCORE_THRESHOLDS["engaged"]:
        return LeadStatus.ENGAGED.value
    else:
        return LeadStatus.ACTIVE.value


# ============================================================
# پایش کاربران غیرفعال (طبق سند فنی)
# ============================================================

def mark_inactive_leads(db: Session) -> dict:
    """
    کاربرانی که مدت زیادی غیرفعال بودن رو علامت‌گذاری می‌کنه.
    این تابع باید به‌صورت دوره‌ای (مثلاً روزانه با Celery Beat) اجرا بشه.
    """
    now = datetime.utcnow()
    stats = {"marked_cold": 0, "marked_lost": 0}

    # ۳۰ روز غیرفعال → cold
    cold_threshold = now - timedelta(days=INACTIVITY_WINDOWS["cold"])
    cold_leads = db.query(Lead).filter(
        Lead.last_interaction_at < cold_threshold,
        Lead.status.in_([LeadStatus.ACTIVE.value, LeadStatus.ENGAGED.value, LeadStatus.WARM.value]),
    ).all()

    for lead in cold_leads:
        lead.status = LeadStatus.COLD.value
        stats["marked_cold"] += 1

    # ۹۰ روز غیرفعال → lost
    lost_threshold = now - timedelta(days=INACTIVITY_WINDOWS["lost"])
    lost_leads = db.query(Lead).filter(
        Lead.last_interaction_at < lost_threshold,
        Lead.status != LeadStatus.LOST.value,
    ).all()

    for lead in lost_leads:
        lead.status = LeadStatus.LOST.value
        stats["marked_lost"] += 1

    db.commit()
    logger.info("Inactive leads updated: %s", stats)
    return stats


# ============================================================
# خوشه‌بندی کاربران (برای تحلیل)
# ============================================================

def get_lead_clusters(db: Session) -> dict:
    """
    آمار خوشه‌بندی کاربران بر اساس وضعیت و نیت.
    """
    by_status = dict(
        db.query(Lead.status, func.count(Lead.id)).group_by(Lead.status).all()
    )
    by_intent = dict(
        db.query(Lead.intent, func.count(Lead.id)).group_by(Lead.intent).all()
    )
    return {
        "by_status": by_status,
        "by_intent": by_intent,
        "total": db.query(Lead).count(),
    }