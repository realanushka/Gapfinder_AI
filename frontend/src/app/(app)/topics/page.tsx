"use client";

import Link from "next/link";
import { useCallback, useMemo, useState } from "react";

import { TopicTree } from "@/components/TopicTree";
import {
  Button,
  Card,
  EmptyState,
  ErrorBanner,
  Field,
  PageHeader,
  Spinner,
  inputClass,
} from "@/components/ui";
import { api } from "@/lib/api";
import { syllabusLabel, useSyllabi } from "@/lib/syllabi";
import { toTree } from "@/lib/tree";
import type { TopicDraft } from "@/lib/types";
import { toMessage, useApiData } from "@/lib/useApiData";

interface Draft {
  documentId: string;
  subject: string;
  topics: TopicDraft[];
}

function ContentPreview({ documentId }: { documentId: string }) {
  const fetchContent = useCallback(() => api.documentContent(documentId), [documentId]);
  const { data, loading, error } = useApiData(fetchContent);

  if (loading) return <Spinner label="Opening the file…" />;
  if (error) return <ErrorBanner message={error} />;
  if (!data) return null;

  return (
    <div>
      <pre className="max-h-72 overflow-auto whitespace-pre-wrap rounded-lg bg-surface-muted p-4 text-xs leading-relaxed">
        {data.text}
      </pre>
      {data.truncated ? (
        <p className="mt-1.5 text-xs text-muted">Showing the start of the file only.</p>
      ) : null}
    </div>
  );
}

/** The extracted subject → topic → subtopic structure, which the student can trim before saving. */
function DraftReview({
  draft,
  saving,
  onSubject,
  onRemoveTopic,
  onRemoveSubtopic,
  onSave,
  onDiscard,
}: {
  draft: Draft;
  saving: boolean;
  onSubject: (value: string) => void;
  onRemoveTopic: (topicIndex: number) => void;
  onRemoveSubtopic: (topicIndex: number, subtopicIndex: number) => void;
  onSave: () => void;
  onDiscard: () => void;
}) {
  const subtopicCount = draft.topics.reduce((sum, topic) => sum + topic.subtopics.length, 0);

  return (
    <div className="space-y-4 border-t border-border pt-5">
      <div>
        <h3 className="text-sm font-semibold">Review the topic map</h3>
        <p className="mt-0.5 text-xs text-muted">
          Extracted from your syllabus. Remove anything that doesn&apos;t belong, then save.
        </p>
      </div>

      <Field label="Subject" hint={`Saved as “${syllabusLabel(draft.subject || "…")}” in the sidebar.`}>
        <input
          className={inputClass}
          value={draft.subject}
          maxLength={255}
          disabled={saving}
          onChange={(e) => onSubject(e.target.value)}
        />
      </Field>

      <ul className="overflow-hidden rounded-xl border border-border bg-surface">
        {draft.topics.map((topic, topicIndex) => (
          <li key={`${topic.name}-${topicIndex}`} className="border-b border-border last:border-b-0">
            <div className="flex items-center justify-between gap-3 px-4 py-2.5">
              <span className="min-w-0 truncate text-sm font-medium">{topic.name}</span>
              <button
                type="button"
                disabled={saving}
                onClick={() => onRemoveTopic(topicIndex)}
                aria-label={`Remove topic ${topic.name}`}
                className="shrink-0 text-xs text-muted hover:text-weak disabled:opacity-50"
              >
                ✕ Remove
              </button>
            </div>
            {topic.subtopics.length > 0 ? (
              <ul className="pb-2">
                {topic.subtopics.map((subtopic, subtopicIndex) => (
                  <li
                    key={`${subtopic}-${subtopicIndex}`}
                    className="flex items-center justify-between gap-3 py-1.5 pr-4 pl-9"
                  >
                    <span className="min-w-0 truncate text-sm">
                      <span className="mr-1.5 text-muted">↳</span>
                      {subtopic}
                    </span>
                    <button
                      type="button"
                      disabled={saving}
                      onClick={() => onRemoveSubtopic(topicIndex, subtopicIndex)}
                      aria-label={`Remove subtopic ${subtopic}`}
                      className="shrink-0 text-xs text-muted hover:text-weak disabled:opacity-50"
                    >
                      ✕
                    </button>
                  </li>
                ))}
              </ul>
            ) : null}
          </li>
        ))}
      </ul>

      <p className="text-xs text-muted">
        {draft.topics.length} topic{draft.topics.length === 1 ? "" : "s"}, {subtopicCount} subtopic
        {subtopicCount === 1 ? "" : "s"}.
      </p>

      <div className="flex flex-wrap items-center gap-2">
        <Button onClick={onSave} disabled={saving || draft.topics.length === 0 || !draft.subject.trim()}>
          {saving ? "Saving…" : "Save topic map"}
        </Button>
        <Button variant="secondary" onClick={onDiscard} disabled={saving}>
          Discard
        </Button>
      </div>

      {saving ? (
        <Spinner label="Linking your notes to each topic and mapping past-paper questions — this can take a minute…" />
      ) : null}
    </div>
  );
}

export default function TopicsPage() {
  const fetchTopics = useCallback(() => api.listTopics(), []);
  const { data: topics, loading, error, reload: reloadTopics } = useApiData(fetchTopics);

  const fetchDocuments = useCallback(() => api.listDocuments(), []);
  const { data: documents, reload: reloadDocuments } = useApiData(fetchDocuments);

  const { syllabi, reload: reloadSyllabi } = useSyllabi();

  const [selectedId, setSelectedId] = useState("");
  const [contentFor, setContentFor] = useState<string | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [building, setBuilding] = useState(false);
  const [saving, setSaving] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [saved, setSaved] = useState<{ id: string; message: string } | null>(null);

  const syllabusFiles = useMemo(
    () => (documents ?? []).filter((doc) => doc.type === "syllabus"),
    [documents],
  );
  // A deleted file must not stay "selected".
  const activeId = syllabusFiles.some((doc) => doc.id === selectedId) ? selectedId : "";
  const activeDraft = draft && draft.documentId === activeId ? draft : null;

  function select(id: string) {
    setSelectedId(id);
    setActionError(null);
    setSaved(null);
  }

  async function handleBuild() {
    if (!activeId) return;
    setBuilding(true);
    setActionError(null);
    setSaved(null);
    setDraft(null);
    try {
      const preview = await api.previewTopicMap(activeId);
      setDraft({ documentId: preview.document_id, subject: preview.subject, topics: preview.topics });
    } catch (err) {
      setActionError(toMessage(err));
    } finally {
      setBuilding(false);
    }
  }

  async function handleSave() {
    if (!activeDraft) return;
    setSaving(true);
    setActionError(null);
    try {
      const result = await api.saveTopicMap(
        activeDraft.documentId,
        activeDraft.subject,
        activeDraft.topics,
      );
      setSaved({
        id: result.document_id,
        message:
          `Saved “${syllabusLabel(result.subject)}”: ${result.topics_created} topics, ` +
          `${result.chunks_linked} chunks of your material linked, ` +
          `${result.past_questions_mapped} past-paper questions mapped.`,
      });
      setDraft(null);
      reloadTopics();
      reloadDocuments();
      reloadSyllabi();
    } catch (err) {
      setActionError(toMessage(err));
    } finally {
      setSaving(false);
    }
  }

  function updateDraft(update: (current: Draft) => Draft) {
    setDraft((current) => (current ? update(current) : current));
  }

  // Saved maps, grouped by the syllabus each topic came from.
  const groups = useMemo(() => {
    const all = topics ?? [];
    const known = new Set(syllabi.map((s) => s.document_id));
    const bySyllabus = syllabi
      .map((s) => ({
        id: s.document_id,
        title: syllabusLabel(s.subject),
        nodes: toTree(all.filter((t) => t.document_id === s.document_id)),
      }))
      .filter((group) => group.nodes.length > 0);
    const orphans = toTree(all.filter((t) => !t.document_id || !known.has(t.document_id)));
    return { bySyllabus, orphans };
  }, [topics, syllabi]);

  const hasAnyTopics = groups.bySyllabus.length > 0 || groups.orphans.length > 0;

  return (
    <>
      <PageHeader
        title="Topic map"
        subtitle="Your syllabus, broken into subjects and topics and weighted by how often each one shows up in past papers."
      />

      <Card className="mb-8">
        <div className="space-y-5">
          {actionError ? <ErrorBanner message={actionError} /> : null}
          {saved ? (
            <p className="rounded-lg border border-strong/30 bg-strong-soft px-4 py-3 text-sm text-strong">
              {saved.message}{" "}
              <Link href={`/syllabus/${saved.id}`} className="font-medium underline">
                Open it →
              </Link>
            </p>
          ) : null}

          {syllabusFiles.length === 0 ? (
            <p className="text-sm text-muted">
              Your Syllabus folder is empty. Upload a file to the{" "}
              <span className="font-medium text-foreground">Syllabus</span> folder first —{" "}
              <Link href="/upload" className="font-medium text-brand hover:underline">
                go to Upload
              </Link>
              .
            </p>
          ) : (
            <>
              <Field label="1. Choose a syllabus from the Syllabus folder">
                <ul className="space-y-2">
                  {syllabusFiles.map((doc) => (
                    <li key={doc.id}>
                      <label
                        className={`flex cursor-pointer items-center gap-3 rounded-lg border p-3 text-sm transition-colors ${
                          activeId === doc.id
                            ? "border-brand bg-brand-soft"
                            : "border-border hover:bg-surface-muted"
                        }`}
                      >
                        <input
                          type="radio"
                          name="syllabus"
                          className="accent-brand"
                          checked={activeId === doc.id}
                          onChange={() => select(doc.id)}
                        />
                        <span className="min-w-0 flex-1 truncate font-medium">📄 {doc.filename}</span>
                        {doc.subject ? (
                          <span className="shrink-0 rounded-full bg-strong-soft px-2 py-0.5 text-xs font-semibold text-strong">
                            Saved
                          </span>
                        ) : null}
                      </label>
                    </li>
                  ))}
                </ul>
              </Field>

              {activeId ? (
                <div className="space-y-3">
                  <button
                    type="button"
                    onClick={() => setContentFor(contentFor === activeId ? null : activeId)}
                    className="text-sm font-medium text-brand hover:underline"
                    aria-expanded={contentFor === activeId}
                  >
                    {contentFor === activeId ? "Hide file content" : "Open file content"}
                  </button>
                  {contentFor === activeId ? <ContentPreview documentId={activeId} /> : null}

                  <div>
                    <p className="mb-1.5 text-sm font-medium">2. Build the topic map</p>
                    <Button onClick={handleBuild} disabled={building || saving}>
                      {building ? "Reading the syllabus…" : "Topic Build"}
                    </Button>
                    <p className="mt-1.5 text-xs text-muted">
                      Extracts the subject and topics so you can review them. Nothing is saved
                      until you click Save.
                    </p>
                  </div>
                </div>
              ) : null}

              {activeDraft ? (
                <DraftReview
                  draft={activeDraft}
                  saving={saving}
                  onSubject={(subject) => updateDraft((d) => ({ ...d, subject }))}
                  onRemoveTopic={(index) =>
                    updateDraft((d) => ({ ...d, topics: d.topics.filter((_, i) => i !== index) }))
                  }
                  onRemoveSubtopic={(topicIndex, subtopicIndex) =>
                    updateDraft((d) => ({
                      ...d,
                      topics: d.topics.map((topic, i) =>
                        i === topicIndex
                          ? { ...topic, subtopics: topic.subtopics.filter((_, j) => j !== subtopicIndex) }
                          : topic,
                      ),
                    }))
                  }
                  onSave={handleSave}
                  onDiscard={() => setDraft(null)}
                />
              ) : null}
            </>
          )}
        </div>
      </Card>

      {loading && !topics ? <Spinner /> : null}
      {error ? <ErrorBanner message={error} /> : null}

      {!loading && !error && !hasAnyTopics ? (
        <EmptyState
          title="No saved topic maps yet"
          description="Choose a syllabus above, click Topic Build, review the result and save it. Saved maps appear here and as shortcuts in the sidebar."
        />
      ) : null}

      <div className="space-y-8">
        {groups.bySyllabus.map((group) => (
          <section key={group.id}>
            <h2 className="mb-2 flex items-center gap-2 text-sm font-semibold">
              <span aria-hidden>📘</span>
              <Link href={`/syllabus/${group.id}`} className="hover:underline">
                {group.title}
              </Link>
            </h2>
            <TopicTree nodes={group.nodes} />
          </section>
        ))}

        {groups.orphans.length > 0 ? (
          <section>
            <h2 className="mb-2 text-sm font-semibold">Other topics</h2>
            <TopicTree nodes={groups.orphans} />
          </section>
        ) : null}
      </div>
    </>
  );
}
