"use client";
import { useEffect, useState } from "react";

interface Props {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}

export default function SearchInput({ value, onChange, placeholder }: Props) {
  const [local, setLocal] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => onChange(local), 150);
    return () => clearTimeout(t);
  }, [local, onChange]);
  return (
    <input
      value={local}
      onChange={(e) => setLocal(e.target.value)}
      placeholder={placeholder ?? "Search by name or district…"}
      className="w-full px-3 py-2 text-sm border border-slate-200 rounded-md bg-white focus:outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20"
      aria-label="Search candidates"
    />
  );
}
