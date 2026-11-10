"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useCallback, useState } from "react";

import { TopicOptions } from "@/components/TopicOptions";
import {
  Button,
  Card,
  CitationChip,
  EmptyState,
  ErrorBanner,
  Field,
  PageHeader,
  Spinner,
  inputClass,
} from "@/components/ui";
import { api } from "@/lib/api";
import type { AnswerResult, Question } from "@/lib/types";
import { toMessage, useApiData } from "@/lib/useApiData";

function QuestionCard({
  question,
  index,
  result,
  onGraded,
}: {
  question: Question;
  index: number;
  result: AnswerResult | undefined;
  onGraded: (result: AnswerResult) => void;
}) {
  const [answer, setAnswer] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isMcq = question.options !== null;
  const graded = result !== undefined;

  async function handleSubmit() {
    if (!answer) return;
    setSubmitting(true);
    setError(null);
    try {
      onGraded(await api.submitAnswer(question.id, answer));
    } catch (err) {
      setError(toMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Card>
      <div className="mb-3 flex items-start justify-between gap-4">
        <p className="font-medium">
          <span className="mr-2 text-muted">{index + 1}.</span>
          {question.question}
        </p>
      </div>

      {question.citation ? (
        <div className="mb-4">
          <CitationChip text={question.citation} />
        </div>
      ) : null}

      {isMcq ? (
        <div className="space-y-2">
          {Object.entries(question.options ?? {}).map(([key, text]) => (
            <label
              key={key}
              className={`flex cursor-pointer items-start gap-3 rounded-lg border p-3 text-sm transition-colors ${
                answer === key ? "border-brand bg-brand-soft" : "border-border hover:bg-surface-muted"
              } ${graded ? "pointer-events-none opacity-80" : ""}`}
            >
              <input
                type="radio"
                name={`q-${question.id}`}
                className="mt-0.5 accent-brand"
                checked={answer === key}
                disabled={graded}
                onChange={() => setAnswer(key)}
              />
              <span>
                <span className="font-medium">{key}.</span> {text}
              </span>
            </label>
          ))}
        </div>
      ) : (
        <textarea
          rows={3}
          className={inputClass}
          placeholder="Type your answer…"
          value={answer}
          disabled={graded}
          onChange={(e) => setAnswer(e.target.value)}
        />
      )}

      {error ? (
        <div className="mt-3">
          <ErrorBanner message={error} />
        </div>
      ) : null}

      {!graded ? (
        <Button className="mt-4" onClick={handleSubmit} disabled={!answer || submitting}>
          {submitting ? "Checking…" : "Submit answer"}
        </Button>
      ) : (
        <div
          className={`mt-4 rounded-lg px-4 py-3 text-sm ${
            result.is_correct ? "bg-strong-soft text-strong" : "bg-weak-soft text-weak"
          }`}
        >
          <p className="font-semibold">
            {result.is_correct ? "✅ Correct" : "❌ Not quite"}
            {!result.is_correct && result.concept_tag ? (
              <span className="font-normal"> — missed concept: {result.concept_tag}</span>
            ) : null}
          </p>
          {result.feedback ? <p className="mt-1 opacity-90">{result.feedback}</p> : null}
        </div>
      )}
    </Card>
  );
}

function QuizContent() {
  const searchParams = useSearchParams();
  const topicFromUrl = searchParams.get("topic") ?? "";

  const fetchTopics = useCallback(() => api.listTopics(), []);
  const { data: topics, loading: topicsLoading, error: topicsError } = useApiData(fetchTopics);

  const [questions, setQuestions] = useState<Question[] | null>(null);
  const [results, setResults] = useState<Record<string, AnswerResult>>({});
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [snapshotDone, setSnapshotDone] = useState(false);

  // Derive the selection instead of mirroring the URL into state via an effect.
  // Stamping the choice with the URL value it was made under means arriving from
  // a new ?topic= link resets the picker, without any synchronisation code.
  const [picked, setPicked] = useState<{ under: string; value: string } | null>(null);
  const topicId = picked?.under === topicFromUrl ? picked.value : topicFromUrl;
  const setTopicId = (value: string) => setPicked({ under: topicFromUrl, value });

  const generate = useCallback(async (id?: string) => {
    setGenerating(true);
    setError(null);
    setResults({});
    setSnapshotDone(false);
    try {
      setQuestions(await api.generateQuiz(id));
    } catch (err) {
      setError(toMessage(err));
      setQuestions(null);
    } finally {
      setGenerating(false);
    }
  }, []);

  const answeredCount = Object.keys(results).length;
  const allAnswered =
    questions !== null && questions.length > 0 && answeredCount === questions.length;

  /**
   * Record this sitting once every question is answered. The gap report is a
   * pure read, so this is what gives the dashboard its attempt history.
   */
  async function handleGraded(result: AnswerResult) {
    const next = { ...results, [result.question_id]: result };
    setResults(next);

    if (questions && Object.keys(next).length === questions.length && !snapshotDone) {
      setSnapshotDone(true);
      try {
        await api.snapshotGapReport();
      } catch {
        // Non-fatal: the answers are already saved, only the history snapshot
        // failed, so don't block the student's results screen.
        setSnapshotDone(false);
      }
    }
  }

  return (
    <>
      <PageHeader
        title="Diagnostic quiz"
        subtitle="Questions are written only from your uploaded material, and each one cites its source."
      />

      <Card className="mb-8">
        <div className="space-y-4">
          {topicsLoading ? <Spinner label="Loading topics…" /> : null}
          {topicsError ? <ErrorBanner message={topicsError} /> : null}

          {!topicsLoading && topics?.length === 0 ? (
            <p className="text-sm text-muted">
              You need a topic map first —{" "}
              <Link href="/topics" className="font-medium text-brand hover:underline">
                build it from your syllabus
              </Link>
              .
            </p>
          ) : null}

          {topics && topics.length > 0 ? (
            <>
              <Field label="Topic">
                <select
                  className={inputClass}
                  value={topicId}
                  onChange={(e) => setTopicId(e.target.value)}
                >
                  <option value="">Choose a topic…</option>
                  <TopicOptions
                    topics={topics}
                    describe={(topic) =>
                      topic.name +
                      (topic.exam_weight > 0 ? ` (${topic.exam_weight}× in past papers)` : "")
                    }
                  />
                </select>
              </Field>
              <div className="flex flex-wrap gap-2">
                <Button onClick={() => generate(topicId)} disabled={!topicId || generating}>
                  {generating
                    ? "Writing questions…"
                    : questions
                      ? "Retake with new questions"
                      : "Generate quiz"}
                </Button>
                <Button variant="secondary" onClick={() => generate()} disabled={generating}>
                  Retake my weakest topics
                </Button>
              </div>
              <p className="text-xs text-muted">
                Question count scales with each topic&apos;s exam weight, and retakes draw on
                material you haven&apos;t been asked about yet.
              </p>
            </>
          ) : null}
        </div>
      </Card>

      {error ? <ErrorBanner message={error} /> : null}

      {questions && questions.length === 0 ? (
        <EmptyState
          title="No questions survived validation"
          description="Every generated question is checked against its source chunk and discarded if the answer isn't really there. Try generating again, or upload more detailed notes for this topic."
        />
      ) : null}

      {questions && questions.length > 0 ? (
        <>
          <div className="mb-4 flex items-center justify-between text-sm text-muted">
            <span>
              {answeredCount} of {questions.length} answered
            </span>
            {allAnswered ? (
              <Link href="/gap-report" className="font-medium text-brand hover:underline">
                See your gap report →
              </Link>
            ) : null}
          </div>

          <div className="space-y-4">
            {questions.map((question, index) => (
              <QuestionCard
                key={question.id}
                question={question}
                index={index}
                result={results[question.id]}
                onGraded={handleGraded}
              />
            ))}
          </div>
        </>
      ) : null}
    </>
  );
}

export default function QuizPage() {
  // useSearchParams() requires a Suspense boundary during prerender.
  return (
    <Suspense fallback={<Spinner />}>
      <QuizContent />
    </Suspense>
  );
}
