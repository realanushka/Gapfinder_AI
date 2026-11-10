import type { TopicRecord, TopicTreeNode } from "./types";

/** The API lists topics flat; rebuild parents with their subtopics, sorted by name. */
export function toTree(topics: TopicRecord[]): TopicTreeNode[] {
  const nodes = new Map<string, TopicTreeNode>(
    topics.map((topic) => [
      topic.id,
      { id: topic.id, name: topic.name, exam_weight: topic.exam_weight, subtopics: [] },
    ]),
  );
  const roots: TopicTreeNode[] = [];

  for (const topic of topics) {
    const node = nodes.get(topic.id);
    if (!node) continue;
    const parent = topic.parent_id ? nodes.get(topic.parent_id) : undefined;
    if (parent) parent.subtopics.push(node);
    else roots.push(node);
  }

  const byName = (a: TopicTreeNode, b: TopicTreeNode) => a.name.localeCompare(b.name);
  roots.sort(byName);
  for (const node of nodes.values()) node.subtopics.sort(byName);
  return roots;
}
