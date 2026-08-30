type GeoPoint = { lat: number; lon: number; accuracy: number }

export function formatGpsEvidence(point: GeoPoint): string {
  return `${point.lat.toFixed(5)}, ${point.lon.toFixed(5)} · ±${Math.round(point.accuracy)}m`
}
