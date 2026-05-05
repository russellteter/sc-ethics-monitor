interface Props {
  title: string;
  sub?: string;
}

export default function EmptyState({ title, sub }: Props) {
  return (
    <div className="px-4 py-12 text-center text-sm text-slate-500">
      <div className="text-base font-semibold text-slate-700 mb-1">{title}</div>
      {sub && <div>{sub}</div>}
    </div>
  );
}
