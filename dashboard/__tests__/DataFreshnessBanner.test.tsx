import { render, screen } from "@testing-library/react";
import DataFreshnessBanner from "@/components/DataFreshnessBanner";

describe("DataFreshnessBanner", () => {
  it("shows the cron schedule", () => {
    render(<DataFreshnessBanner generatedAt="2026-05-04T03:00:00Z" />);
    expect(screen.getByText(/Refreshes every Sunday at 11:00 PM ET/i)).toBeInTheDocument();
  });

  it("shows last update when generatedAt is provided", () => {
    render(<DataFreshnessBanner generatedAt="2026-05-04T03:00:00Z" />);
    expect(screen.getByText(/Last update/i)).toBeInTheDocument();
  });

  it("renders gracefully when generatedAt is null", () => {
    render(<DataFreshnessBanner generatedAt={null} />);
    expect(screen.getByText(/Refreshes every Sunday at 11:00 PM ET/i)).toBeInTheDocument();
    expect(screen.queryByText(/Last update/i)).not.toBeInTheDocument();
  });
});
