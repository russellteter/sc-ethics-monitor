"use client";

interface Props {
  active?: "house" | "senate";
}

export default function ChamberToggle({ active = "house" }: Props) {
  return (
    <div
      role="group"
      aria-label="Chamber"
      className="inline-flex bg-slate-100 rounded-lg p-1 text-sm"
    >
      <button
        type="button"
        aria-pressed={active === "house"}
        className={
          "px-4 py-1.5 rounded-md font-medium transition " +
          (active === "house"
            ? "bg-white text-slate-900 shadow-sm"
            : "text-slate-500 hover:text-slate-700")
        }
      >
        House
      </button>
      <button
        type="button"
        aria-pressed={false}
        disabled
        title="Senate view coming in v2"
        aria-label="Senate (coming in v2)"
        className="px-4 py-1.5 rounded-md font-medium text-slate-300 cursor-not-allowed"
      >
        Senate
      </button>
    </div>
  );
}
