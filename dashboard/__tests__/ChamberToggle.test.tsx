import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import ChamberToggle from "@/components/ChamberToggle";

describe("ChamberToggle", () => {
  it("renders House and Senate buttons", () => {
    render(<ChamberToggle />);
    expect(screen.getByRole("button", { name: /^House$/i })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /senate.*coming.*v2/i }),
    ).toBeInTheDocument();
  });

  it("marks House as pressed by default", () => {
    render(<ChamberToggle />);
    const house = screen.getByRole("button", { name: /^House$/i });
    expect(house).toHaveAttribute("aria-pressed", "true");
  });

  it("disables Senate with a tooltip", () => {
    render(<ChamberToggle />);
    const senate = screen.getByRole("button", {
      name: /senate.*coming.*v2/i,
    });
    expect(senate).toBeDisabled();
    expect(senate).toHaveAttribute("title", "Senate view coming in v2");
  });
});
