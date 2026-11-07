"""Dashboard numbers, computed from stored chat messages (no extra tables)."""
from datetime import timedelta

from django.db.models import Avg, Count, Max, Q
from django.db.models.functions import TruncDate
from django.utils import timezone

from apps.chat.models import Message


def _since(days):
    return timezone.now() - timedelta(days=days)


def summary(days):
    since = _since(days)
    questions = Message.objects.filter(role=Message.Role.USER, created_at__gte=since)
    answers = Message.objects.filter(role=Message.Role.ASSISTANT, created_at__gte=since)
    agg = answers.aggregate(
        total=Count("id"), refused=Count("id", filter=Q(refused=True)), latency=Avg("latency_ms"),
        up=Count("id", filter=Q(feedback="up")), down=Count("id", filter=Q(feedback="down")))
    per_day = (questions.annotate(date=TruncDate("created_at")).values("date")
               .annotate(count=Count("id")).order_by("date"))
    return {
        "period_days": days,
        "total_questions": questions.count(),
        "active_users": questions.values("conversation__user").distinct().count(),
        "refusal_rate": round(agg["refused"] / agg["total"], 3) if agg["total"] else 0.0,
        "avg_latency_ms": int(agg["latency"] or 0),
        "feedback": {"up": agg["up"], "down": agg["down"]},
        "questions_per_day": [{"date": d["date"].isoformat(), "count": d["count"]} for d in per_day],
    }


def top_questions(days, limit):
    rows = (Message.objects.filter(role=Message.Role.USER, created_at__gte=_since(days))
            .exclude(normalized="")
            .values("normalized")
            .annotate(count=Count("id"), refused_count=Count("id", filter=Q(replies__refused=True)),
                      last_id=Max("id"))
            .order_by("-count", "-last_id")[:limit])
    # Show the most recent original wording of each group, not the normalised form.
    wording = dict(Message.objects.filter(id__in=[r["last_id"] for r in rows]).values_list("id", "content"))
    return [{"question": wording.get(r["last_id"], r["normalized"]), "count": r["count"],
             "refused_count": r["refused_count"]} for r in rows]
