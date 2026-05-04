import { describe, expect, it } from "vitest";
import {
  computeBBox,
  districtNumberFromFeature,
  geoFeatureToPath,
  project,
} from "@/lib/districtMap";
import type { Feature, FeatureCollection, Polygon } from "geojson";

describe("computeBBox", () => {
  it("returns [minLng, minLat, maxLng, maxLat] from FeatureCollection", () => {
    const fc: FeatureCollection = {
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
          properties: {},
        },
      ],
    };
    expect(computeBBox(fc)).toEqual([-80, 32, -79, 33]);
  });

  it("walks MultiPolygon coordinates", () => {
    const fc: FeatureCollection = {
      type: "FeatureCollection",
      features: [
        {
          type: "Feature",
          geometry: {
            type: "MultiPolygon",
            coordinates: [
              [
                [
                  [-83, 32],
                  [-82, 32],
                  [-82, 33],
                  [-83, 33],
                  [-83, 32],
                ],
              ],
              [
                [
                  [-79, 34],
                  [-78, 34],
                  [-78, 35],
                  [-79, 35],
                  [-79, 34],
                ],
              ],
            ],
          },
          properties: {},
        },
      ],
    };
    expect(computeBBox(fc)).toEqual([-83, 32, -78, 35]);
  });
});

describe("project", () => {
  it("maps lng/lat to SVG x/y within the viewBox", () => {
    const bbox: [number, number, number, number] = [-83.5, 32, -78.5, 35.2];
    const dim = { width: 400, height: 300 };
    const [x, y] = project(-81, 33.6, bbox, dim);
    expect(x).toBeGreaterThanOrEqual(0);
    expect(x).toBeLessThanOrEqual(400);
    expect(y).toBeGreaterThanOrEqual(0);
    expect(y).toBeLessThanOrEqual(300);
  });

  it("flips Y axis (max lat → top of svg)", () => {
    const bbox: [number, number, number, number] = [-80, 32, -79, 33];
    const dim = { width: 100, height: 100 };
    const [, yTop] = project(-79.5, 33, bbox, dim);
    const [, yBottom] = project(-79.5, 32, bbox, dim);
    expect(yTop).toBeLessThan(yBottom);
  });
});

describe("geoFeatureToPath", () => {
  it("emits an SVG path string for a Polygon feature", () => {
    const feat: Feature<Polygon> = {
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
      properties: {},
    };
    const bbox: [number, number, number, number] = [-80, 32, -79, 33];
    const path = geoFeatureToPath(feat, bbox, { width: 100, height: 100 });
    expect(path).toMatch(/^M/);
    expect(path).toMatch(/Z$/);
    // Polygon has 5 points, expect 4 L commands plus initial M
    expect((path.match(/L/g) || []).length).toBe(4);
  });
});

describe("districtNumberFromFeature", () => {
  it("parses zero-padded SLDLST string", () => {
    const feat = {
      type: "Feature" as const,
      geometry: { type: "Polygon" as const, coordinates: [] },
      properties: { SLDLST: "075" },
    };
    expect(districtNumberFromFeature(feat as unknown as Feature)).toBe(75);
  });

  it("handles numeric SLDLST", () => {
    const feat = {
      type: "Feature" as const,
      geometry: { type: "Polygon" as const, coordinates: [] },
      properties: { SLDLST: 70 },
    };
    expect(districtNumberFromFeature(feat as unknown as Feature)).toBe(70);
  });
});
