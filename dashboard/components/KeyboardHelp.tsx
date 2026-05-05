"use client";
import { useEffect, useRef } from "react";

interface Props {
  open: boolean;
  onClose: () => void;
}

export default function KeyboardHelp({ open, onClose }: Props) {
  const closeBtnRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    const id = window.setTimeout(() => closeBtnRef.current?.focus(), 0);
    return () => {
      document.removeEventListener("keydown", onKey);
      window.clearTimeout(id);
    };
  }, [open, onClose]);

  if (!open) return null;
  return (
    <div
      className="fixed inset-0 bg-ink/40 z-50 flex items-center justify-center p-4"
      onClick={onClose}
      aria-hidden
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Keyboard shortcuts"
        className="glass-card rounded-xl p-6 max-w-sm w-full bg-white border border-slate-200"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="font-display font-bold text-lg mb-3 text-slate-900">
          Keyboard shortcuts
        </h2>
        <dl className="text-sm space-y-2">
          <Row label="Focus search" keyName="/" />
          <Row label="Open candidate" keyName="Enter" />
          <Row label="Close drawer / help" keyName="Esc" />
          <Row label="This help" keyName="?" />
        </dl>
        <button
          ref={closeBtnRef}
          type="button"
          onClick={onClose}
          className="mt-5 text-xs text-brand-deep underline focus:outline-none focus:ring-2 focus:ring-brand-primary/40 rounded"
        >
          Close
        </button>
      </div>
    </div>
  );
}

function Row({ label, keyName }: { label: string; keyName: string }) {
  return (
    <div className="flex justify-between items-center">
      <dt className="text-slate-900">{label}</dt>
      <dd>
        <kbd className="font-mono text-xs px-2 py-0.5 rounded border border-slate-200 bg-slate-50 text-slate-700">
          {keyName}
        </kbd>
      </dd>
    </div>
  );
}
