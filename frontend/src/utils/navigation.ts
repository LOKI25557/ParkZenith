import type { Facility } from '../types';

export interface Coordinates {
  latitude: number;
  longitude: number;
}

/**
 * Calculates the real great-circle distance between two geographic coordinates using the Haversine formula.
 * Returns distance in kilometers rounded to 1 decimal place, or null if coordinates are invalid.
 */
export function calculateHaversineDistanceKm(
  coord1: Coordinates,
  coord2: Coordinates
): number | null {
  if (
    coord1.latitude == null ||
    coord1.longitude == null ||
    coord2.latitude == null ||
    coord2.longitude == null
  ) {
    return null;
  }

  const R = 6371; // Earth's mean radius in km
  const dLat = ((coord2.latitude - coord1.latitude) * Math.PI) / 180;
  const dLon = ((coord2.longitude - coord1.longitude) * Math.PI) / 180;
  const lat1 = (coord1.latitude * Math.PI) / 180;
  const lat2 = (coord2.latitude * Math.PI) / 180;

  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.sin(dLon / 2) * Math.sin(dLon / 2) * Math.cos(lat1) * Math.cos(lat2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

  return Math.round(R * c * 10) / 10;
}

/**
 * Generates an external navigation URL to open real directions in Google Maps.
 * Uses exact coordinates when available; falls back cleanly to the real physical address.
 */
export function getDirectionsUrl(
  facility: Pick<Facility, 'name' | 'address' | 'city' | 'latitude' | 'longitude'>,
  userLocation?: Coordinates | null
): string {
  const hasCoords = facility.latitude != null && facility.longitude != null;

  let destination = '';
  if (hasCoords) {
    destination = `${facility.latitude},${facility.longitude}`;
  } else {
    const parts = [facility.name, facility.address, facility.city].filter(Boolean);
    destination = encodeURIComponent(parts.join(', '));
  }

  const originParam =
    userLocation?.latitude != null && userLocation?.longitude != null
      ? `&origin=${userLocation.latitude},${userLocation.longitude}`
      : '';

  return `https://www.google.com/maps/dir/?api=1&destination=${destination}${originParam}`;
}

/**
 * Generates Apple Maps navigation URL.
 */
export function getAppleMapsUrl(
  facility: Pick<Facility, 'name' | 'address' | 'city' | 'latitude' | 'longitude'>,
  userLocation?: Coordinates | null
): string {
  const hasCoords = facility.latitude != null && facility.longitude != null;
  const saddr = userLocation ? `&saddr=${userLocation.latitude},${userLocation.longitude}` : '';

  if (hasCoords) {
    return `https://maps.apple.com/?daddr=${facility.latitude},${facility.longitude}&q=${encodeURIComponent(facility.name || 'Parking')}${saddr}`;
  }

  const query = encodeURIComponent([facility.name, facility.address, facility.city].filter(Boolean).join(', '));
  return `https://maps.apple.com/?daddr=${query}${saddr}`;
}

/**
 * Generates OpenStreetMap URL centered on facility coordinates.
 */
export function getOpenStreetMapUrl(
  facility: Pick<Facility, 'latitude' | 'longitude'>
): string | null {
  if (facility.latitude == null || facility.longitude == null) return null;
  return `https://www.openstreetmap.org/?mlat=${facility.latitude}&mlon=${facility.longitude}#map=16/${facility.latitude}/${facility.longitude}`;
}
