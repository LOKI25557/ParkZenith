import React, { useEffect, useRef, useMemo } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import type { Facility, Availability } from '../../types';
import { calculateHaversineDistanceKm, getDirectionsUrl, type Coordinates } from '../../utils/navigation';
import { MapPin, Compass, Crosshair } from 'lucide-react';

export interface ParkingMapProps {
  facilities: Facility[];
  selectedFacilityId?: number | null;
  onFacilitySelect?: (facility: Facility) => void;
  availabilities?: Record<number, Availability>;
  userLocation?: Coordinates | null;
  onRequestUserLocation?: () => void;
  isLocating?: boolean;
  height?: string | number;
  interactive?: boolean;
  showControls?: boolean;
  singleFacilityMode?: boolean;
  className?: string;
  emptyMessage?: string;
}

const DEFAULT_CENTER: [number, number] = [12.9716, 77.5946]; // Default to urban tech hub coordinates
const DEFAULT_ZOOM = 13;

export const ParkingMap: React.FC<ParkingMapProps> = ({
  facilities,
  selectedFacilityId,
  onFacilitySelect,
  availabilities = {},
  userLocation,
  onRequestUserLocation,
  isLocating = false,
  height = '100%',
  interactive = true,
  showControls = true,
  singleFacilityMode = false,
  className = '',
  emptyMessage = 'No facility geographic coordinates available to display on map.',
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const markersLayerRef = useRef<L.LayerGroup | null>(null);
  const userMarkerRef = useRef<L.Marker | null>(null);

  // Filter facilities with valid coordinates
  const validFacilities = useMemo(() => {
    return facilities.filter(
      (f) =>
        f.latitude != null &&
        f.longitude != null &&
        !isNaN(Number(f.latitude)) &&
        !isNaN(Number(f.longitude)) &&
        Number(f.latitude) >= -90 &&
        Number(f.latitude) <= 90 &&
        Number(f.longitude) >= -180 &&
        Number(f.longitude) <= 180
    );
  }, [facilities]);

  // Initialize Map
  useEffect(() => {
    if (!mapContainerRef.current) return;

    // Cleanup existing instance if any
    if (mapInstanceRef.current) {
      mapInstanceRef.current.remove();
      mapInstanceRef.current = null;
    }

    const tileUrl =
      import.meta.env.VITE_MAP_TILE_URL ||
      'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png';
    const tileAttribution =
      import.meta.env.VITE_MAP_ATTRIBUTION ||
      '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>';

    const map = L.map(mapContainerRef.current, {
      center: DEFAULT_CENTER,
      zoom: DEFAULT_ZOOM,
      zoomControl: false,
      attributionControl: false,
      dragging: interactive,
      touchZoom: interactive,
      scrollWheelZoom: interactive ? 'center' : false,
      doubleClickZoom: interactive,
      boxZoom: interactive,
    });

    // Dark Matter tile layer matching ParkZenith aesthetic
    L.tileLayer(tileUrl, {
      subdomains: 'abcd',
      maxZoom: 19,
      attribution: tileAttribution,
    }).addTo(map);

    // Subtle attribution in bottom right
    L.control
      .attribution({
        position: 'bottomright',
        prefix: false,
      })
      .addTo(map);

    const markersLayer = L.layerGroup().addTo(map);
    markersLayerRef.current = markersLayer;
    mapInstanceRef.current = map;

    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
  }, [interactive]);

  // Update Markers when facilities or availabilities change
  useEffect(() => {
    const map = mapInstanceRef.current;
    const markersLayer = markersLayerRef.current;
    if (!map || !markersLayer) return;

    markersLayer.clearLayers();

    if (validFacilities.length === 0) return;

    const bounds = L.latLngBounds([]);

    validFacilities.forEach((facility) => {
      const lat = Number(facility.latitude);
      const lon = Number(facility.longitude);
      const isSelected = selectedFacilityId === facility.id;

      bounds.extend([lat, lon]);

      const avail = availabilities[facility.id];
      const availableCount = avail?.available;
      const totalCount = avail?.total_slots ?? facility.total_slots ?? 0;
      const occPct =
        avail?.occupancy_percentage ??
        (totalCount > 0 && availableCount !== undefined
          ? Math.round(((totalCount - availableCount) / totalCount) * 100)
          : 0);

      // Status color logic
      const isFull = availableCount !== undefined && availableCount <= 0;
      const isWarning = occPct >= 80;
      const badgeBg = isFull ? '#F43F5E' : isWarning ? '#F59E0B' : '#10B981';
      const badgeText = availableCount !== undefined ? `${availableCount} bays` : 'OPEN';

      // Custom HTML Marker matching ParkZenith Neon Theme
      const iconHtml = `
        <div class="pz-map-marker-container ${isSelected ? 'selected' : ''}" style="
          position: relative;
          display: flex;
          flex-direction: column;
          align-items: center;
          cursor: pointer;
          transform: translate(-50%, -100%);
        ">
          <!-- Availability Pill -->
          <div style="
            background-color: #090B10;
            border: 1px solid ${isSelected ? '#00E5FF' : badgeBg};
            color: #FFFFFF;
            padding: 2px 7px;
            border-radius: 9999px;
            font-size: 10px;
            font-weight: 700;
            font-family: monospace;
            white-space: nowrap;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.6);
            display: flex;
            align-items: center;
            gap: 4px;
            margin-bottom: 2px;
            transition: all 0.2s ease;
          ">
            <span style="width: 5px; height: 5px; border-radius: 50%; background-color: ${badgeBg};"></span>
            ${badgeText}
          </div>

          <!-- Pin Icon -->
          <div style="
            width: ${isSelected ? '32px' : '26px'};
            height: ${isSelected ? '32px' : '26px'};
            border-radius: 50% 50% 50% 0;
            background: ${isSelected ? 'linear-gradient(135deg, #1A5BFF 0%, #00E5FF 100%)' : '#1E2330'};
            border: 2px solid ${isSelected ? '#00E5FF' : 'rgba(255, 255, 255, 0.2)'};
            transform: rotate(-45deg);
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: ${isSelected ? '0 0 16px rgba(0, 229, 255, 0.6)' : '0 4px 10px rgba(0, 0, 0, 0.4)'};
            transition: all 0.25s ease;
          ">
            <div style="
              width: 8px;
              height: 8px;
              border-radius: 50%;
              background-color: #FFFFFF;
              transform: rotate(45deg);
            "></div>
          </div>
        </div>
      `;

      const customIcon = L.divIcon({
        html: iconHtml,
        className: 'pz-custom-marker',
        iconSize: [32, 48],
        iconAnchor: [16, 48],
        popupAnchor: [0, -48],
      });

      const marker = L.marker([lat, lon], {
        icon: customIcon,
        zIndexOffset: isSelected ? 1000 : 100,
      });

      // Compute real distance if userLocation is available
      const distanceKm = userLocation
        ? calculateHaversineDistanceKm(userLocation, { latitude: lat, longitude: lon })
        : null;

      const directionsUrl = getDirectionsUrl(facility, userLocation);

      // Custom styled dark popup
      const popupContent = `
        <div style="
          background-color: #0F131E;
          color: #FFFFFF;
          padding: 14px;
          border-radius: 12px;
          border: 1px solid rgba(0, 229, 255, 0.25);
          box-shadow: 0 16px 36px rgba(0, 0, 0, 0.8);
          font-family: inherit;
          min-width: 220px;
        ">
          <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; margin-bottom: 6px;">
            <h4 style="margin: 0; font-size: 14px; font-weight: 700; color: #FFFFFF; line-height: 1.3;">
              ${facility.name}
            </h4>
            <span style="
              font-size: 10px;
              font-weight: 700;
              padding: 2px 6px;
              border-radius: 4px;
              background-color: ${facility.is_active ? 'rgba(16, 185, 129, 0.2)' : 'rgba(244, 63, 94, 0.2)'};
              color: ${facility.is_active ? '#10B981' : '#F43F5E'};
            ">
              ${facility.is_active ? 'OPEN' : 'CLOSED'}
            </span>
          </div>

          <p style="margin: 0 0 8px 0; font-size: 11px; color: #94A3B8; line-height: 1.4;">
            ${facility.address}${facility.city ? `, ${facility.city}` : ''}
          </p>

          <!-- Live metrics -->
          <div style="
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 6px;
            background: rgba(255, 255, 255, 0.03);
            padding: 8px;
            border-radius: 8px;
            margin-bottom: 10px;
            border: 1px solid rgba(255, 255, 255, 0.06);
          ">
            <div>
              <span style="display: block; font-size: 9px; color: #64748B; text-transform: uppercase;">Available</span>
              <strong style="font-size: 13px; color: #10B981; font-family: monospace;">
                ${availableCount !== undefined ? `${availableCount} bays` : 'Live telemetry'}
              </strong>
            </div>
            <div>
              <span style="display: block; font-size: 9px; color: #64748B; text-transform: uppercase;">Occupancy</span>
              <strong style="font-size: 13px; color: #00E5FF; font-family: monospace;">
                ${occPct}%
              </strong>
            </div>
          </div>

          ${
            distanceKm !== null
              ? `<div style="display: flex; align-items: center; gap: 4px; font-size: 11px; color: #00E5FF; margin-bottom: 10px;">
                  <span>📍 Real distance: <strong>${distanceKm} km</strong> away</span>
                </div>`
              : ''
          }

          <div style="display: flex; gap: 6px; margin-top: 8px;">
            <a
              href="${directionsUrl}"
              target="_blank"
              rel="noopener noreferrer"
              style="
                flex: 1;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                gap: 4px;
                background-color: rgba(0, 229, 255, 0.12);
                border: 1px solid rgba(0, 229, 255, 0.35);
                color: #00E5FF;
                padding: 6px 8px;
                border-radius: 6px;
                font-size: 11px;
                font-weight: 600;
                text-decoration: none;
                transition: background-color 0.15s;
              "
            >
              Navigate
            </a>
            <a
              href="/parking/${facility.id}"
              style="
                flex: 1;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                gap: 4px;
                background-color: #1A5BFF;
                border: 1px solid transparent;
                color: #FFFFFF;
                padding: 6px 8px;
                border-radius: 6px;
                font-size: 11px;
                font-weight: 600;
                text-decoration: none;
                transition: background-color 0.15s;
              "
            >
              View Bays
            </a>
          </div>
        </div>
      `;

      marker.bindPopup(popupContent, {
        className: 'pz-leaflet-popup',
        maxWidth: 280,
      });

      marker.on('click', () => {
        if (onFacilitySelect) {
          onFacilitySelect(facility);
        }
      });

      markersLayer.addLayer(marker);
    });

    // Auto-fit bounds if we have facilities and not in single-facility locked mode
    if (!singleFacilityMode && bounds.isValid() && validFacilities.length > 1) {
      map.fitBounds(bounds, { padding: [50, 50], maxZoom: 15 });
    }
  }, [validFacilities, selectedFacilityId, availabilities, userLocation, onFacilitySelect, singleFacilityMode]);

  // Center on selected facility when it changes
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map || selectedFacilityId == null) return;

    const targetFac = validFacilities.find((f) => f.id === selectedFacilityId);
    if (targetFac && targetFac.latitude != null && targetFac.longitude != null) {
      map.flyTo([Number(targetFac.latitude), Number(targetFac.longitude)], 15, {
        duration: 0.8,
      });
    }
  }, [selectedFacilityId, validFacilities]);

  // Update User Location marker
  useEffect(() => {
    const map = mapInstanceRef.current;
    if (!map) return;

    if (userMarkerRef.current) {
      map.removeLayer(userMarkerRef.current);
      userMarkerRef.current = null;
    }

    if (userLocation && userLocation.latitude != null && userLocation.longitude != null) {
      const userHtml = `
        <div style="position: relative; display: flex; align-items: center; justify-content: center; width: 24px; height: 24px;">
          <div style="
            position: absolute;
            width: 24px;
            height: 24px;
            border-radius: 50%;
            background-color: rgba(0, 229, 255, 0.25);
            animation: ping 1.5s cubic-bezier(0, 0, 0.2, 1) infinite;
          "></div>
          <div style="
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background-color: #00E5FF;
            border: 2px solid #FFFFFF;
            box-shadow: 0 0 10px #00E5FF;
          "></div>
        </div>
      `;

      const userIcon = L.divIcon({
        html: userHtml,
        className: 'pz-user-marker',
        iconSize: [24, 24],
        iconAnchor: [12, 12],
      });

      const userMarker = L.marker([userLocation.latitude, userLocation.longitude], {
        icon: userIcon,
        zIndexOffset: 9999,
      }).bindPopup(
        `<div style="background: #090B10; color: #00E5FF; font-weight: 700; font-size: 11px; padding: 4px 8px; border-radius: 6px;">📍 You Are Here</div>`,
        { className: 'pz-leaflet-popup' }
      );

      userMarker.addTo(map);
      userMarkerRef.current = userMarker;
    }
  }, [userLocation]);

  // Map Controls Helpers
  const handleZoomIn = () => mapInstanceRef.current?.zoomIn();
  const handleZoomOut = () => mapInstanceRef.current?.zoomOut();

  const handleFitAll = () => {
    const map = mapInstanceRef.current;
    if (!map || validFacilities.length === 0) return;
    const bounds = L.latLngBounds(
      validFacilities.map((f) => [Number(f.latitude), Number(f.longitude)])
    );
    if (userLocation) {
      bounds.extend([userLocation.latitude, userLocation.longitude]);
    }
    map.fitBounds(bounds, { padding: [50, 50], maxZoom: 16 });
  };

  const handleCenterUser = () => {
    if (userLocation && mapInstanceRef.current) {
      mapInstanceRef.current.flyTo([userLocation.latitude, userLocation.longitude], 15, {
        duration: 0.8,
      });
    } else if (onRequestUserLocation) {
      onRequestUserLocation();
    }
  };

  return (
    <div
      style={{
        position: 'relative',
        width: '100%',
        height: typeof height === 'number' ? `${height}px` : height,
        borderRadius: '16px',
        overflow: 'hidden',
        border: '1px solid var(--pz-border-subtle)',
        backgroundColor: '#090B10',
      }}
      className={`pz-parking-map-wrapper ${className}`}
    >
      {/* Actual Leaflet Container */}
      <div
        ref={mapContainerRef}
        style={{
          width: '100%',
          height: '100%',
          zIndex: 1,
        }}
      />

      {/* Empty State Banner if no facilities have coordinates */}
      {validFacilities.length === 0 && (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            zIndex: 10,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: 'rgba(9, 11, 16, 0.85)',
            backdropFilter: 'blur(8px)',
            padding: '2rem',
            textAlign: 'center',
          }}
        >
          <MapPin size={32} color="var(--pz-text-muted)" style={{ marginBottom: '12px' }} />
          <h4 style={{ fontSize: '1rem', fontWeight: 600, color: '#FFFFFF', marginBottom: '4px' }}>
            Map View Unavailable
          </h4>
          <p style={{ fontSize: '0.8125rem', color: 'var(--pz-text-secondary)', maxWidth: '320px' }}>
            {emptyMessage}
          </p>
        </div>
      )}

      {/* Floating Control Toolbar */}
      {showControls && (
        <div
          style={{
            position: 'absolute',
            top: '12px',
            right: '12px',
            zIndex: 500,
            display: 'flex',
            flexDirection: 'column',
            gap: '6px',
          }}
        >
          {/* Zoom In */}
          <button
            type="button"
            onClick={handleZoomIn}
            aria-label="Zoom in on map"
            style={{
              width: '32px',
              height: '32px',
              borderRadius: '8px',
              backgroundColor: 'rgba(15, 19, 30, 0.85)',
              backdropFilter: 'blur(8px)',
              border: '1px solid var(--pz-border-subtle)',
              color: '#FFFFFF',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
              fontSize: '16px',
              fontWeight: 700,
              boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
            }}
          >
            +
          </button>

          {/* Zoom Out */}
          <button
            type="button"
            onClick={handleZoomOut}
            aria-label="Zoom out on map"
            style={{
              width: '32px',
              height: '32px',
              borderRadius: '8px',
              backgroundColor: 'rgba(15, 19, 30, 0.85)',
              backdropFilter: 'blur(8px)',
              border: '1px solid var(--pz-border-subtle)',
              color: '#FFFFFF',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
              fontSize: '16px',
              fontWeight: 700,
              boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
            }}
          >
            -
          </button>

          {/* Fit Bounds */}
          {validFacilities.length > 1 && (
            <button
              type="button"
              onClick={handleFitAll}
              aria-label="Fit all parking facilities on map"
              title="Fit all facilities"
              style={{
                width: '32px',
                height: '32px',
                borderRadius: '8px',
                backgroundColor: 'rgba(15, 19, 30, 0.85)',
                backdropFilter: 'blur(8px)',
                border: '1px solid var(--pz-border-subtle)',
                color: 'var(--pz-secondary)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                cursor: 'pointer',
                boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
              }}
            >
              <Compass size={16} />
            </button>
          )}

          {/* Geolocation Button */}
          {onRequestUserLocation && (
            <button
              type="button"
              onClick={handleCenterUser}
              aria-label="Find my location"
              title={userLocation ? 'Center on my location' : 'Locate my position'}
              disabled={isLocating}
              style={{
                width: '32px',
                height: '32px',
                borderRadius: '8px',
                backgroundColor: userLocation ? 'rgba(0, 229, 255, 0.2)' : 'rgba(15, 19, 30, 0.85)',
                backdropFilter: 'blur(8px)',
                border: userLocation ? '1px solid var(--pz-secondary)' : '1px solid var(--pz-border-subtle)',
                color: userLocation ? 'var(--pz-secondary)' : 'var(--pz-text-secondary)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                cursor: isLocating ? 'wait' : 'pointer',
                boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
              }}
            >
              <Crosshair size={16} className={isLocating ? 'animate-spin' : ''} />
            </button>
          )}
        </div>
      )}

      {/* Floating Status Pill (Top Left) */}
      <div
        style={{
          position: 'absolute',
          top: '12px',
          left: '12px',
          zIndex: 500,
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
        }}
      >
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            padding: '4px 10px',
            borderRadius: '9999px',
            backgroundColor: 'rgba(15, 19, 30, 0.85)',
            backdropFilter: 'blur(8px)',
            border: '1px solid var(--pz-border-subtle)',
            fontSize: '0.6875rem',
            fontFamily: 'var(--font-mono)',
            color: 'var(--pz-text-secondary)',
          }}
        >
          <span style={{ width: '6px', height: '6px', borderRadius: '50%', backgroundColor: 'var(--pz-secondary)' }} />
          <span>{validFacilities.length} Mapped Hubs</span>
        </div>
      </div>

      <style>{`
        .leaflet-popup-content-wrapper {
          background: transparent !important;
          box-shadow: none !important;
          padding: 0 !important;
        }
        .leaflet-popup-content {
          margin: 0 !important;
          line-height: inherit !important;
        }
        .leaflet-popup-tip {
          background: #0F131E !important;
          border: 1px solid rgba(0, 229, 255, 0.25) !important;
        }
        .leaflet-container {
          background-color: #090B10 !important;
          font-family: inherit !important;
        }
      `}</style>
    </div>
  );
};
