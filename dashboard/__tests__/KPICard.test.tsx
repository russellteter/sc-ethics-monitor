import { render, screen } from "@testing-library/react";
import KPICard from "@/components/KPICard";

describe("KPICard", () => {
  it("renders label, value, and sub", () => {
    const { container } = render(
      <KPICard label="Tracked" value="162" sub="Dem House candidates" />,
    );
    expect(screen.getByText("Tracked")).toBeInTheDocument();
    expect(screen.getByText("Dem House candidates")).toBeInTheDocument();
    expect(container.querySelector("[data-value='162']")).toBeTruthy();
  });

  it("renders without sub", () => {
    const { container } = render(<KPICard label="Filed" value="53" />);
    expect(screen.getByText("Filed")).toBeInTheDocument();
    expect(container.querySelector("[data-value='53']")).toBeTruthy();
  });

  it("applies data-accent attribute when accent=true", () => {
    const { container } = render(<KPICard label="X" value="1" accent />);
    expect(container.querySelector("[data-accent='true']")).toBeTruthy();
  });

  it("does not apply data-accent when accent=false", () => {
    const { container } = render(<KPICard label="X" value="1" />);
    expect(container.querySelector("[data-accent='true']")).toBeNull();
  });
});
