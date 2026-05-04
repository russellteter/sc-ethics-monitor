import type {
  Feature,
  FeatureCollection,
  MultiPolygon,
  Polygon,
  Position,
} from "geojson";

export type BBox = [number, number, number, number]; // [minLng, minLat, maxLng, maxLat]
export interface Dim {
  width: number;
  height: number;
}

/**
 * Compute the bounding box of a GeoJSON FeatureCollection, walking every
 * Polygon / MultiPolygon coordinate. Returns [minLng, minLat, maxLng, maxLat].
 */
export function computeBBox(fc: FeatureCollection): BBox {
  let minLng = Infinity;
  let minLat = Infinity;
  let maxLng = -Infinity;
  let maxLat = -Infinity;
  const each = (coord: Position) => {
    const [lng, lat] = coord;
    if (lng < minLng) minLng = lng;
    if (lng > maxLng) maxLng = lng;
    if (lat < minLat) minLat = lat;
    if (lat > maxLat) maxLat = lat;
  };
  for (const f of fc.features) {
    if (!f.geometry) continue;
    walkCoordinates(f.geometry as Polygon | MultiPolygon, each);
  }
  return [minLng, minLat, maxLng, maxLat];
}

function walkCoordinates(
  g: Polygon | MultiPolygon,
  fn: (c: Position) => void,
): void {
  if (g.type === "Polygon") {
    for (const ring of g.coordinates) {
      for (const c of ring) fn(c);
    }
  } else if (g.type === "MultiPolygon") {
    for (const poly of g.coordinates) {
      for (const ring of poly) {
        for (const c of ring) fn(c);
      }
    }
  }
}

/**
 * Project lng/lat to SVG x/y. Equirectangular projection with longitude
 * scaling compensated by cos(meanLat) so SC doesn't get visually squashed.
 * Padding (default 8px) leaves a small margin inside the viewBox.
 */
export function project(
  lng: number,
  lat: number,
  bbox: BBox,
  dim: Dim,
  padding = 8,
): [number, number] {
  const [minLng, minLat, maxLng, maxLat] = bbox;
  const dLng = maxLng - minLng;
  const dLat = maxLat - minLat;
  const innerW = dim.width - padding * 2;
  const innerH = dim.height - padding * 2;
  const aspect = Math.cos(((minLat + maxLat) / 2) * (Math.PI / 180));
  const scaleX = dLng > 0 ? innerW / (dLng * aspect) : innerW;
  const scaleY = dLat > 0 ? innerH / dLat : innerH;
  const scale = Math.min(scaleX, scaleY);
  const offsetX = (innerW - dLng * aspect * scale) / 2;
  const offsetY = (innerH - dLat * scale) / 2;
  const x = padding + offsetX + (lng - minLng) * aspect * scale;
  const y = padding + offsetY + (maxLat - lat) * scale; // flip Y so north is up
  return [x, y];
}

/**
 * Convert a Polygon or MultiPolygon Feature to an SVG path "d" string.
 * Each ring becomes an M ... L ... Z subpath.
 */
export function geoFeatureToPath(
  feat: Feature<Polygon | MultiPolygon>,
  bbox: BBox,
  dim: Dim,
): string {
  const ringToCmd = (ring: Position[]): string => {
    const points = ring.map(([lng, lat]) => project(lng, lat, bbox, dim));
    if (points.length === 0) return "";
    const head = points[0];
    const tail = points.slice(1);
    const m = `M${head[0].toFixed(2)},${head[1].toFixed(2)}`;
    const l = tail
      .map(([x, y]) => `L${x.toFixed(2)},${y.toFixed(2)}`)
      .join("");
    return `${m}${l}Z`;
  };
  if (feat.geometry.type === "Polygon") {
    return feat.geometry.coordinates.map(ringToCmd).join(" ");
  }
  // MultiPolygon
  return feat.geometry.coordinates
    .map((poly) => poly.map(ringToCmd).join(" "))
    .join(" ");
}

/**
 * Pull the SC House district number from a feature.
 * Census TIGER stores it as zero-padded string in `SLDLST` ("075", "070", etc.)
 */
export function districtNumberFromFeature(feat: Feature): number {
  const props = (feat.properties as Record<string, unknown> | null) ?? {};
  const sldlst = props.SLDLST;
  if (typeof sldlst === "string") return parseInt(sldlst, 10);
  return Number(sldlst);
}
