"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useCallback, useMemo, useState } from "react";

import { TopicOptions } from "@/components/TopicOptions";
import {
  Button,
  Card,
  CitationChip,
  ErrorBanner,
  Field,
  PageHeader,
  Spinner,
  formatCitation,
  inputClass,
} from "@/components/ui";
import { api } from "@/lib/api";
import type { ExplainResponse } from "@/lib/types";
import { toMessage, useApiData } from "@/lib/useApiData";

function ExplainContent() {
  const searchParams = useSearchParams();
  const topicFromUrl = searchParams.get("topic") ?? "";

  const fetchTopics = useCallback(() => api.listTopics(), []);
  const { data: topics } = useApiData(fetchTopics);

  const [answer, setAnswer] = useState<ExplainResponse | null>(null);
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Both the topic and the question are derived from the URL rather than
  // copied into state by an effect. Each edit is stamped with the ?topic=
  // value it was made under, so following a new "Revise this" link resets
  // the form instead of keeping the previous topic's question.
  const [picked, setPicked] = useState<{ under: string; value: string } | null>(null);
  const topicId = picked?.under === topicFromUrl ? picked.value : topicFromUrl;
  const setTopicId = (value: string) => setPicked({ under: topicFromUrl, value });

  const suggestedQuestion = useMemo(() => {
    const topic = topics?.find((t) => t.id === topicFromUrl);
    return topic ? `Explain ${topic.name}` : "";
  }, [topics, topicFromUrl]);

  const [typed, setTyped] = useState<{ under: string; value: string } | null>(null);
  const question = typed?.under === topicFromUrl ? typed.value : suggestedQuestion;
  const setQuestion = (value: string) => setTyped({ under: topicFromUrl, value });

  async function handleAsk(event: React.FormEvent) {
    event.preventDefault();
    if (!question.trim()) return;

    setAsking(true);
    setError(null);
    setAnswer(null);
    try {
      setAnswer(await api.explain(question, topicId || undefined));
    } catch (err) {
      setError(toMessage(err));
    } finally {
      setAsking(false);
    }
  }

  return (
    <>
      <PageHeader
        title="Explain this topic"
        subtitle="Answers come only from your uploaded material, framed by your saved syllabus — if it isn't in there, GapFinder says so."
      />

      <Card className="mb-8">
        <form onSubmit={handleAsk} className="space-y-4">
          {error ? <ErrorBanner message={error} /> : null}

          <Field label="Your question">
            <textarea
              rows={3}
              required
              className={inputClass}
              placeholder="e.g. Why does the light reaction need water?"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
            />
          </Field>

          {topics && topics.length > 0 ? (
            <Field label="Focus on a topic" hint="Optional — searches only that topic's material, and tells the tutor where it sits in your syllabus.">
              <select
                className={inputClass}
                value={topicId}
                onChange={(e) => setTopicId(e.target.value)}
              >
                <option value="">All of my material</option>
                <TopicOptions topics={topics} />
              </select>
            </Field>
          ) : null}

          <Button type="submit" disabled={asking || !question.trim()}>
            {asking ? "Searching your material…" : "Explain"}
          </Button>
        </form>
      </Card>

      {asking ? <Spinner label="Retrieving the most relevant chunks…" /> : null}

      {answer ? (
        <Card>
          {!answer.covered_by_material ? (
            <div className="mb-4 rounded-lg border border-medium/30 bg-medium-soft px-4 py-3 text-sm text-medium">
              <p className="font-semibold">Not in your material</p>
              <p className="mt-1 opacity-90">
                GapFinder refuses to answer from outside knowledge — upload notes covering this
                to get an answer.
              </p>
            </div>
          ) : null}

          <p className="whitespace-pre-wrap text-sm leading-relaxed">{answer.answer}</p>

          {answer.citations.length > 0 ? (
            <div className="mt-5 border-t border-border pt-4">
              <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted">
                Sources
              </p>
              <div className="flex flex-wrap gap-2">
                {answer.citations.map((citation) => (
                  <CitationChip
                    key={citation.chunk_id}
                    text={formatCitation(citation) || "Your material"}
                  />
                ))}
              </div>
            </div>
          ) : null}
        </Card>
      ) : null}
    </>
  );
}

export default function ExplainPage() {
  return (
    <Suspense fallback={<Spinner />}>
      <ExplainContent />
    </Suspense>
  );
}
