"use client";

import { createContext, useCallback, useContext, useMemo } from "react";

import { api } from "./api";
import type { SyllabusSummary } from "./types";
import { useApiData } from "./useApiData";

interface SyllabiState {
  /** Syllabi whose topic map has been saved; each is a sidebar shortcut. */
  syllabi: SyllabusSummary[];
  /** Re-fetch after saving a topic map or deleting a syllabus. */
  reload: () => void;
}

const SyllabiContext = createContext<SyllabiState | null>(null);

/** Mount only once the user is signed in -- it calls an authenticated endpoint. */
export function SyllabiProvider({ children }: { children: React.ReactNode }) {
  const fetchSyllabi = useCallback(() => api.listSyllabi(), []);
  const { data, reload } = useApiData(fetchSyllabi);

  const value = useMemo(() => ({ syllabi: data ?? [], reload }), [data, reload]);
  return <SyllabiContext.Provider value={value}>{children}</SyllabiContext.Provider>;
}

export function useSyllabi(): SyllabiState {
  const context = useContext(SyllabiContext);
  if (!context) throw new Error("useSyllabi must be used inside <SyllabiProvider>");
  return context;
}

/** "Physics" -> "Physics Syllabus"; leaves names that already say so alone. */
export function syllabusLabel(subject: string): string {
  return /syllabus\s*$/i.test(subject) ? subject : `${subject} Syllabus`;
}
