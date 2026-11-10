import path from "node:path";
import { loadEnvConfig } from "@next/env";
import type { NextConfig } from "next";

// The project keeps one .env at the repository root, shared with the backend.
// Next.js only reads .env files from its own folder (frontend/), so load the
// root one here. This runs before the app is compiled, so NEXT_PUBLIC_* values
// from it are inlined into the browser bundle as usual. Variables already set
// in the environment (e.g. on Vercel) are not overwritten, and a missing file
// is ignored.
loadEnvConfig(path.resolve(process.cwd(), ".."), process.env.NODE_ENV !== "production");

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
