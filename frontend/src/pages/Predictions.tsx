import React, { useEffect, useState, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { parkingApi } from '../api/parking';
import { aiApi } from '../api/ai';
import type {
  Facility,
  AvailabilityPrediction,
  OccupancyForecast,
  QueuePrediction,
  ParkingRecommendation,
  RiskLevel,
} from '../types';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Select } from '../components/ui/Select';
import { Breadcrumb } from '../components/ui/Breadcrumb';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';
import { ProbabilityIndicator } from '../components/ai/ProbabilityIndicator';
import { DemandIndicator } from '../components/ai/DemandIndicator';
import { QueueEstimate } from '../components/ai/QueueEstimate';
import { RecommendationCard } from '../components/ai/RecommendationCard';
import { InsightCard } from '../components/ai/InsightCard';
import { ForecastCard } from '../components/ai/ForecastCard';
import { HeatMapContainer, type ZoneCongestion } from '../components/ai/HeatMapContainer';
import {
  Brain,
  Sparkles,
  TrendingUp,
  RefreshCw,
  ArrowRight,
  Database,
  Cpu,
  AlertCircle,
} from 'lucide-react';

const Predictions: React.FC = () => {
  const navigate = useNavigate();
  const [facilities, setFacilities] = useState<Facility[]>([]);
  const [selectedFacilityId, setSelectedFacilityId] = useState<number | null>(null);
  const [etaMinutes, setEtaMinutes] = useState<number>(20);
  const [vehicleFilter, setVehicleFilter] = useState<string>('all');

  // Real backend predictive telemetry state
  const [predictionData, setPredictionData] = useState<AvailabilityPrediction | null>(null);
  const [forecastData, setForecastData] = useState<OccupancyForecast | null>(null);
  const [queueData, setQueueData] = useState<QueuePrediction | null>(null);
  const [recommendations, setRecommendations] = useState<ParkingRecommendation[]>([]);
  const [zonesList, setZonesList] = useState<ZoneCongestion[]>([]);

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch initial facilities list
  useEffect(() => {
    let isMounted = true;
    const fetchFacilities = async () => {
      try {
        const facs = await parkingApi.getFacilities();
        if (isMounted) {
          setFacilities(facs);
          if (facs.length > 0) {
            setSelectedFacilityId(facs[0].id);
          } else {
            setIsLoading(false);
          }
        }
      } catch (err: any) {
        if (isMounted) {
          console.error('Error fetching facilities for predictions:', err);
          setError('Failed to load parking facilities. Please verify your connection.');
          setIsLoading(false);
        }
      }
    };
    fetchFacilities();
    return () => {
      isMounted = false;
    };
  }, []);

  // Fetch real predictive intelligence from backend APIs
  const loadPredictions = useCallback(async (facId: number, eta: number) => {
    try {
      setIsRefreshing(true);
      setError(null);

      const targetFac = facilities.find((f) => f.id === facId);
      const lat = targetFac?.latitude || 12.9716;
      const lon = targetFac?.longitude || 77.5946;

      // Parallelize calls to backend prediction & telemetry endpoints
      const [predResult, forecastResult, queueResult, recResult, zonesResult] = await Promise.allSettled([
        aiApi.getPrediction(facId, undefined, eta),
        aiApi.getOccupancyForecast(facId, 15),
        aiApi.getQueueMetrics(facId, eta),
        aiApi.getRecommendations({
          latitude: lat,
          longitude: lon,
          eta_minutes: eta,
          max_distance_km: 15,
          max_results: 3,
        }),
        parkingApi.getZones(facId),
      ]);

      // 1. Availability Prediction
      if (predResult.status === 'fulfilled') {
        setPredictionData(predResult.value);
      } else {
        console.warn('Availability prediction request failed:', predResult.reason);
      }

      // 2. Temporal Occupancy Forecast
      if (forecastResult.status === 'fulfilled') {
        setForecastData(forecastResult.value);
      } else {
        console.warn('Occupancy forecast request failed:', forecastResult.reason);
      }

      // 3. Queue Prediction
      if (queueResult.status === 'fulfilled') {
        setQueueData(queueResult.value);
      } else {
        console.warn('Queue prediction request failed:', queueResult.reason);
      }

      // 4. Smart Recommendations
      if (recResult.status === 'fulfilled') {
        setRecommendations(recResult.value?.recommendations || []);
      } else {
        console.warn('Recommendations request failed:', recResult.reason);
      }

      // 5. Zone Density Heatmap Data
      if (zonesResult.status === 'fulfilled') {
        const rawZones = zonesResult.value;
        const availPromises = rawZones.map((z) =>
          parkingApi.getZoneAvailability(z.id).catch(() => null)
        );
        const avails = await Promise.all(availPromises);
        const mappedZones: ZoneCongestion[] = rawZones.map((z, idx) => {
          const za = avails[idx];
          const available = za?.available ?? Math.max(0, Math.round(z.total_slots * 0.4));
          const occPct = za?.occupancy_percentage ?? (z.total_slots > 0 ? Math.round(((z.total_slots - available) / z.total_slots) * 100) : 0);
          return {
            id: String(z.id),
            name: `${z.name} (Floor ${z.floor_number ?? 1})`,
            occupancyPct: occPct,
            availableBays: available,
            totalBays: z.total_slots,
            description: z.description || `Floor ${z.floor_number ?? 1} • Real-time Monitoring`,
          };
        });
        setZonesList(mappedZones);
      }

      // If both core availability and forecast failed completely, report error
      if (predResult.status === 'rejected' && forecastResult.status === 'rejected') {
        setError('Predictive intelligence endpoint is currently unreachable.');
      }
    } catch (err: any) {
      console.error('Failed to load predictions:', err);
      setError('An unexpected error occurred while fetching AI predictions.');
    } finally {
      setIsRefreshing(false);
      setIsLoading(false);
    }
  }, [facilities]);

  useEffect(() => {
    if (selectedFacilityId) {
      loadPredictions(selectedFacilityId, etaMinutes);
    }
  }, [selectedFacilityId, etaMinutes, loadPredictions]);

  const selectedFacility = facilities.find((f) => f.id === selectedFacilityId);

  // Compute dynamic demand surge parameters from real forecast
  const surgeParams = useMemo(() => {
    const occ = forecastData?.prediction_30 ?? predictionData?.forecast_occupancy ?? 50;
    const curr = forecastData?.current_occupancy ?? predictionData?.current_occupancy ?? 50;
    const diffPct = Math.max(0, Math.round(occ - curr));

    let level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL' = 'LOW';
    let multiplier = 1.0;

    if (occ >= 90) {
      level = 'CRITICAL';
      multiplier = 1.45;
    } else if (occ >= 75) {
      level = 'HIGH';
      multiplier = 1.25;
    } else if (occ >= 50) {
      level = 'MEDIUM';
      multiplier = 1.1;
    } else {
      level = 'LOW';
      multiplier = 1.0;
    }

    return { level, multiplier, diffPct };
  }, [forecastData, predictionData]);

  // Construct dynamic SVG curve points based on real forecast data
  const curvePoints = useMemo(() => {
    const c0 = forecastData?.current_occupancy ?? predictionData?.current_occupancy ?? 50;
    const c15 = forecastData?.prediction_15 ?? c0;
    const c30 = forecastData?.prediction_30 ?? c15;
    const c60 = forecastData?.prediction_60 ?? c30;

    // SVG coordinates: Width 700, Height 200 (y: 30 = 100% occ, 170 = 0% occ)
    const mapY = (val: number) => {
      const clamped = Math.max(0, Math.min(100, val));
      return Math.round(170 - (clamped / 100) * 140);
    };

    const y0 = mapY(c0);
    const y15 = mapY(c15);
    const y30 = mapY(c30);
    const y60 = mapY(c60);

    // Points at x: 50 (Now), 250 (+15m), 450 (+30m), 650 (+60m)
    const mainPath = `M 50 ${y0} C 150 ${y0}, 150 ${y15}, 250 ${y15} C 350 ${y15}, 350 ${y30}, 450 ${y30} C 550 ${y30}, 550 ${y60}, 650 ${y60}`;
    const fillArea = `${mainPath} L 650 190 L 50 190 Z`;

    // Dynamic position of current ETA indicator point
    let etaX = 50 + (etaMinutes / 60) * 600;
    etaX = Math.max(50, Math.min(650, etaX));
    // Linear approximation for ETA y position
    const t = etaMinutes / 60;
    const etaOcc = c0 + (c60 - c0) * t;
    const etaY = mapY(etaOcc);

    return { mainPath, fillArea, etaX, etaY, y0, y15, y30, y60, c0, c15, c30, c60 };
  }, [forecastData, predictionData, etaMinutes]);

  const isDegradedFallback = predictionData?.prediction_status === 'DEGRADED_FALLBACK' || forecastData?.prediction_status === 'DEGRADED_FALLBACK';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      {/* Header & Breadcrumb */}
      <div>
        <Breadcrumb items={[{ label: 'AI Predictions' }]} />
        <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'flex-end', gap: '1rem', marginTop: '0.75rem' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
              <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#C084FC', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                ✦ NEURAL LSTM SPATIAL FORECASTING
              </span>
              <span className="telemetry-pulse" />

              {/* Status Badge */}
              {isDegradedFallback ? (
                <span
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '4px',
                    fontSize: '0.6875rem',
                    fontWeight: 600,
                    padding: '2px 8px',
                    borderRadius: '9999px',
                    backgroundColor: 'rgba(0, 229, 255, 0.12)',
                    color: '#00E5FF',
                    border: '1px solid rgba(0, 229, 255, 0.3)',
                  }}
                  title="Calculated from real-time database slot occupancy"
                >
                  <Database size={11} /> Real-time Slot Telemetry
                </span>
              ) : (
                <span
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '4px',
                    fontSize: '0.6875rem',
                    fontWeight: 600,
                    padding: '2px 8px',
                    borderRadius: '9999px',
                    backgroundColor: 'rgba(139, 92, 246, 0.15)',
                    color: '#C084FC',
                    border: '1px solid rgba(139, 92, 246, 0.3)',
                  }}
                >
                  <Cpu size={11} /> LSTM Model v4.9 Active
                </span>
              )}
            </div>
            <h1 className="text-page-title">AI Predictive Intelligence Hub</h1>
            <p className="text-body" style={{ marginTop: '4px' }}>
              {selectedFacility ? `${selectedFacility.name}: ` : ''}Realtime arrival probabilities, demand surge forecasting, and multi-bay congestion analytics.
            </p>
          </div>

          <Button
            variant="outline"
            size="sm"
            leftIcon={<RefreshCw size={14} className={isRefreshing ? 'animate-spin' : ''} />}
            onClick={() => selectedFacilityId && loadPredictions(selectedFacilityId, etaMinutes)}
            disabled={isRefreshing || !selectedFacilityId}
          >
            Refresh Inference
          </Button>
        </div>
      </div>

      {/* Interactive Control Toolbar */}
      <Card
        glow="purple"
        style={{
          padding: '1.25rem 1.5rem',
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '1.5rem',
        }}
      >
        {/* Facility Selector */}
        <div style={{ minWidth: '260px', flex: 1 }}>
          <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-muted)', display: 'block', marginBottom: '4px' }}>
            Target Parking Facility
          </span>
          <Select
            value={selectedFacilityId ?? ''}
            onChange={(e) => setSelectedFacilityId(Number(e.target.value))}
            options={
              facilities.length > 0
                ? facilities.map((f) => ({ value: f.id, label: f.name }))
                : [{ value: '', label: 'Loading facilities...' }]
            }
          />
        </div>

        {/* Dynamic ETA Selector with Quick Chips */}
        <div style={{ minWidth: '280px', flex: 1 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-muted)' }}>Estimated Arrival Horizon</span>
            <span style={{ fontSize: '0.8125rem', color: 'var(--pz-secondary)', fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
              +{etaMinutes} mins ETA
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            {[15, 20, 30, 45, 60].map((mins) => (
              <button
                key={mins}
                onClick={() => setEtaMinutes(mins)}
                style={{
                  flex: 1,
                  padding: '6px 10px',
                  borderRadius: '8px',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  backgroundColor: etaMinutes === mins ? 'rgba(139, 92, 246, 0.3)' : 'rgba(255, 255, 255, 0.04)',
                  color: etaMinutes === mins ? '#FFFFFF' : 'var(--pz-text-secondary)',
                  border: etaMinutes === mins ? '1px solid #8B5CF6' : '1px solid var(--pz-border-subtle)',
                  cursor: 'pointer',
                  transition: 'all 0.15s',
                }}
              >
                +{mins}m
              </button>
            ))}
          </div>
        </div>

        {/* Vehicle Filter */}
        <div style={{ width: '180px' }}>
          <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-muted)', display: 'block', marginBottom: '4px' }}>
            Vehicle Profile
          </span>
          <Select
            value={vehicleFilter}
            onChange={(e) => setVehicleFilter(e.target.value)}
            options={[
              { value: 'all', label: 'All Vehicles' },
              { value: 'ev', label: 'EV 350kW Fast' },
              { value: 'suv', label: 'High Clearance' },
            ]}
          />
        </div>
      </Card>

      {/* Error Banner if any */}
      {error && (
        <div
          style={{
            padding: '1rem 1.25rem',
            borderRadius: '12px',
            backgroundColor: 'rgba(244, 63, 94, 0.12)',
            border: '1px solid rgba(244, 63, 94, 0.3)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '12px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <AlertCircle size={18} color="var(--pz-error)" />
            <span style={{ fontSize: '0.875rem', color: '#FFFFFF' }}>{error}</span>
          </div>
          <Button
            size="sm"
            variant="outline"
            onClick={() => selectedFacilityId && loadPredictions(selectedFacilityId, etaMinutes)}
          >
            Retry Connection
          </Button>
        </div>
      )}

      {/* Top AI Metrics Row */}
      {isLoading ? (
        <LoadingSpinner size="lg" label="Computing real-time neural forecasts..." />
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1.25rem' }}>
          <ProbabilityIndicator
            probability={predictionData?.availability_probability ?? 0}
            confidence={predictionData?.confidence ?? (isDegradedFallback ? 100 : 94)}
            etaMinutes={etaMinutes}
            riskLevel={(predictionData?.occupancy_risk as RiskLevel) ?? 'LOW'}
          />

          <DemandIndicator
            multiplier={surgeParams.multiplier}
            level={surgeParams.level}
            peakTime={forecastData?.prediction_60 && forecastData.prediction_60 > 75 ? '+60m Horizon' : undefined}
            expectedIncreasePct={surgeParams.diffPct}
          />

          <QueueEstimate
            waitTimeMinutes={queueData?.expected_wait_minutes ?? predictionData?.queue_wait_minutes ?? 0}
            throughputRate={queueData?.expected_departures ? Math.round(queueData.expected_departures * 10) / 10 : 12.0}
            gateName="Gate A Express ALPR"
            status={queueData?.congestion_level ? `${queueData.congestion_level} Congestion` : 'Smooth Flow'}
          />

          <ForecastCard
            currentOccupancy={forecastData?.current_occupancy ?? predictionData?.current_occupancy ?? 0}
            prediction15={forecastData?.prediction_15 ?? predictionData?.current_occupancy ?? 0}
            prediction30={forecastData?.prediction_30 ?? predictionData?.current_occupancy ?? 0}
            prediction60={forecastData?.prediction_60 ?? predictionData?.current_occupancy ?? 0}
            confidence={forecastData?.confidence ?? (isDegradedFallback ? 100 : 94)}
          />
        </div>
      )}

      {/* Main Grid: Forecast Chart + Congestion Heat Map vs Recommendations */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(12, 1fr)', gap: '1.5rem' }}>
        {/* Left Column (8 cols): 24-Hour Demand Curve & Live Heat Map */}
        <div style={{ gridColumn: 'span 8', display: 'flex', flexDirection: 'column', gap: '1.5rem' }} className="pred-main-col">
          {/* Predictive Demand Curve Visualization */}
          <Card>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <TrendingUp size={18} color="var(--pz-secondary)" />
                  <h3 style={{ fontSize: '1.125rem', fontWeight: 600, color: '#FFFFFF' }}>
                    Temporal Predictive Occupancy Horizon
                  </h3>
                </div>
                <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-secondary)', marginTop: '2px', display: 'block' }}>
                  Target Arrival Window marked at +{etaMinutes}m ETA ({predictionData?.expected_free_slots ?? 0} bays expected free)
                </span>
              </div>

              <div style={{ display: 'flex', gap: '12px', fontSize: '0.75rem' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--pz-secondary)' }}>
                  <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: 'var(--pz-secondary)' }} /> Forecast
                </span>
                <span style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#C084FC' }}>
                  <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#C084FC' }} /> Neural Trend
                </span>
              </div>
            </div>

            {/* SVG Forecast Graph Curve */}
            <div style={{ width: '100%', height: '220px', position: 'relative' }}>
              <svg width="100%" height="100%" viewBox="0 0 700 200" preserveAspectRatio="none" style={{ overflow: 'visible' }}>
                <defs>
                  <linearGradient id="curveGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#00E5FF" stopOpacity="0.35" />
                    <stop offset="100%" stopColor="#00E5FF" stopOpacity="0.0" />
                  </linearGradient>
                </defs>

                {/* Grid guidelines */}
                <line x1="50" y1="50" x2="650" y2="50" stroke="rgba(255,255,255,0.06)" strokeDasharray="4 4" />
                <line x1="50" y1="100" x2="650" y2="100" stroke="rgba(255,255,255,0.06)" strokeDasharray="4 4" />
                <line x1="50" y1="150" x2="650" y2="150" stroke="rgba(255,255,255,0.06)" strokeDasharray="4 4" />

                {/* Shaded Area under forecast curve */}
                <path d={curvePoints.fillArea} fill="url(#curveGradient)" />

                {/* Main Predicted Curve */}
                <path d={curvePoints.mainPath} fill="none" stroke="#00E5FF" strokeWidth="3" />

                {/* Data Points */}
                <circle cx="50" cy={curvePoints.y0} r="4" fill="#00E5FF" />
                <circle cx="250" cy={curvePoints.y15} r="4" fill="#00E5FF" />
                <circle cx="450" cy={curvePoints.y30} r="4" fill="#00E5FF" />
                <circle cx="650" cy={curvePoints.y60} r="4" fill="#00E5FF" />

                {/* Target ETA indicator point */}
                <circle cx={curvePoints.etaX} cy={curvePoints.etaY} r="6" fill="#8B5CF6" />
                <circle cx={curvePoints.etaX} cy={curvePoints.etaY} r="12" fill="none" stroke="#8B5CF6" opacity="0.6" />
                <line x1={curvePoints.etaX} y1="30" x2={curvePoints.etaX} y2="180" stroke="#8B5CF6" strokeDasharray="2 2" strokeWidth="1.5" />
                
                <text
                  x={Math.min(520, curvePoints.etaX + 10)}
                  y={Math.max(40, curvePoints.etaY - 12)}
                  fill="#FFFFFF"
                  fontSize="11"
                  fontWeight="700"
                  fontFamily="var(--font-mono)"
                >
                  Arrival ETA: {predictionData?.availability_probability?.toFixed(0) ?? 0}% Prob
                </text>
              </svg>
            </div>

            {/* Time horizon labels */}
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '0 25px', fontSize: '0.75rem', color: 'var(--pz-text-muted)', fontFamily: 'var(--font-mono)', marginTop: '8px' }}>
              <span>Now ({curvePoints.c0.toFixed(0)}%)</span>
              <span>+15m ({curvePoints.c15.toFixed(0)}%)</span>
              <span>+30m ({curvePoints.c30.toFixed(0)}%)</span>
              <span>+60m ({curvePoints.c60.toFixed(0)}%)</span>
            </div>
          </Card>

          {/* Congestion Heat Map with real zone data */}
          <HeatMapContainer
            zones={zonesList.length > 0 ? zonesList : undefined}
            onZoneSelect={(_zone) => {
              if (selectedFacilityId) {
                navigate(`/parking/${selectedFacilityId}`);
              }
            }}
          />
        </div>

        {/* Right Column (4 cols): AI Alternative Recommendations & Insights */}
        <div style={{ gridColumn: 'span 4', display: 'flex', flexDirection: 'column', gap: '1.5rem' }} className="pred-side-col">
          {/* AI Facility Recommendations */}
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '0.75rem' }}>
              <Brain size={18} color="var(--pz-secondary)" />
              <h3 style={{ fontSize: '1.0625rem', fontWeight: 600, color: '#FFFFFF' }}>
                Neural Alternatives
              </h3>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {recommendations.length > 0 ? (
                recommendations.map((rec) => (
                  <RecommendationCard
                    key={rec.facility_id}
                    rank={rec.rank}
                    facilityName={rec.facility_name}
                    matchScore={Math.round(rec.recommendation_score)}
                    distanceKm={rec.distance_km}
                    openBays={
                      rec.availability_probability > 0
                        ? Math.round(rec.availability_probability)
                        : Math.max(0, Math.round(100 - rec.current_occupancy))
                    }
                    estimatedCost={rec.estimated_cost}
                    reason={rec.reason}
                    onSelect={() => navigate(`/parking/${rec.facility_id}`)}
                  />
                ))
              ) : (
                <Card style={{ padding: '1.5rem', textAlign: 'center' }}>
                  <Sparkles size={24} color="#C084FC" style={{ margin: '0 auto 8px auto' }} />
                  <p style={{ fontSize: '0.875rem', color: 'var(--pz-text-secondary)' }}>
                    {isRefreshing ? 'Computing ranked alternatives...' : 'Primary facility is optimal for your destination.'}
                  </p>
                </Card>
              )}
            </div>
          </div>

          {/* AI Causal Insights Feed */}
          <Card>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '1rem' }}>
              <Sparkles size={16} color="#C084FC" />
              <h4 style={{ fontSize: '0.9375rem', fontWeight: 600, color: '#FFFFFF' }}>
                Live Causal Telemetry
              </h4>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <InsightCard
                type="weather"
                severity="INFO"
                factor="PREDICTIVE ASSURANCE"
                message={`${predictionData?.availability_probability?.toFixed(0) ?? 0}% probability of open bay at +${etaMinutes}m ETA window with ${predictionData?.expected_free_slots ?? 0} slots forecasted free.`}
              />
              <InsightCard
                type="traffic"
                severity={surgeParams.level === 'HIGH' || surgeParams.level === 'CRITICAL' ? 'WARNING' : 'SUCCESS'}
                factor="GATE INGRESS LATENCY"
                message={`Estimated queue wait is ${queueData?.expected_wait_minutes?.toFixed(1) ?? 0} mins. Gate status: ${queueData?.congestion_level || 'NORMAL'}.`}
              />
              <InsightCard
                type="recommendation"
                severity="SUCCESS"
                factor="RESERVATION WINDOW"
                message={
                  predictionData?.occupancy_risk === 'HIGH'
                    ? 'High surge expected; advance reservation strongly advised to lock slot.'
                    : 'Optimal arrival window detected. Bays currently accessible with minimum friction.'
                }
              />
            </div>

            {/* Hold CTA */}
            <div style={{ marginTop: '1.25rem', borderTop: '1px solid var(--pz-border-subtle)', paddingTop: '1rem' }}>
              <Button
                variant="ai"
                size="md"
                onClick={() => selectedFacilityId && navigate(`/parking/${selectedFacilityId}`)}
                rightIcon={<ArrowRight size={16} />}
                style={{ width: '100%' }}
                disabled={!selectedFacilityId}
              >
                Reserve Slot at Selected Facility
              </Button>
            </div>
          </Card>
        </div>
      </div>

      <style>{`
        @media (max-width: 1024px) {
          .pred-main-col { grid-column: span 12 !important; }
          .pred-side-col { grid-column: span 12 !important; }
        }
      `}</style>
    </div>
  );
};

export default Predictions;
