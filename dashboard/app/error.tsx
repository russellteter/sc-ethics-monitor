"use client";
import { useEffect } from "react";

interface Props {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function Error({ error, reset }: Props) {
  useEffect(() => {
    // Surface the error in dev tools without leaking sensitive info to UI.
    console.error("Dashboard error boundary:", error);
  }, [error]);

  return (
    <div className="min-h-[60vh] flex items-center justify-center p-8">
      <div className="max-w-md w-full text-center bg-card border border-line rounded-lg shadow-card p-6">
        <h2 className="font-display text-xl font-bold mb-2 text-ink">
          Couldn't load data
        </h2>
        <p className="text-sm text-muted mb-4">
          {error?.message || "An unexpected error occurred."}
        </p>
        <button
          type="button"
          onClick={reset}
          className="bg-teal-deep text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-teal-deep/90 focus:outline-none focus:ring-2 focus:ring-teal-primary/40"
        >
          Try again
        </button>
      </div>
    </div>
  );
}
