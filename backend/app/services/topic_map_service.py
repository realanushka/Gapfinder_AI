"""Saving a topic map, and the curriculum context built from it (Plan Step 4).

The pipeline is order-dependent, which is why it lives in one place:
topics -> link study material to topics -> map past-paper questions -> weights.
"""

import uuid

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chunk_topic import ChunkTopic
from app.models.document import Document, DocumentType
from app.models.past_question import PastQuestion
from app.models.topic import Topic
from app.schemas.topic import TopicBuildResult, TopicDraft, TopicTreeNode
from app.services.embedding_client import embed_texts
from app.services.retrieval_service import (
    STUDY_MATERIAL_TYPES,
    document_text,
    search_chunks,
    search_chunks_scored,
)
from app.services.topic_service import (
    confirm_past_question_topic,
    extract_year,
    split_past_paper,
)

# How many study-material chunks to attach to each topic. These are the chunks
# quiz generation will draw on, so a handful per topic is plenty.
CHUNKS_PER_TOPIC = 6
# Shortlist size handed to the LLM when confirming a past question's topic.
TOPIC_CANDIDATES_PER_QUESTION = 5
# A chunk is linked to a topic only if its similarity is within this margin of that
# topic's best-matching chunk. Without it, a small set of notes ends up linked to
# every topic and the quiz stops being topic-specific.
LINK_SIMILARITY_MARGIN = 0.07

# Bounds on what one save may create, so a bad extraction or a hand-crafted
# request cannot flood the database or the embedding API.
MAX_TOPICS = 60
MAX_SUBTOPICS_PER_TOPIC = 30


def clean_draft(drafts: list[TopicDraft]) -> list[TopicDraft]:
    """Drop blanks and duplicates (case-insensitive) and enforce the size caps."""
    cleaned: list[TopicDraft] = []
    seen_topics: set[str] = set()
    for draft in drafts:
        if not draft.name or draft.name.lower() in seen_topics:
            continue
        seen_topics.add(draft.name.lower())

        subtopics: list[str] = []
        seen_sub: set[str] = set()
        for name in draft.subtopics:
            if not name or name.lower() in seen_sub or name.lower() == draft.name.lower():
                continue
            seen_sub.add(name.lower())
            subtopics.append(name)
        cleaned.append(TopicDraft(name=draft.name, subtopics=subtopics[:MAX_SUBTOPICS_PER_TOPIC]))
    return cleaned[:MAX_TOPICS]


async def upsert_topic(
    db: AsyncSession,
    user_id: uuid.UUID,
    name: str,
    parent_id: uuid.UUID | None,
    document_id: uuid.UUID,
) -> Topic:
    """Reuse an existing topic with the same name, otherwise create it.

    Saving again must not delete topics: `questions` and `topic_scores` both
    cascade from `topics`, so dropping a row would silently destroy the
    student's quiz history. A topic that predates syllabi (document_id NULL) is
    adopted by this syllabus; one belonging to a *different* syllabus is left
    alone, so two syllabi can both have an "Introduction".
    """
    existing = await db.scalar(
        select(Topic)
        .where(
            Topic.user_id == user_id,
            Topic.name == name,
            Topic.parent_id.is_(None) if parent_id is None else Topic.parent_id == parent_id,
            or_(Topic.document_id == document_id, Topic.document_id.is_(None)),
        )
        .limit(1)
    )
    if existing is not None:
        existing.document_id = document_id
        return existing

    topic = Topic(
        user_id=user_id,
        name=name,
        parent_id=parent_id,
        exam_weight=0,
        document_id=document_id,
    )
    db.add(topic)
    await db.flush()
    return topic


def topic_query_text(topic: Topic, topics: list[Topic]) -> str:
    """Embed a topic with its subtopic names: a bare title like 'Nutrition' is too
    short to embed meaningfully, while 'Nutrition: autotrophic..., heterotrophic...' is."""
    children = [child.name for child in topics if child.parent_id == topic.id]
    return f"{topic.name}: {', '.join(children)}" if children else topic.name


async def link_material_to_topics(
    db: AsyncSession, user_id: uuid.UUID, topics: list[Topic]
) -> int:
    """Embed each topic and attach its closest study-material chunks."""
    if not topics:
        return 0

    embeddings = await embed_texts([topic_query_text(topic, topics) for topic in topics])

    links = 0
    for topic, embedding in zip(topics, embeddings, strict=True):
        # Links carry no history, so replacing them wholesale is safe and keeps
        # the mapping fresh when new notes are uploaded.
        await db.execute(delete(ChunkTopic).where(ChunkTopic.topic_id == topic.id))

        scored = await search_chunks_scored(
            db,
            user_id,
            embedding,
            limit=CHUNKS_PER_TOPIC,
            doc_types=STUDY_MATERIAL_TYPES,
        )
        if not scored:
            continue
        best = scored[0][1]  # results are nearest-first, so the first is the best
        for chunk, similarity in scored:
            if similarity >= best - LINK_SIMILARITY_MARGIN:
                db.add(ChunkTopic(chunk_id=chunk.id, topic_id=topic.id))
                links += 1

    return links


async def map_past_papers(
    db: AsyncSession, user_id: uuid.UUID, topics: list[Topic]
) -> int:
    """Split every past paper into questions and attach each to its best topic."""
    if not topics:
        return 0

    papers = list(
        (
            await db.scalars(
                select(Document).where(
                    Document.user_id == user_id,
                    Document.type == DocumentType.PAST_PAPER,
                )
            )
        ).all()
    )

    mapped = 0
    for paper in papers:
        # Clear this paper's previous rows so re-running doesn't double-count
        # and inflate every exam weight.
        await db.execute(delete(PastQuestion).where(PastQuestion.document_id == paper.id))

        text = await document_text(db, paper.id)
        questions = split_past_paper(text)
        if not questions:
            continue

        year = extract_year(paper.filename)
        question_embeddings = await embed_texts(questions)

        for question_text, embedding in zip(questions, question_embeddings, strict=True):
            # Retrieve candidate topics by similarity, then let the LLM confirm —
            # embeddings alone match loosely on shared vocabulary.
            candidates = await search_chunks(
                db, user_id, embedding, limit=TOPIC_CANDIDATES_PER_QUESTION
            )
            candidate_topic_ids = set(
                (
                    await db.scalars(
                        select(ChunkTopic.topic_id)
                        .where(ChunkTopic.chunk_id.in_([c.id for c in candidates]))
                        .distinct()
                    )
                ).all()
            )
            shortlist = [
                {"id": str(topic.id), "name": topic.name}
                for topic in topics
                if topic.id in candidate_topic_ids
            ][:TOPIC_CANDIDATES_PER_QUESTION]

            topic_id: uuid.UUID | None = None
            if shortlist:
                chosen = await confirm_past_question_topic(question_text, shortlist)
                if chosen:
                    try:
                        topic_id = uuid.UUID(chosen)
                    except ValueError:
                        topic_id = None

            db.add(
                PastQuestion(
                    text=question_text,
                    topic_id=topic_id,
                    year=year,
                    document_id=paper.id,
                )
            )
            if topic_id is not None:
                mapped += 1

    return mapped


async def recompute_exam_weights(db: AsyncSession, user_id: uuid.UUID) -> None:
    """exam_weight = how many past questions fall under each topic (Step 4.4)."""
    counts = (
        await db.execute(
            select(PastQuestion.topic_id, func.count(PastQuestion.id))
            .where(PastQuestion.topic_id.is_not(None))
            .group_by(PastQuestion.topic_id)
        )
    ).all()
    by_topic = {topic_id: count for topic_id, count in counts}

    topic_ids = list(
        (await db.scalars(select(Topic.id).where(Topic.user_id == user_id))).all()
    )
    for topic_id in topic_ids:
        await db.execute(
            update(Topic)
            .where(Topic.id == topic_id)
            .values(exam_weight=by_topic.get(topic_id, 0))
        )


def build_tree(topics: list[Topic]) -> list[TopicTreeNode]:
    """Turn a flat topic list into parents with their subtopics, sorted by name."""
    children: dict[uuid.UUID, list[Topic]] = {}
    roots: list[Topic] = []
    ids = {topic.id for topic in topics}
    for topic in topics:
        if topic.parent_id is not None and topic.parent_id in ids:
            children.setdefault(topic.parent_id, []).append(topic)
        else:
            roots.append(topic)

    def node(topic: Topic) -> TopicTreeNode:
        subs = sorted(children.get(topic.id, []), key=lambda t: t.name.lower())
        return TopicTreeNode(
            id=topic.id,
            name=topic.name,
            exam_weight=topic.exam_weight,
            subtopics=[node(sub) for sub in subs],
        )

    return [node(root) for root in sorted(roots, key=lambda t: t.name.lower())]


async def save_topic_map(
    db: AsyncSession,
    user_id: uuid.UUID,
    document: Document,
    subject: str,
    drafts: list[TopicDraft],
) -> TopicBuildResult:
    """Persist a reviewed topic map and run the rest of the pipeline.

    Does not commit; the caller owns the transaction.
    """
    drafts = clean_draft(drafts)

    saved: list[Topic] = []
    for draft in drafts:
        parent = await upsert_topic(db, user_id, draft.name, None, document.id)
        saved.append(parent)
        for subtopic_name in draft.subtopics:
            saved.append(await upsert_topic(db, user_id, subtopic_name, parent.id, document.id))

    document.subject = subject

    chunks_linked = await link_material_to_topics(db, user_id, saved)

    # Past questions are mapped against ALL of this student's topics, not just
    # the syllabus being saved: each paper is cleared and re-mapped, so limiting
    # it would wipe the mappings to every other syllabus.
    every_topic = list(
        (await db.scalars(select(Topic).where(Topic.user_id == user_id))).all()
    )
    questions_mapped = await map_past_papers(db, user_id, every_topic)
    await recompute_exam_weights(db, user_id)

    return TopicBuildResult(
        document_id=document.id,
        subject=subject,
        topics=build_tree(saved),
        topics_created=len(saved),
        chunks_linked=chunks_linked,
        past_questions_mapped=questions_mapped,
    )


async def curriculum_context(
    db: AsyncSession,
    user_id: uuid.UUID,
    topic: Topic | None = None,
    max_chars: int = 3500,
) -> str:
    """The saved syllabus outline as text, for use as a foundational prompt.

    With a topic, only that topic's syllabus is included, plus a line saying
    what the student is currently studying. Without one, every saved syllabus is
    included. Returns "" if the student has not saved a topic map yet.
    """
    syllabus_query = select(Document).where(
        Document.user_id == user_id,
        Document.type == DocumentType.SYLLABUS,
        Document.subject.is_not(None),
    )
    if topic is not None and topic.document_id is not None:
        syllabus_query = syllabus_query.where(Document.id == topic.document_id)
    syllabi = list((await db.scalars(syllabus_query.order_by(Document.subject))).all())
    if not syllabi:
        return ""

    all_topics = list(
        (
            await db.scalars(
                select(Topic).where(
                    Topic.user_id == user_id,
                    Topic.document_id.in_([doc.id for doc in syllabi]),
                )
            )
        ).all()
    )

    blocks: list[str] = []
    for syllabus in syllabi:
        own = [t for t in all_topics if t.document_id == syllabus.id]
        lines = [f"Subject: {syllabus.subject}"]
        for node in build_tree(own):
            subs = "; ".join(sub.name for sub in node.subtopics)
            lines.append(f"- {node.name}" + (f": {subs}" if subs else ""))
        blocks.append("\n".join(lines))

    text = "\n\n".join(blocks)
    if topic is not None:
        parent = (
            next((t for t in all_topics if t.id == topic.parent_id), None)
            if topic.parent_id
            else None
        )
        focus = f"The student is currently studying: {topic.name}"
        if parent is not None:
            focus += f" (part of {parent.name})"
        text += f"\n\n{focus}"

    return text[:max_chars]
