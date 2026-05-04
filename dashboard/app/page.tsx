import Header from "@/components/Header";
import PageShell from "@/components/PageShell";
import { fetchHouseFinance } from "@/lib/data";

// Render at request time so the upstream JSON fetch isn't required during build.
export const dynamic = "force-dynamic";
export const revalidate = 60;

export default async function Page() {
  const artifact = await fetchHouseFinance();
  return (
    <>
      <Header generatedAt={artifact.generated_at} cycle={artifact.cycle} />
      <PageShell artifact={artifact} />
    </>
  );
}
