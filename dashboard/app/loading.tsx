export default function Loading() {
  return (
    <div className="max-w-page mx-auto px-6 lg:px-8 py-6">
      <div className="h-16 bg-card border border-line rounded-lg mb-6 animate-pulse" />
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 mb-5">
        {Array.from({ length: 5 }).map((_, i) => (
          <div
            key={i}
            className="h-24 bg-card border border-line rounded-lg animate-pulse"
          />
        ))}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-4">
        <div className="h-96 bg-card border border-line rounded-lg animate-pulse" />
        <div className="hidden lg:block h-96 bg-card border border-line rounded-lg animate-pulse" />
      </div>
      <span className="sr-only" role="status" aria-live="polite">
        Loading dashboard data
      </span>
    </div>
  );
}
