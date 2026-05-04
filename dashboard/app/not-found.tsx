import Link from "next/link";

export default function NotFound() {
  return (
    <div className="min-h-[60vh] flex items-center justify-center p-8">
      <div className="max-w-md w-full text-center bg-card border border-line rounded-lg shadow-card p-6">
        <h2 className="font-display text-xl font-bold mb-2 text-ink">
          Page not found
        </h2>
        <p className="text-sm text-muted mb-4">
          The page you're looking for doesn't exist.
        </p>
        <Link
          href="/"
          className="inline-block bg-teal-deep text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-teal-deep/90 focus:outline-none focus:ring-2 focus:ring-teal-primary/40"
        >
          Back to dashboard
        </Link>
      </div>
    </div>
  );
}
