import { useState, useCallback } from 'react';
import type { Coordinates } from '../utils/navigation';

export interface UseUserLocationResult {
  location: Coordinates | null;
  isLocating: boolean;
  error: string | null;
  requestLocation: () => void;
  clearLocation: () => void;
}

export function useUserLocation(): UseUserLocationResult {
  const [location, setLocation] = useState<Coordinates | null>(null);
  const [isLocating, setIsLocating] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const requestLocation = useCallback(() => {
    if (!navigator.geolocation) {
      setError('Geolocation is not supported by your browser.');
      return;
    }

    setIsLocating(true);
    setError(null);

    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLocation({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
        });
        setIsLocating(false);
        setError(null);
      },
      (err) => {
        setIsLocating(false);
        switch (err.code) {
          case err.PERMISSION_DENIED:
            setError('Location permission denied. Enable location access to view real distances.');
            break;
          case err.POSITION_UNAVAILABLE:
            setError('Location information is currently unavailable.');
            break;
          case err.TIMEOUT:
            setError('Location request timed out. Please try again.');
            break;
          default:
            setError('An error occurred while retrieving your location.');
            break;
        }
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 60000, // Cache for 1 minute to avoid repeated device sensor wakes
      }
    );
  }, []);

  const clearLocation = useCallback(() => {
    setLocation(null);
    setError(null);
    setIsLocating(false);
  }, []);

  return {
    location,
    isLocating,
    error,
    requestLocation,
    clearLocation,
  };
}
