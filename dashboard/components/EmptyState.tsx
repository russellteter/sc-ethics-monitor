interface Props {
  title: string;
  sub?: string;
}

export default function EmptyState({ title, sub }: Props) {
  return (
    <div className="px-4 py-12 text-center text-sm text-muted">
      <div className="font-display text-base text-ink mb-1">{title}</div>
      {sub && <div>{sub}</div>}
    </div>
  );
}
