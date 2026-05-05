interface Props {
  generatedAt: string | null;
}

export default function DataFreshnessBanner({ generatedAt }: Props) {
  return (
    <div className="text-right leading-tight">
      <div className="text-[11px] text-slate-500">Refreshes every Sunday at 11:00 PM ET</div>
      {generatedAt && (
        <div className="text-[11px] text-slate-400 tabular-nums">
          Last update{" "}
          {new Date(generatedAt).toLocaleDateString("en-US", {
            month: "short",
            day: "numeric",
          })}
          {" · "}
          {new Date(generatedAt).toLocaleTimeString("en-US", {
            hour: "numeric",
            minute: "2-digit",
          })}
        </div>
      )}
    </div>
  );
}
