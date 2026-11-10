import Link from "next/link";

import type { TopicTreeNode } from "@/lib/types";

function ExamWeightBadge({ weight }: { weight: number }) {
  if (weight <= 0) return null;
  return (
    <span
      className="shrink-0 rounded-full bg-medium-soft px-2 py-0.5 text-xs font-semibold text-medium"
      title={`${weight} past-paper question${weight === 1 ? "" : "s"} mapped to this topic`}
    >
      {weight}× in past papers
    </span>
  );
}

function TopicRow({ node, depth }: { node: TopicTreeNode; depth: number }) {
  return (
    <>
      <li
        className="flex items-center justify-between gap-3 border-b border-border px-4 py-3 last:border-b-0"
        style={{ paddingLeft: `${16 + depth * 20}px` }}
      >
        <span className="min-w-0 truncate text-sm">
          {depth > 0 ? <span className="mr-1.5 text-muted">↳</span> : null}
          {node.name}
        </span>
        <div className="flex shrink-0 items-center gap-3">
          <ExamWeightBadge weight={node.exam_weight} />
          <Link
            href={`/quiz?topic=${node.id}`}
            className="text-xs font-medium text-brand hover:underline"
          >
            Quiz me
          </Link>
          <Link
            href={`/explain?topic=${node.id}`}
            className="text-xs font-medium text-brand hover:underline"
          >
            Ask
          </Link>
        </div>
      </li>
      {node.subtopics.map((child) => (
        <TopicRow key={child.id} node={child} depth={depth + 1} />
      ))}
    </>
  );
}

/** A saved topic map: topics with their subtopics, exam weights and study actions. */
export function TopicTree({ nodes }: { nodes: TopicTreeNode[] }) {
  return (
    <ul className="overflow-hidden rounded-xl border border-border bg-surface">
      {nodes.map((node) => (
        <TopicRow key={node.id} node={node} depth={0} />
      ))}
    </ul>
  );
}
