"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback } from "react";

import { TopicTree } from "@/components/TopicTree";
import { Button, Card, EmptyState, ErrorBanner, PageHeader, Spinner } from "@/components/ui";
import { api } from "@/lib/api";
import { syllabusLabel } from "@/lib/syllabi";
import { useApiData } from "@/lib/useApiData";

/** A saved syllabus: reached from its sidebar shortcut. */
export default function SyllabusPage() {
  const { id } = useParams<{ id: string }>();

  const fetchSyllabus = useCallback(() => api.syllabusDetail(id), [id]);
  const { data: syllabus, loading, error } = useApiData(fetchSyllabus);

  if (loading && !syllabus) return <Spinner label="Opening syllabus…" />;

  if (error || !syllabus) {
    return (
      <>
        {error ? <ErrorBanner message={error} /> : null}
        <div className="mt-4">
          <EmptyState
            title="Syllabus not found"
            description="It may have been deleted, or its topic map hasn't been saved yet."
            action={
              <Link href="/topics" className="text-sm font-medium text-brand hover:underline">
                Go to the Topic Map
              </Link>
            }
          />
        </div>
      </>
    );
  }

  const subtopicCount = syllabus.topics.reduce((sum, topic) => sum + topic.subtopics.length, 0);

  return (
    <>
      <PageHeader
        title={syllabusLabel(syllabus.subject)}
        subtitle={`From ${syllabus.filename} · ${syllabus.topics.length} topics, ${subtopicCount} subtopics`}
      />

      <Card className="mb-8">
        <p className="text-sm text-muted">
          Quizzes and the tutor use this structure: questions are written from your notes for the
          topic you pick, and the chatbot answers with this syllabus as its frame of reference.
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          <Link href="/quiz">
            <Button>Take a quiz</Button>
          </Link>
          <Link href="/explain">
            <Button variant="secondary">Ask the tutor</Button>
          </Link>
          <Link href="/topics">
            <Button variant="secondary">Rebuild topic map</Button>
          </Link>
        </div>
      </Card>

      {syllabus.topics.length === 0 ? (
        <EmptyState title="No topics" description="This syllabus has no topics saved." />
      ) : (
        <TopicTree nodes={syllabus.topics} />
      )}
    </>
  );
}
