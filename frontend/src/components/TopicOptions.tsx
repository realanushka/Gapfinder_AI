"use client";

import { syllabusLabel, useSyllabi } from "@/lib/syllabi";
import type { TopicRecord } from "@/lib/types";

/**
 * <option> elements for a topic dropdown, grouped under the syllabus each topic
 * belongs to ("Physics Syllabus", "Chemistry Syllabus", ...). Topics that do not
 * belong to a saved syllabus go under "Other topics".
 */
export function TopicOptions({
  topics,
  describe = (topic) => topic.name,
}: {
  topics: TopicRecord[];
  describe?: (topic: TopicRecord) => string;
}) {
  const { syllabi } = useSyllabi();

  const groups = syllabi
    .map((syllabus) => ({
      key: syllabus.document_id,
      label: syllabusLabel(syllabus.subject),
      topics: topics.filter((topic) => topic.document_id === syllabus.document_id),
    }))
    .filter((group) => group.topics.length > 0);

  const known = new Set(syllabi.map((syllabus) => syllabus.document_id));
  const other = topics.filter((topic) => !topic.document_id || !known.has(topic.document_id));

  // With nothing to group by, a flat list is simpler than a single optgroup.
  if (groups.length === 0) {
    return (
      <>
        {topics.map((topic) => (
          <option key={topic.id} value={topic.id}>
            {describe(topic)}
          </option>
        ))}
      </>
    );
  }

  return (
    <>
      {groups.map((group) => (
        <optgroup key={group.key} label={group.label}>
          {group.topics.map((topic) => (
            <option key={topic.id} value={topic.id}>
              {describe(topic)}
            </option>
          ))}
        </optgroup>
      ))}
      {other.length > 0 ? (
        <optgroup label="Other topics">
          {other.map((topic) => (
            <option key={topic.id} value={topic.id}>
              {describe(topic)}
            </option>
          ))}
        </optgroup>
      ) : null}
    </>
  );
}
