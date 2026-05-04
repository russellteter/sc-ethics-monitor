"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import type { Feature, FeatureCollection, MultiPolygon, Polygon } from "geojson";
import { Candidate } from "@/lib/types";
import { cohTier, cohTierColor } from "@/lib/cohTier";
import {
  computeBBox,
  districtNumberFromFeature,
  geoFeatureToPath,
} from "@/lib/districtMap";
import Legend from "./Legend";
import MapTooltip from "./MapTooltip";

interface Props {
  geojson?: FeatureCollection;
  candidates: Candidate[];
  onSelect: (c: Candidate) => void;
  selectedId?: string | null;
}

const VIEWBOX_W = 480;
const VIEWBOX_H = 560;
const EMPTY_FILL = "#F1F5F9"; // slate-100
const HOVER_STROKE = "#1A4A45"; // teal-deep
const DEFAULT_STROKE = "#94A3B8"; // slate-400
const SELECTED_STROKE_WIDTH = 2;
const DEFAULT_STROKE_WIDTH = 0.5;

export default function DistrictGeoMap({
  geojson,
  candidates,
  onSelect,
  selectedId,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [data, setData] = useState<FeatureCollection | null>(geojson ?? null);
  const [hovered, setHovered] = useState<{
    district: number;
    x: number;
    y: number;
  } | null>(null);

  useEffect(() => {
    if (geojson) {
      setData(geojson);
      return;
    }
    let cancelled = false;
    fetch("/data/sc-house-districts.geojson")
      .then((r) => r.json())
      .then((j: FeatureCollection) => {
        if (!cancelled) setData(j);
      })
      .catch((e) => {
        // eslint-disable-next-line no-console
        console.error("Failed to load district GeoJSON", e);
      });
    return () => {
      cancelled = true;
    };
  }, [geojson]);

  const byDistrict = useMemo(() => {
    const m = new Map<number, Candidate>();
    for (const c of candidates) m.set(c.district, c);
    return m;
  }, [candidates]);

  const dim = { width: VIEWBOX_W, height: VIEWBOX_H };

  const paths = useMemo(() => {
    if (!data) return [];
    const bbox = computeBBox(data);
    return data.features.map((f) => {
      const district = districtNumberFromFeature(f);
      const candidate = byDistrict.get(district) ?? null;
      const d = geoFeatureToPath(
        f as Feature<Polygon | MultiPolygon>,
        bbox,
        dim,
      );
      return { district, candidate, d };
    });
  }, [data, byDistrict]);

  if (!data) {
    return (
      <div className="bg-white border border-slate-200 rounded-xl shadow-sm p-4">
        <div
          className="h-[560px] bg-slate-50 rounded-md animate-pulse"
          aria-label="Loading district map"
        />
      </div>
    );
  }

  const handleHover = (
    district: number,
    e: React.MouseEvent<SVGPathElement>,
  ) => {
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return;
    setHovered({
      district,
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    });
  };

  return (
    <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
      <div className="px-4 py-3 border-b border-slate-200">
        <h3 className="font-display font-semibold text-sm text-slate-900">
          SC House Districts
        </h3>
        <p className="text-xs text-slate-500 mt-0.5">
          124 districts · color = cash on hand
        </p>
      </div>
      <div ref={containerRef} className="relative p-3">
        <svg
          viewBox={`0 0 ${VIEWBOX_W} ${VIEWBOX_H}`}
          className="w-full h-auto map-container"
          role="img"
          aria-label="Interactive SC House district map"
        >
          <g>
            {paths.map(({ district, candidate, d }) => {
              const tier = cohTier(candidate?.latest_report?.cash_on_hand ?? null);
              const fill = candidate ? cohTierColor(tier) : EMPTY_FILL;
              const isSelected =
                selectedId !== null &&
                selectedId !== undefined &&
                candidate?.id === selectedId;
              const strokeWidth = isSelected
                ? SELECTED_STROKE_WIDTH
                : DEFAULT_STROKE_WIDTH;
              const stroke = isSelected ? HOVER_STROKE : DEFAULT_STROKE;
              const interactive = candidate !== null;
              return (
                <path
                  key={district}
                  data-district={district}
                  d={d}
                  fill={fill}
                  stroke={stroke}
                  strokeWidth={strokeWidth}
                  tabIndex={interactive ? 0 : -1}
                  className={
                    "transition-[stroke-width,fill] duration-150 focus:outline-none " +
                    (interactive
                      ? "cursor-pointer hover:brightness-95"
                      : "cursor-default")
                  }
                  onMouseEnter={(e) => handleHover(district, e)}
                  onMouseMove={(e) => handleHover(district, e)}
                  onMouseLeave={() => setHovered(null)}
                  onClick={() => {
                    if (candidate) onSelect(candidate);
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && candidate) onSelect(candidate);
                  }}
                  aria-label={
                    candidate
                      ? `District ${district}, ${candidate.name}`
                      : `District ${district}, no candidate`
                  }
                />
              );
            })}
          </g>
        </svg>
        {hovered && (
          <MapTooltip
            districtNumber={hovered.district}
            candidate={byDistrict.get(hovered.district) ?? null}
            x={hovered.x}
            y={hovered.y}
          />
        )}
      </div>
      <Legend />
    </div>
  );
}
