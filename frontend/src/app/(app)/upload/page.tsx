"use client";

import { useCallback, useState } from "react";

import { KebabMenu } from "@/components/KebabMenu";
import {
  Button,
  Card,
  ErrorBanner,
  Field,
  PageHeader,
  Spinner,
  inputClass,
} from "@/components/ui";
import { api } from "@/lib/api";
import { useSyllabi } from "@/lib/syllabi";
import type { DocumentRecord, DocumentType } from "@/lib/types";
import { toMessage, useApiData } from "@/lib/useApiData";

/** Each document type is a folder: choosing the type is what routes the file. */
const FOLDERS: { value: DocumentType; label: string; hint: string }[] = [
  { value: "syllabus", label: "Syllabus", hint: "Used to build your topic map" },
  { value: "notes", label: "Notes", hint: "Source for quiz questions" },
  { value: "textbook", label: "Textbook", hint: "Source for quiz questions" },
  { value: "past_paper", label: "Past paper", hint: "Used to weight topics by exam frequency" },
];

function folderLabel(type: DocumentType): string {
  return FOLDERS.find((folder) => folder.value === type)?.label ?? type;
}

/** What deleting a file takes with it, so the confirmation can say so plainly. */
function deleteWarning(type: DocumentType): string {
  switch (type) {
    case "syllabus":
      return "Its saved topic map goes too, along with quiz questions and scores for those topics.";
    case "past_paper":
      return "Exam weights will be recalculated without it.";
    default:
      return "Quiz questions generated from it, and your answers to them, are removed too.";
  }
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <dt className="text-xs text-muted">{label}</dt>
      <dd className="text-sm font-medium">{value}</dd>
    </div>
  );
}

function DetailsPanel({ documentId, onClose }: { documentId: string; onClose: () => void }) {
  const fetchDetails = useCallback(() => api.documentDetails(documentId), [documentId]);
  const { data, loading, error } = useApiData(fetchDetails);

  return (
    <div className="mt-3 rounded-lg bg-surface-muted p-4">
      {loading ? <Spinner label="Loading details…" /> : null}
      {error ? <ErrorBanner message={error} /> : null}
      {data ? (
        <dl className="grid grid-cols-2 gap-4 sm:grid-cols-3">
          <Stat label="Folder" value={folderLabel(data.type)} />
          <Stat label="Uploaded" value={new Date(data.created_at).toLocaleString()} />
          <Stat label="Searchable chunks" value={data.chunk_count} />
          <Stat label="Pages" value={data.page_count} />
          {data.type === "syllabus" ? (
            <>
              <Stat label="Topic map" value={data.subject ? `Saved as “${data.subject}”` : "Not saved yet"} />
              <Stat label="Topics" value={data.topic_count} />
            </>
          ) : null}
        </dl>
      ) : null}
      <button onClick={onClose} className="mt-3 text-xs text-muted underline hover:text-foreground">
        Close
      </button>
    </div>
  );
}

function ConfirmDelete({
  message,
  busy,
  onConfirm,
  onCancel,
}: {
  message: string;
  busy: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <div role="alertdialog" className="mt-3 rounded-lg border border-weak/30 bg-weak-soft p-4">
      <p className="text-sm text-weak">{message} This can&apos;t be undone.</p>
      <div className="mt-3 flex gap-2">
        <button
          onClick={onConfirm}
          disabled={busy}
          className="rounded-lg bg-weak px-3 py-1.5 text-sm font-medium text-white disabled:opacity-50"
        >
          {busy ? "Deleting…" : "Delete"}
        </button>
        <Button variant="secondary" onClick={onCancel} disabled={busy} className="!py-1.5">
          Cancel
        </Button>
      </div>
    </div>
  );
}

type RowMode = "idle" | "rename" | "delete" | "details";

function FileRow({ doc, onChanged }: { doc: DocumentRecord; onChanged: () => void }) {
  const { reload: reloadSyllabi } = useSyllabi();
  const [mode, setMode] = useState<RowMode>("idle");
  const [name, setName] = useState(doc.filename);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function open(next: RowMode) {
    setError(null);
    setName(doc.filename);
    setMode(next);
  }

  async function handleRename(event: React.FormEvent) {
    event.preventDefault();
    if (!name.trim() || name.trim() === doc.filename) {
      setMode("idle");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await api.renameDocument(doc.id, name);
      setMode("idle");
      onChanged();
      reloadSyllabi();
    } catch (err) {
      setError(toMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleDelete() {
    setBusy(true);
    setError(null);
    try {
      await api.deleteDocument(doc.id);
      onChanged();
      reloadSyllabi();
    } catch (err) {
      setError(toMessage(err));
      setBusy(false);
    }
  }

  return (
    <li className="rounded-lg border border-border bg-surface px-4 py-3">
      <div className="flex items-center justify-between gap-3">
        {mode === "rename" ? (
          <form onSubmit={handleRename} className="flex min-w-0 flex-1 items-center gap-2">
            <input
              autoFocus
              aria-label="New file name"
              className={inputClass}
              value={name}
              maxLength={255}
              onChange={(e) => setName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Escape") setMode("idle");
              }}
            />
            <Button type="submit" disabled={busy} className="!py-1.5">
              {busy ? "Saving…" : "Save"}
            </Button>
            <Button
              type="button"
              variant="secondary"
              disabled={busy}
              className="!py-1.5"
              onClick={() => setMode("idle")}
            >
              Cancel
            </Button>
          </form>
        ) : (
          <span className="min-w-0">
            <span className="block truncate text-sm font-medium">{doc.filename}</span>
            <span className="text-xs text-muted">
              {new Date(doc.created_at).toLocaleDateString()} · {doc.chunk_count} chunk
              {doc.chunk_count === 1 ? "" : "s"}
              {doc.subject ? ` · topic map saved as “${doc.subject}”` : ""}
            </span>
          </span>
        )}

        {mode !== "rename" ? (
          <KebabMenu
            label={`Actions for ${doc.filename}`}
            items={[
              { label: "View details", onSelect: () => open("details") },
              { label: "Rename", onSelect: () => open("rename") },
              { label: "Delete", danger: true, onSelect: () => open("delete") },
            ]}
          />
        ) : null}
      </div>

      {error ? (
        <div className="mt-3">
          <ErrorBanner message={error} />
        </div>
      ) : null}
      {mode === "details" ? <DetailsPanel documentId={doc.id} onClose={() => setMode("idle")} /> : null}
      {mode === "delete" ? (
        <ConfirmDelete
          message={`Delete “${doc.filename}”? ${deleteWarning(doc.type)}`}
          busy={busy}
          onConfirm={handleDelete}
          onCancel={() => setMode("idle")}
        />
      ) : null}
    </li>
  );
}

type FolderMode = "idle" | "details" | "delete";

function FolderSection({
  type,
  docs,
  onChanged,
}: {
  type: DocumentType;
  docs: DocumentRecord[];
  onChanged: () => void;
}) {
  const { reload: reloadSyllabi } = useSyllabi();
  const [mode, setMode] = useState<FolderMode>("idle");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const folder = FOLDERS.find((f) => f.value === type);
  const chunks = docs.reduce((sum, doc) => sum + doc.chunk_count, 0);

  async function handleDeleteAll() {
    setBusy(true);
    setError(null);
    try {
      for (const doc of docs) await api.deleteDocument(doc.id);
      setMode("idle");
    } catch (err) {
      setError(toMessage(err));
    } finally {
      setBusy(false);
      onChanged();
      reloadSyllabi();
    }
  }

  return (
    <section aria-label={`${folder?.label} folder`}>
      <div className="mb-2 flex items-center justify-between gap-3">
        <div className="min-w-0">
          <h3 className="flex items-center gap-2 text-sm font-semibold">
            <span aria-hidden>📁</span>
            {folder?.label}
            <span className="rounded-full bg-surface-muted px-2 py-0.5 text-xs font-medium text-muted">
              {docs.length} file{docs.length === 1 ? "" : "s"}
            </span>
          </h3>
          <p className="text-xs text-muted">{folder?.hint}</p>
        </div>
        <KebabMenu
          label={`Actions for the ${folder?.label} folder`}
          items={[
            { label: "View details", onSelect: () => setMode("details") },
            ...(docs.length > 0
              ? [{ label: "Delete all files", danger: true, onSelect: () => setMode("delete") }]
              : []),
          ]}
        />
      </div>

      {error ? (
        <div className="mb-2">
          <ErrorBanner message={error} />
        </div>
      ) : null}

      {mode === "details" ? (
        <div className="mb-2 rounded-lg bg-surface-muted p-4">
          <dl className="grid grid-cols-2 gap-4 sm:grid-cols-3">
            <Stat label="Files" value={docs.length} />
            <Stat label="Searchable chunks" value={chunks} />
            <Stat
              label="Last upload"
              value={docs.length ? new Date(docs[0].created_at).toLocaleDateString() : "—"}
            />
          </dl>
          <button
            onClick={() => setMode("idle")}
            className="mt-3 text-xs text-muted underline hover:text-foreground"
          >
            Close
          </button>
        </div>
      ) : null}
      {mode === "delete" ? (
        <div className="mb-2">
          <ConfirmDelete
            message={`Delete all ${docs.length} file${docs.length === 1 ? "" : "s"} in the ${folder?.label} folder, and everything built from them?`}
            busy={busy}
            onConfirm={handleDeleteAll}
            onCancel={() => setMode("idle")}
          />
        </div>
      ) : null}

      {docs.length === 0 ? (
        <p className="rounded-lg border border-dashed border-border px-4 py-3 text-sm text-muted">
          Empty — upload a file with “{folder?.label}” selected to put it here.
        </p>
      ) : (
        <ul className="space-y-2">
          {docs.map((doc) => (
            <FileRow key={doc.id} doc={doc} onChanged={onChanged} />
          ))}
        </ul>
      )}
    </section>
  );
}

export default function UploadPage() {
  const fetchDocuments = useCallback(() => api.listDocuments(), []);
  const { data: documents, loading, error, reload } = useApiData(fetchDocuments);

  const [file, setFile] = useState<File | null>(null);
  // Bumping the key remounts the file input, which is how a native file input is cleared.
  const [fileInputKey, setFileInputKey] = useState(0);
  const [docType, setDocType] = useState<DocumentType>("syllabus");
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);

  async function handleUpload(event: React.FormEvent) {
    event.preventDefault();
    if (!file) return;

    setUploading(true);
    setUploadError(null);
    setResult(null);
    try {
      const response = await api.uploadDocument(file, docType);
      setResult(
        `Saved “${response.document.filename}” to the ${folderLabel(response.document.type)} folder ` +
          `(${response.chunks_created} searchable chunks).`,
      );
      setFile(null);
      setFileInputKey((key) => key + 1);
      reload();
    } catch (err) {
      setUploadError(toMessage(err));
    } finally {
      setUploading(false);
    }
  }

  return (
    <>
      <PageHeader
        title="Upload your material"
        subtitle="Everything GapFinder tests you on comes from these files — nothing else."
      />

      <Card className="mb-8">
        <form onSubmit={handleUpload} className="space-y-5">
          {uploadError ? <ErrorBanner message={uploadError} /> : null}
          {result ? (
            <p className="rounded-lg border border-strong/30 bg-strong-soft px-4 py-3 text-sm text-strong">
              {result}
            </p>
          ) : null}

          <Field label="1. Choose a folder" hint="Your file is saved into the folder you pick.">
            <div className="grid gap-2 sm:grid-cols-2">
              {FOLDERS.map((option) => (
                <label
                  key={option.value}
                  className={`flex cursor-pointer items-start gap-3 rounded-lg border p-3 text-sm transition-colors ${
                    docType === option.value
                      ? "border-brand bg-brand-soft"
                      : "border-border hover:bg-surface-muted"
                  }`}
                >
                  <input
                    type="radio"
                    name="doc_type"
                    className="mt-0.5 accent-brand"
                    checked={docType === option.value}
                    onChange={() => setDocType(option.value)}
                  />
                  <span>
                    <span className="block font-medium">📁 {option.label}</span>
                    <span className="block text-xs text-muted">{option.hint}</span>
                  </span>
                </label>
              ))}
            </div>
          </Field>

          <Field label="2. Choose a file" hint="PDF works best — page numbers are kept for citations. Plain .txt also works.">
            <input
              key={fileInputKey}
              type="file"
              accept=".pdf,.txt"
              required
              className={inputClass}
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
          </Field>

          <Button type="submit" disabled={!file || uploading}>
            {uploading ? "Saving…" : `Save to ${folderLabel(docType)} folder`}
          </Button>
        </form>
      </Card>

      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted">
        Your material
      </h2>

      {loading && !documents ? <Spinner /> : null}
      {error ? <ErrorBanner message={error} /> : null}

      {documents ? (
        <div className="space-y-8">
          {FOLDERS.map((folder) => (
            <FolderSection
              key={folder.value}
              type={folder.value}
              docs={documents.filter((doc) => doc.type === folder.value)}
              onChanged={reload}
            />
          ))}
        </div>
      ) : null}
    </>
  );
}
