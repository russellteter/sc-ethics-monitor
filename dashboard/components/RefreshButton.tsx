"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";

export default function RefreshButton() {
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const router = useRouter();

  async function onClick() {
    setBusy(true);
    setMsg(null);
    try {
      const r = await fetch("/api/refresh", { method: "POST" });
      if (r.status === 202) {
        setMsg("Refresh started — data updates in ~3 minutes");
        setTimeout(() => router.refresh(), 60_000);
      } else if (r.status === 429) {
        setMsg("Just refreshed — try again in a minute");
      } else {
        setMsg("Couldn't start refresh — try again later");
      }
    } catch {
      setMsg("Network error — try again");
    } finally {
      setBusy(false);
      setTimeout(() => setMsg(null), 6000);
    }
  }

  return (
    <div className="relative">
      <button
        onClick={onClick}
        disabled={busy}
        className="bg-teal-deep text-white px-4 py-2 rounded-md text-xs font-semibold disabled:opacity-60 hover:bg-ink"
        aria-label="Trigger data refresh"
      >
        {busy ? "Triggering…" : "↻ Refresh now"}
      </button>
      {msg && (
        <div className="absolute right-0 top-full mt-2 bg-ink text-white text-xs px-3 py-2 rounded-md shadow-lg whitespace-nowrap">
          {msg}
        </div>
      )}
    </div>
  );
}
