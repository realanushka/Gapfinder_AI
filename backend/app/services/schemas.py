"""JSON Schemas for structured LLM outputs.

Passing one of these to `llm_client.generate_json` constrains decoding, so the
reply is guaranteed to be valid JSON with every required field present. That
removes the whole class of "the model returned prose instead of JSON" failures
the retry layer previously absorbed.

Schema constraints the API enforces, which shape everything below:

* every object needs `additionalProperties: false` and must list all of its
  properties in `required`;
* numeric bounds (`minimum`/`maximum`) and string bounds (`minLength`) are NOT
  supported, so value ranges are clamped in code instead -- see
  `evaluation_service.grade_short_answer`;
* recursive schemas are not supported, which is why the topic tree is a flat
  parent + subtopic-names shape rather than an arbitrarily nested node type.

`enum` is supported and worth using: it makes an invalid MCQ answer key or
grading verdict impossible rather than something to validate afterwards.
"""

from typing import Any

# A nullable string. Expressed with anyOf rather than a type array because
# anyOf is explicitly supported.
_NULLABLE_STRING: dict[str, Any] = {"anyOf": [{"type": "string"}, {"type": "null"}]}


# --- Step 4: syllabus -> topic tree ------------------------------------------
TOPIC_TREE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "subject": {"type": "string"},
        "topics": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string"},
                    "subtopics": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["topic", "subtopics"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["subject", "topics"],
    "additionalProperties": False,
}


# --- Step 4: which topic a past-paper question belongs to ---------------------
PAST_QUESTION_TOPIC_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"topic_id": _NULLABLE_STRING},
    "required": ["topic_id"],
    "additionalProperties": False,
}


# --- Step 5: quiz generation --------------------------------------------------
# The enum on `answer` is the important part: the key is guaranteed to be one of
# the four options, so a generation can no longer name an option that does not
# exist.
MCQ_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "question": {"type": "string"},
        "options": {
            "type": "object",
            "properties": {
                "A": {"type": "string"},
                "B": {"type": "string"},
                "C": {"type": "string"},
                "D": {"type": "string"},
            },
            "required": ["A", "B", "C", "D"],
            "additionalProperties": False,
        },
        "answer": {"type": "string", "enum": ["A", "B", "C", "D"]},
        "explanation": {"type": "string"},
    },
    "required": ["question", "options", "answer", "explanation"],
    "additionalProperties": False,
}

SHORT_ANSWER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "question": {"type": "string"},
        "answer": {"type": "string"},
        "explanation": {"type": "string"},
    },
    "required": ["question", "answer", "explanation"],
    "additionalProperties": False,
}


# --- Step 6: short-answer grading --------------------------------------------
# `score` cannot carry 0..1 bounds in the schema, so the caller clamps it.
# `concept_tag` is null when the answer was correct.
SHORT_ANSWER_GRADE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["correct", "partial", "wrong"]},
        "score": {"type": "number"},
        "reason": {"type": "string"},
        "concept_tag": _NULLABLE_STRING,
    },
    "required": ["verdict", "score", "reason", "concept_tag"],
    "additionalProperties": False,
}
