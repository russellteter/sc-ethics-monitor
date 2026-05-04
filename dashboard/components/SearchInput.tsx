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
      className="w-full px-3 py-2 text-sm border border-line rounded-md bg-card focus:outline-none focus:ring-2 focus:ring-teal-primary/40"
      aria-label="Search candidates"
    />
  );
}
