import React, { useEffect, useState, useMemo, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { parkingApi } from '../api/parking';
import type { Facility, Availability } from '../types';
import { ParkingFilters } from '../components/parking/ParkingFilters';
import { ParkingList } from '../components/parking/ParkingList';
import { ParkingMap } from '../components/maps/ParkingMap';
import { Breadcrumb } from '../components/ui/Breadcrumb';
import { LiveDataTimestamp } from '../components/parking/LiveDataTimestamp';
import { useWebSocket } from '../hooks/useWebSocket';
import { useUserLocation } from '../hooks/useUserLocation';
import { calculateHaversineDistanceKm } from '../utils/navigation';
import { RefreshCw } from 'lucide-react';

export const Parking: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialView = (searchParams.get('view') as 'split' | 'list' | 'map') || 'split';

  const [facilities, setFacilities] = useState<Facility[]>([]);
  const [availabilities, setAvailabilities] = useState<Record<number, Availability>>({});
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedSort, setSelectedSort] = useState('default');
  const [availableOnlyFilter, setAvailableOnlyFilter] = useState(false);
  const [activeOnlyFilter, setActiveOnlyFilter] = useState(false);
  const [roundTheClockFilter, setRoundTheClockFilter] = useState(false);
  const [selectedFacilityId, setSelectedFacilityId] = useState<number | null>(null);
  const [viewMode, setViewMode] = useState<'split' | 'list' | 'map'>(initialView);

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastFetchedAt, setLastFetchedAt] = useState<Date | null>(new Date());

  // Geolocation integration
  const {
    location: userLocation,
    isLocating,
    error: locationError,
    requestLocation,
    clearLocation,
  } = useUserLocation();

  // Real-time WebSocket hook subscribed to all facilities
  const { latestMessage } = useWebSocket('*');

  // Handle incoming real-time updates to synchronize availability in-place
  useEffect(() => {
    if (!latestMessage) return;

    if (latestMessage.event === 'occupancy_updated' && latestMessage.facility_id) {
      const fid = latestMessage.facility_id;
      const data = latestMessage.data;
      setAvailabilities((prev) => ({
        ...prev,
        [fid]: {
          entity_id: fid,
          total_slots: data.total_slots,
          available: data.available_slots,
          occupied: data.occupied_slots,
          reserved: data.reserved_slots,
          occupancy_percentage: data.occupancy_percentage,
        },
      }));
    } else if (latestMessage.event === 'slot_status_changed' && latestMessage.facility_id) {
      const fid = latestMessage.facility_id;
      const oldStatus = latestMessage.old_status;
      const newStatus = latestMessage.new_status;

      setAvailabilities((prev) => {
        const cur = prev[fid];
        if (!cur) return prev;

        let avail = cur.available;
        let occ = cur.occupied;
        let res = cur.reserved;

        if (oldStatus === 'available') avail = Math.max(0, avail - 1);
        else if (oldStatus === 'occupied') occ = Math.max(0, occ - 1);
        else if (oldStatus === 'reserved') res = Math.max(0, res - 1);

        if (newStatus === 'available') avail += 1;
        else if (newStatus === 'occupied') occ += 1;
        else if (newStatus === 'reserved') res += 1;

        const total = cur.total_slots || (avail + occ + res);
        const pct = total > 0 ? Math.round(((total - avail) / total) * 100) : cur.occupancy_percentage;

        return {
          ...prev,
          [fid]: {
            ...cur,
            available: avail,
            occupied: occ,
            reserved: res,
            occupancy_percentage: pct,
          },
        };
      });
    }
  }, [latestMessage]);

  const loadData = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      const data = await parkingApi.getFacilities({ skip: 0, limit: 100 });
      setFacilities(data);

      if (data.length > 0 && selectedFacilityId === null) {
        setSelectedFacilityId(data[0].id);
      }

      // Fetch availability for each facility concurrently
      const availMap: Record<number, Availability> = {};
      await Promise.all(
        data.map(async (fac) => {
          try {
            const avail = await parkingApi.getFacilityAvailability(fac.id);
            availMap[fac.id] = avail;
          } catch {
            // Keep real state without fabricating fake numbers
          }
        })
      );
      setAvailabilities(availMap);
    } catch (err: any) {
      console.error('Failed to load parking facilities:', err);
      const msg = err.response?.data?.detail || err.message || 'Unable to connect to parking facilities service.';
      setError(msg);
    } finally {
      setIsLoading(false);
      setLastFetchedAt(new Date());
    }
  }, [selectedFacilityId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Sync viewMode changes to URL params
  const handleViewModeChange = (mode: 'split' | 'list' | 'map') => {
    setViewMode(mode);
    setSearchParams((prev) => {
      prev.set('view', mode);
      return prev;
    });
  };

  const clearAllFilters = () => {
    setSearchQuery('');
    setSelectedSort('default');
    setAvailableOnlyFilter(false);
    setActiveOnlyFilter(false);
    setRoundTheClockFilter(false);
  };

  const hasActiveFilters = Boolean(
    searchQuery.trim() ||
    availableOnlyFilter ||
    activeOnlyFilter ||
    roundTheClockFilter ||
    selectedSort !== 'default'
  );

  // Search, filter, and sort
  const filteredFacilities = useMemo(() => {
    return facilities
      .filter((fac) => {
        // Search query matching name, city, state, or address
        if (searchQuery.trim()) {
          const q = searchQuery.toLowerCase().trim();
          const name = fac.name?.toLowerCase() || '';
          const address = fac.address?.toLowerCase() || '';
          const city = fac.city?.toLowerCase() || '';
          const state = fac.state?.toLowerCase() || '';
          const matches = name.includes(q) || address.includes(q) || city.includes(q) || state.includes(q);
          if (!matches) return false;
        }

        // Available bays only
        if (availableOnlyFilter) {
          const avail = availabilities[fac.id]?.available;
          if (avail === undefined || avail <= 0) return false;
        }

        // Active/Open only
        if (activeOnlyFilter && !fac.is_active) {
          return false;
        }

        // 24/7 Access filter
        if (roundTheClockFilter) {
          const hasSpecificHours = Boolean(fac.operating_start_time && fac.operating_end_time);
          if (hasSpecificHours) return false;
        }

        return true;
      })
      .sort((a, b) => {
        // Sort by distance (if userLocation enabled)
        if (selectedSort === 'distance' && userLocation) {
          const distA =
            a.latitude != null && a.longitude != null
              ? calculateHaversineDistanceKm(userLocation, {
                  latitude: Number(a.latitude),
                  longitude: Number(a.longitude),
                }) ?? 999999
              : 999999;

          const distB =
            b.latitude != null && b.longitude != null
              ? calculateHaversineDistanceKm(userLocation, {
                  latitude: Number(b.latitude),
                  longitude: Number(b.longitude),
                }) ?? 999999
              : 999999;

          return distA - distB;
        }

        const aAvail = availabilities[a.id]?.available ?? -1;
        const bAvail = availabilities[b.id]?.available ?? -1;

        if (selectedSort === 'availability') {
          return bAvail - aAvail;
        }
        if (selectedSort === 'capacity') {
          return (b.total_slots || 0) - (a.total_slots || 0);
        }
        if (selectedSort === 'occupancy') {
          const aOcc = availabilities[a.id]?.occupancy_percentage ?? 100;
          const bOcc = availabilities[b.id]?.occupancy_percentage ?? 100;
          return aOcc - bOcc; // Lowest occupancy first
        }
        if (selectedSort === 'name') {
          return a.name.localeCompare(b.name);
        }
        return a.id - b.id;
      });
  }, [
    facilities,
    availabilities,
    searchQuery,
    availableOnlyFilter,
    activeOnlyFilter,
    roundTheClockFilter,
    selectedSort,
    userLocation,
  ]);

  // Aggregate telemetry
  const totalBaysAvailable = useMemo(() => {
    return filteredFacilities.reduce((sum, fac) => {
      const avail = availabilities[fac.id]?.available;
      return sum + (typeof avail === 'number' ? avail : 0);
    }, 0);
  }, [filteredFacilities, availabilities]);

  const totalCapacity = useMemo(() => {
    return filteredFacilities.reduce((sum, fac) => sum + (fac.total_slots || 0), 0);
  }, [filteredFacilities]);

  // Handle marker selection synchronization with list scroll
  const handleFacilitySelect = (facility: Facility) => {
    setSelectedFacilityId(facility.id);
    const cardEl = document.getElementById(`facility-card-${facility.id}`);
    if (cardEl) {
      cardEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.75rem' }}>
      {/* Header & Breadcrumb */}
      <div>
        <Breadcrumb items={[{ label: 'Find Parking' }]} />
        <div
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            justifyContent: 'space-between',
            alignItems: 'flex-end',
            gap: '1rem',
            marginTop: '0.75rem',
          }}
        >
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
              <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--pz-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                ✦ SPATIAL DISCOVERY ENGINE
              </span>
            </div>
            <h1 className="text-page-title">Parking Discovery &amp; Navigation</h1>
            <p className="text-body" style={{ marginTop: '4px' }}>
              Search, map, and reserve parking spaces across live connected facilities.
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
            <LiveDataTimestamp timestamp={lastFetchedAt} prefix="Synced" onRefresh={loadData} />
            <button
              onClick={() => loadData()}
              disabled={isLoading}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '8px 14px',
                borderRadius: '10px',
                fontSize: '0.8125rem',
                fontWeight: 500,
                backgroundColor: 'rgba(255, 255, 255, 0.04)',
                border: '1px solid var(--pz-border-subtle)',
                color: 'var(--pz-text-secondary)',
                cursor: isLoading ? 'not-allowed' : 'pointer',
                transition: 'all 0.2s',
              }}
            >
              <RefreshCw size={14} className={isLoading ? 'spin-animation' : ''} />
              Refresh Telemetry
            </button>
          </div>
        </div>
      </div>

      {/* Search & Filter Component with View Mode and Geolocation */}
      <ParkingFilters
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        selectedSort={selectedSort}
        onSortChange={setSelectedSort}
        availableOnly={availableOnlyFilter}
        onToggleAvailableOnly={() => setAvailableOnlyFilter(!availableOnlyFilter)}
        activeOnly={activeOnlyFilter}
        onToggleActiveOnly={() => setActiveOnlyFilter(!activeOnlyFilter)}
        roundTheClock={roundTheClockFilter}
        onToggleRoundTheClock={() => setRoundTheClockFilter(!roundTheClockFilter)}
        hasActiveFilters={hasActiveFilters}
        onClearFilters={clearAllFilters}
        userLocation={userLocation}
        onRequestLocation={requestLocation}
        onClearLocation={clearLocation}
        isLocating={isLocating}
        locationError={locationError}
        viewMode={viewMode}
        onViewModeChange={handleViewModeChange}
      />

      {/* Aggregate Telemetry Strip */}
      {!isLoading && !error && facilities.length > 0 && (
        <div
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontSize: '0.8125rem',
            color: 'var(--pz-text-secondary)',
            padding: '0 4px',
            fontFamily: 'var(--font-mono)',
          }}
        >
          <span>
            Showing <strong style={{ color: '#FFFFFF' }}>{filteredFacilities.length}</strong> of{' '}
            <strong style={{ color: '#FFFFFF' }}>{facilities.length}</strong> facilities
          </span>
          <span style={{ display: 'flex', gap: '16px' }}>
            <span>
              Available Bays: <strong style={{ color: 'var(--pz-success)' }}>{totalBaysAvailable}</strong>
            </span>
            <span>
              Total Capacity: <strong style={{ color: '#FFFFFF' }}>{totalCapacity}</strong>
            </span>
          </span>
        </div>
      )}

      {/* Main Content Area based on View Mode */}
      {viewMode === 'map' ? (
        /* Full Map View */
        <div style={{ height: '620px', width: '100%' }}>
          <ParkingMap
            facilities={filteredFacilities}
            selectedFacilityId={selectedFacilityId}
            onFacilitySelect={handleFacilitySelect}
            availabilities={availabilities}
            userLocation={userLocation}
            onRequestUserLocation={requestLocation}
            isLocating={isLocating}
            height="100%"
          />
        </div>
      ) : viewMode === 'split' ? (
        /* Split View: Left List Cards (55%), Right Sticky Map (45%) */
        <div className="parking-split-layout">
          <div className="parking-split-list">
            <ParkingList
              facilities={filteredFacilities}
              availabilities={availabilities}
              isLoading={isLoading}
              error={error}
              hasFilters={hasActiveFilters}
              searchQuery={searchQuery}
              selectedFacilityId={selectedFacilityId}
              userLocation={userLocation}
              layout="compact"
              onRetry={loadData}
              onClearFilters={clearAllFilters}
            />
          </div>

          <div className="parking-split-map">
            <div
              style={{
                position: 'sticky',
                top: '90px',
                height: 'calc(100vh - 220px)',
                minHeight: '520px',
                maxHeight: '740px',
              }}
            >
              <ParkingMap
                facilities={filteredFacilities}
                selectedFacilityId={selectedFacilityId}
                onFacilitySelect={handleFacilitySelect}
                availabilities={availabilities}
                userLocation={userLocation}
                onRequestUserLocation={requestLocation}
                isLocating={isLocating}
                height="100%"
              />
            </div>
          </div>
        </div>
      ) : (
        /* Pure Cards Grid View */
        <ParkingList
          facilities={filteredFacilities}
          availabilities={availabilities}
          isLoading={isLoading}
          error={error}
          hasFilters={hasActiveFilters}
          searchQuery={searchQuery}
          selectedFacilityId={selectedFacilityId}
          userLocation={userLocation}
          layout="grid"
          onRetry={loadData}
          onClearFilters={clearAllFilters}
        />
      )}

      <style>{`
        .parking-split-layout {
          display: grid;
          grid-template-columns: minmax(0, 1.25fr) minmax(0, 1fr);
          gap: 1.5rem;
          align-items: start;
        }
        @media (max-width: 1024px) {
          .parking-split-layout {
            grid-template-columns: 1fr;
          }
          .split-view-btn {
            display: none !important;
          }
          .parking-split-map {
            margin-top: 1rem;
          }
          .parking-split-map > div {
            position: relative !important;
            top: 0 !important;
            height: 440px !important;
            min-height: 440px !important;
          }
        }
        @media (max-width: 640px) {
          .hidden-mobile {
            display: none !important;
          }
        }
      `}</style>
    </div>
  );
};

export default Parking;
