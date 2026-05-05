"use client";
import { useEffect, useRef, useState } from "react";

interface Props {
  label: string;
  value: string;
  sub?: string;
  accent?: boolean;
  valueColor?: string;
}

export default function KPICard({
  label,
  value,
  sub,
  accent = false,
  valueColor,
}: Props) {
  const isNumeric = /^[\d,.\s$KM%]+$/.test(value);
  const rawNum = parseFloat(value.replace(/[^\d.]/g, "")) || 0;
  const [displayed, setDisplayed] = useState(isNumeric ? "0" : value);
  const animatedRef = useRef(false);

  useEffect(() => {
    if (!isNumeric || animatedRef.current) return;
    animatedRef.current = true;
    const start = performance.now();
    const dur = 600;
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / dur);
      const eased = 1 - Math.pow(1 - t, 3);
      const cur = Math.round(rawNum * eased);
      setDisplayed(value.replace(/[\d,]+/, cur.toLocaleString()));
      if (t < 1) requestAnimationFrame(tick);
      else setDisplayed(value);
    };
    requestAnimationFrame(tick);
  }, [value, isNumeric, rawNum]);

  const valClass =
    valueColor ?? (accent ? "text-brand-600" : "text-slate-900");

  return (
    <div
      data-accent={accent ? "true" : undefined}
      className="glass-card p-4 rounded-xl"
    >
      <div className="text-[11px] uppercase tracking-wider text-slate-500 mb-1.5">
        {label}
      </div>
      <div
        data-value={value}
        className={`text-[28px] leading-none font-bold tabular-nums ${valClass}`}
      >
        {displayed}
      </div>
      {sub && (
        <div className="text-[11px] text-slate-500 mt-1.5">{sub}</div>
      )}
    </div>
  );
}
