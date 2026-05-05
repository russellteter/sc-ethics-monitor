"use client";
import { MapContainer, TileLayer, GeoJSON } from "react-leaflet";
import type { Layer, PathOptions } from "leaflet";
import "leaflet/dist/leaflet.css";
import { useMemo } from "react";
import type { Feature, FeatureCollection } from "geojson";
import type { Candidate } from "@/lib/types";
import { cohTier, cohTierColor } from "@/lib/cohTier";
// @ts-expect-error — no .d.ts for geojson import, handled by webpack json loader
import districts from "@/public/data/sc-house-districts.geojson";
import MapLegend from "./MapLegend";

// SC bounding box
const SC_CENTER: [number, number] = [33.85, -80.85];
const SC_BOUNDS: [[number, number], [number, number]] = [
  [32.0, -83.5],
  [35.3, -78.5],
];

interface Props {
  candidates: Candidate[];
  onSelect: (c: Candidate) => void;
  selectedId: string | null;
}

export default function InnerLeafletMap({
  candidates,
  onSelect,
  selectedId,
}: Props) {
  const byDistrict = useMemo(
    () => new Map(candidates.map((c) => [c.district, c])),
    [candidates],
  );

  const styleFn = (f?: Feature): PathOptions => {
    const dnum = parseInt(
      (f?.properties?.SLDLST as string | undefined) ?? "0",
      10,
    );
    const c = byDistrict.get(dnum);
    const coh = c?.latest_report?.cash_on_hand ?? null;
    const fill = c ? cohTierColor(cohTier(coh)) : "var(--slate-100)";
    const isSel = c?.id === selectedId;
    return {
      fillColor: fill,
      color: isSel ? "#1e293b" : "#94a3b8",
      weight: isSel ? 2 : 0.5,
      fillOpacity: 0.85,
    };
  };

  const onEachFeature = (feature: Feature, layer: Layer) => {
    const dnum = parseInt(
      (feature.properties?.SLDLST as string | undefined) ?? "0",
      10,
    );
    const c = byDistrict.get(dnum);
    if (c) {
      (layer as any).on({ click: () => onSelect(c) });
    }
    const coh = c?.latest_report?.cash_on_hand;
    const cohStr = coh != null ? `$${coh.toLocaleString()}` : "No report";
    const tip = c
      ? `<strong>D-${dnum}</strong><br/>${c.name}<br/>COH: ${cohStr}`
      : `<strong>D-${dnum}</strong><br/>No Dem candidate`;
    (layer as any).bindTooltip(tip, { sticky: true });
  };

  return (
    <div className="glass-card overflow-hidden rounded-xl">
      <div className="px-4 py-3 border-b border-slate-200">
        <h3 className="font-semibold text-sm text-slate-900">
          SC House Districts
        </h3>
        <p className="text-xs text-slate-500 mt-0.5">
          124 districts · color = cash on hand
        </p>
      </div>
      <MapContainer
        center={SC_CENTER}
        zoom={7}
        maxBounds={SC_BOUNDS}
        style={{ height: 480, width: "100%" }}
        scrollWheelZoom={false}
        attributionControl={false}
      >
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
          attribution="&copy; OpenStreetMap &copy; CARTO"
        />
        <GeoJSON
          key={selectedId ?? "none"}
          data={districts as FeatureCollection}
          style={styleFn}
          onEachFeature={onEachFeature}
        />
      </MapContainer>
      <MapLegend />
    </div>
  );
}
