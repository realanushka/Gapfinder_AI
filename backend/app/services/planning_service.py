"""Priority scoring and scheduling, computed in code; task text via LLM (Plan Step 8)."""

from app.services.llm_client import generate_text

MINUTES_BY_STATUS = {"weak": 45, "medium": 25, "strong": 10}

TASK_DESCRIPTION_SYSTEM_PROMPT = """You write one short, actionable revision task description
for a student, referencing the given chapter/section/page range, e.g.
"Read Ch 3.2 (p. 45-48), then take a 5-question mini-quiz." Keep it to one sentence."""


def compute_priority(mastery: float, exam_weight: int) -> float:
    """priority = (1 - mastery) * exam_weight — deterministic and explainable."""
    return (1 - mastery) * exam_weight


def build_schedule(
    topics: list[dict], days: int, hours_per_day: float
) -> list[list[dict]]:
    """topics: [{"topic_id", "topic_name", "status", "priority"}, ...].

    Sorts by priority (weakest + highest exam-weight first) and fills each day
    with MINUTES_BY_STATUS-sized blocks until the day's time budget is used up.
    """
    minutes_per_day = int(hours_per_day * 60)
    ordered = sorted(topics, key=lambda t: t["priority"], reverse=True)

    schedule: list[list[dict]] = [[] for _ in range(days)]
    day_minutes_used = [0] * days

    for topic in ordered:
        minutes = MINUTES_BY_STATUS.get(topic["status"], 20)
        for day_index in range(days):
            if day_minutes_used[day_index] + minutes <= minutes_per_day:
                schedule[day_index].append({**topic, "minutes": minutes})
                day_minutes_used[day_index] += minutes
                break

    return schedule


async def describe_task(topic_name: str, chapter: str | None, section: str | None, page: int | None) -> str:
    prompt = f"Topic: {topic_name}\nChapter: {chapter}\nSection: {section}\nPage: {page}"
    return await generate_text(TASK_DESCRIPTION_SYSTEM_PROMPT, prompt)
