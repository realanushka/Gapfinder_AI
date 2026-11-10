"use client";

import { useCallback, useEffect, useState } from "react";

import { ApiError } from "./api";

export function toMessage(err: unknown): string {
  if (err instanceof ApiError) return err.message;
  return "Something went wrong. Please try again.";
}

interface ApiDataState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  reload: () => void;
  setData: (value: T | null) => void;
}

/**
 * Loads data on mount and exposes reload().
 *
 * `fetcher` must be wrapped in useCallback by the caller, since it is this
 * hook's effect dependency -- an inline arrow would refetch on every render.
 */
export function useApiData<T>(fetcher: () => Promise<T>): ApiDataState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  // Every setState below sits in a promise callback, so none of them run
  // synchronously during the effect -- which would cascade re-renders.
  useEffect(() => {
    let cancelled = false;

    fetcher()
      .then((result) => {
        if (cancelled) return;
        setData(result);
        setError(null);
      })
      .catch((err) => {
        if (!cancelled) setError(toMessage(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [fetcher, reloadKey]);

  // Called from event handlers, where setState is the normal thing to do.
  const reload = useCallback(() => {
    setLoading(true);
    setReloadKey((key) => key + 1);
  }, []);

  return { data, loading, error, reload, setData };
}
