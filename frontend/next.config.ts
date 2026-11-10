import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  // Both off by intent (they were create-next-app defaults).
  //
  // Protected routes are gated by a client-side auth check (JWT in
  // localStorage), so their page segments render nothing until the session
  // resolves. Next's instant-navigation validation therefore can never succeed
  // for them and logs an error for every protected route on every request. The
  // documented per-segment opt-out (`export const instant = false`) needs a
  // Server Component, and these pages are all "use client".
  //
  // Nothing here uses `use cache` or server-side data fetching -- every page is
  // a client component calling the FastAPI backend at runtime -- so neither
  // flag buys anything.
  cacheComponents: false,
  partialPrefetching: false,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
