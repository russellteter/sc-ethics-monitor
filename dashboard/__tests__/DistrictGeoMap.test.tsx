import { describe, expect, it, vi } from "vitest";
import { fireEvent, render } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";
import type { FeatureCollection } from "geojson";
import DistrictGeoMap from "@/components/DistrictGeoMap";
import type { Candidate } from "@/lib/types";

const FIXTURE_GEOJSON: FeatureCollection = {
  type: "FeatureCollection",
  features: [
    {
      type: "Feature",
      geometry: {
        type: "Polygon",
        coordinates: [
          [
            [-80, 32],
            [-79, 32],
            [-79, 33],
            [-80, 33],
            [-80, 32],
          ],
        ],
      },
      properties: { SLDLST: "075", NAMELSAD: "State House District 75" },
    },
    {
      type: "Feature",
      geometry: {
        type: "Polygon",
        coordinates: [
          [
            [-79, 32],
            [-78, 32],
            [-78, 33],
            [-79, 33],
            [-79, 32],
          ],
        ],
      },
      properties: { SLDLST: "070", NAMELSAD: "State House District 70" },
    },
  ],
};

const FIXTURE_CANDIDATES: Candidate[] = [
  {
    id: "bauer-heather-75",
    name: "Heather Bauer",
    district: 75,
    party: "D",
    personId: "1",
    seiId: "2",
    officeId: "3",
    filing_status: "filed",
    latest_report: {
      reportId: "x",
      report_type: "Quarterly",
      period_label: "Q1 2026",
      filed_date: "2026-04-10",
      url: "u",
      period_raised: 1000,
      total_raised: 2000,
      cash_on_hand: 50000,
      is_amended: false,
    },
    history: [],
    last_error: null,
  },
];

describe("DistrictGeoMap", () => {
  it("renders one path per feature with district number as data attribute", () => {
    const { container } = render(
      <DistrictGeoMap
        geojson={FIXTURE_GEOJSON}
        candidates={FIXTURE_CANDIDATES}
        onSelect={vi.fn()}
      />,
    );
    const paths = container.querySelectorAll("path[data-district]");
    expect(paths).toHaveLength(2);
    const districts = Array.from(paths).map((p) => p.getAttribute("data-district"));
    expect(districts).toContain("75");
    expect(districts).toContain("70");
  });

  it("calls onSelect with candidate when path clicked", () => {
    const onSelect = vi.fn();
    const { container } = render(
      <DistrictGeoMap
        geojson={FIXTURE_GEOJSON}
        candidates={FIXTURE_CANDIDATES}
        onSelect={onSelect}
      />,
    );
    const path = container.querySelector('path[data-district="75"]');
    expect(path).not.toBeNull();
    fireEvent.click(path!);
    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect).toHaveBeenCalledWith(FIXTURE_CANDIDATES[0]);
  });

  it("does not fire onSelect for districts with no candidate", () => {
    const onSelect = vi.fn();
    const { container } = render(
      <DistrictGeoMap
        geojson={FIXTURE_GEOJSON}
        candidates={FIXTURE_CANDIDATES}
        onSelect={onSelect}
      />,
    );
    const empty = container.querySelector('path[data-district="70"]');
    fireEvent.click(empty!);
    expect(onSelect).not.toHaveBeenCalled();
  });

  it("colors district by COH tier", () => {
    const { container } = render(
      <DistrictGeoMap
        geojson={FIXTURE_GEOJSON}
        candidates={FIXTURE_CANDIDATES}
        onSelect={vi.fn()}
      />,
    );
    const filed = container.querySelector('path[data-district="75"]')!;
    const empty = container.querySelector('path[data-district="70"]')!;
    expect(filed.getAttribute("fill")).not.toBe(empty.getAttribute("fill"));
  });

  it("highlights selectedId with thicker stroke", () => {
    const { container } = render(
      <DistrictGeoMap
        geojson={FIXTURE_GEOJSON}
        candidates={FIXTURE_CANDIDATES}
        onSelect={vi.fn()}
        selectedId="bauer-heather-75"
      />,
    );
    const sel = container.querySelector('path[data-district="75"]')!;
    const unsel = container.querySelector('path[data-district="70"]')!;
    expect(Number(sel.getAttribute("stroke-width"))).toBeGreaterThan(
      Number(unsel.getAttribute("stroke-width")),
    );
  });

  it("shows tooltip on hover with district number", () => {
    const { container, getByText } = render(
      <DistrictGeoMap
        geojson={FIXTURE_GEOJSON}
        candidates={FIXTURE_CANDIDATES}
        onSelect={vi.fn()}
      />,
    );
    const path = container.querySelector('path[data-district="75"]')!;
    fireEvent.mouseEnter(path, { clientX: 50, clientY: 50 });
    expect(getByText("D-75")).toBeInTheDocument();
  });
});
