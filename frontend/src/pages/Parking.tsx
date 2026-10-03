import React, { useEffect, useState, useMemo, useCallback } from 'react';
import { parkingApi } from '../api/parking';
import type { Facility, Availability } from '../types';
import { ParkingFilters } from '../components/parking/ParkingFilters';
import { ParkingList } from '../components/parking/ParkingList';
import { Breadcrumb } from '../components/ui/Breadcrumb';
import { RefreshCw } from 'lucide-react';

export const Parking: React.FC = () => {
  const [facilities, setFacilities] = useState<Facility[]>([]);
  const [availabilities, setAvailabilities] = useState<Record<number, Availability>>({});
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedSort, setSelectedSort] = useState('default');
  const [availableOnlyFilter, setAvailableOnlyFilter] = useState(false);
  const [activeOnlyFilter, setActiveOnlyFilter] = useState(false);
  const [roundTheClockFilter, setRoundTheClockFilter] = useState(false);

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      const data = await parkingApi.getFacilities({ skip: 0, limit: 100 });
      setFacilities(data);

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
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

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
  }, [facilities, availabilities, searchQuery, availableOnlyFilter, activeOnlyFilter, roundTheClockFilter, selectedSort]);

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

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
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
            <h1 className="text-page-title">Parking Discovery</h1>
            <p className="text-body" style={{ marginTop: '4px' }}>
              Search and reserve parking spaces across live connected facilities.
            </p>
          </div>

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

      {/* Search & Filter Component */}
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

      {/* Parking Facilities Grid List */}
      <ParkingList
        facilities={filteredFacilities}
        availabilities={availabilities}
        isLoading={isLoading}
        error={error}
        hasFilters={hasActiveFilters}
        searchQuery={searchQuery}
        onRetry={loadData}
        onClearFilters={clearAllFilters}
      />
    </div>
  );
};

export default Parking;
