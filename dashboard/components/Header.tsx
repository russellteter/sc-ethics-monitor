import { formatDate } from "@/lib/format";
import RefreshButton from "./RefreshButton";

interface Props {
  generatedAt: string | null;
  cycle: string;
}

export default function Header({ generatedAt, cycle }: Props) {
  return (
    <header className="sticky top-0 z-30 bg-card border-b border-line px-8 py-4 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <div
          className="w-8 h-8 rounded-lg"
          style={{ background: "linear-gradient(135deg, #1ED4C2, #1A4A45)" }}
        />
        <div>
          <h1 className="font-display text-lg font-bold tracking-tight">
            SC House Dem Finance
          </h1>
          <p className="text-xs text-muted">Locality AI · Q1 {cycle}</p>
        </div>
      </div>
      <div className="flex items-center gap-4 text-xs text-muted">
        <span>
          Last refreshed{" "}
          <span className="text-ink font-medium">
            {generatedAt ? formatDate(generatedAt.slice(0, 10)) : "—"}
            {generatedAt && (
              <>
                {" · "}
                {new Date(generatedAt).toLocaleTimeString("en-US", {
                  hour: "numeric",
                  minute: "2-digit",
                })}
              </>
            )}
          </span>
        </span>
        <RefreshButton />
      </div>
    </header>
  );
}
