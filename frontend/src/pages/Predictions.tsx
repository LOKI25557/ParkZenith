import React, { useEffect, useState } from 'react';
import { parkingApi } from '../api/parking';
import { aiApi } from '../api/ai';
import type { Facility } from '../types';
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
import { HeatMapContainer } from '../components/ai/HeatMapContainer';
import { useNavigate } from 'react-router-dom';
import {
  Brain,
  Sparkles,
  TrendingUp,
  RefreshCw,
  ArrowRight,
} from 'lucide-react';

const Predictions: React.FC = () => {
  const navigate = useNavigate();
  const [facilities, setFacilities] = useState<Facility[]>([]);
  const [selectedFacilityId, setSelectedFacilityId] = useState<number>(1);
  const [etaMinutes, setEtaMinutes] = useState<number>(35);
  const [vehicleFilter, setVehicleFilter] = useState<string>('all');
  const [predictionData, setPredictionData] = useState<any>(null);
  const [forecastData, setForecastData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);

  useEffect(() => {
    const fetchFacilities = async () => {
      try {
        const facs = await parkingApi.getFacilities();
        setFacilities(facs);
        if (facs.length > 0) {
          setSelectedFacilityId(facs[0].id);
        }
      } catch (err) {
        console.error('Error fetching facilities:', err);
      }
    };
    fetchFacilities();
  }, []);

  const loadPredictions = async (facId: number, eta: number) => {
    try {
      setIsRefreshing(true);
      // Try backend prediction endpoint with fallbacks
      const pred = await aiApi.getPrediction(facId, undefined, eta);
      setPredictionData(pred);

      try {
        const occ = await aiApi.getOccupancyForecast(facId, 15);
        setForecastData(occ);
      } catch {
        setForecastData({
          current_occupancy: 68.0,
          prediction_15: 64.0,
          prediction_30: 72.0,
          prediction_60: 84.0,
          confidence: 94.0,
        });
      }
    } catch {
      setPredictionData({
        facility_id: String(facId),
        eta_minutes: eta,
        current_occupancy: 78.0,
        forecast_occupancy: 64.0,
        expected_free_slots: 18,
        availability_probability: 88.4,
        occupancy_risk: 'LOW',
        confidence: 96.0,
        queue_wait_minutes: 2.4,
      });
      setForecastData({
        current_occupancy: 78.0,
        prediction_15: 64.0,
        prediction_30: 72.0,
        prediction_60: 84.0,
        confidence: 94.0,
      });
    } finally {
      setIsRefreshing(false);
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (selectedFacilityId) {
      loadPredictions(selectedFacilityId, etaMinutes);
    }
  }, [selectedFacilityId, etaMinutes]);

  const selectedFacility = facilities.find((f) => f.id === selectedFacilityId);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
      {/* Header & Breadcrumb */}
      <div>
        <Breadcrumb items={[{ label: 'AI Predictions' }]} />
        <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'flex-end', gap: '1rem', marginTop: '0.75rem' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
              <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#C084FC', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                ✦ NEURAL LSTM SPATIAL FORECASTING
              </span>
              <span className="telemetry-pulse" />
            </div>
            <h1 className="text-page-title">AI Predictive Intelligence Hub</h1>
            <p className="text-body" style={{ marginTop: '4px' }}>
              {selectedFacility ? `${selectedFacility.name}: ` : ''}Deep learning arrival probabilities, demand surge forecasting, and real-time congestion heat maps.
            </p>
          </div>

          <Button
            variant="outline"
            size="sm"
            leftIcon={<RefreshCw size={14} className={isRefreshing ? 'animate-spin' : ''} />}
            onClick={() => loadPredictions(selectedFacilityId, etaMinutes)}
            disabled={isRefreshing}
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
        <div style={{ minWidth: '240px', flex: 1 }}>
          <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-muted)', display: 'block', marginBottom: '4px' }}>
            Target Parking Facility
          </span>
          <Select
            value={selectedFacilityId}
            onChange={(e) => setSelectedFacilityId(Number(e.target.value))}
            options={
              facilities.length > 0
                ? facilities.map((f) => ({ value: f.id, label: f.name }))
                : [{ value: 1, label: 'Metropolis Central Hub - Sector B' }]
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
            {[15, 30, 45, 60].map((mins) => (
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

      {/* Top AI Metrics Row */}
      {isLoading ? (
        <LoadingSpinner size="lg" label="Computing neural probabilities..." />
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1.25rem' }}>
          <ProbabilityIndicator
            probability={predictionData?.availability_probability ?? 88.4}
            confidence={predictionData?.confidence ?? 96}
            etaMinutes={etaMinutes}
            riskLevel={predictionData?.occupancy_risk ?? 'LOW'}
          />

          <DemandIndicator
            multiplier={1.15}
            level="MEDIUM"
            peakTime="17:30 EDT"
            expectedIncreasePct={42}
          />

          <QueueEstimate
            waitTimeMinutes={predictionData?.queue_wait_minutes ?? 2.4}
            throughputRate={14.2}
            gateName="Gate B Express ALPR"
            status="Smooth Ingress"
          />

          <ForecastCard
            currentOccupancy={forecastData?.current_occupancy ?? 78.0}
            prediction15={forecastData?.prediction_15 ?? 64.0}
            prediction30={forecastData?.prediction_30 ?? 72.0}
            prediction60={forecastData?.prediction_60 ?? 84.0}
            confidence={forecastData?.confidence ?? 94}
          />
        </div>
      )}

      {/* Main Grid: Forecast Chart + Congestion Heat Map vs Recommendations */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(12, 1fr)', gap: '1.5rem' }}>
        {/* Left Column (8 cols): 24-Hour Demand Curve & Live Heat Map */}
        <div style={{ gridColumn: 'span 8', display: 'flex', flexDirection: 'column', gap: '1.5rem' }} className="pred-main-col">
          {/* 24-Hour Demand Curve Visualization */}
          <Card>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <TrendingUp size={18} color="var(--pz-secondary)" />
                  <h3 style={{ fontSize: '1.125rem', fontWeight: 600, color: '#FFFFFF' }}>
                    24-Hour Predictive Demand &amp; Occupancy Curve
                  </h3>
                </div>
                <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-secondary)', marginTop: '2px', display: 'block' }}>
                  Target Arrival Window marked at +{etaMinutes}m ETA
                </span>
              </div>

              <div style={{ display: 'flex', gap: '12px', fontSize: '0.75rem' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--pz-secondary)' }}>
                  <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: 'var(--pz-secondary)' }} /> Forecast
                </span>
                <span style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#C084FC' }}>
                  <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#C084FC' }} /> EV Saturation
                </span>
                <span style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--pz-text-muted)' }}>
                  <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: 'var(--pz-text-muted)' }} /> 30-Day Mean
                </span>
              </div>
            </div>

            {/* SVG Forecast Graph Curve */}
            <div style={{ width: '100%', height: '220px', position: 'relative' }}>
              <svg width="100%" height="100%" viewBox="0 0 700 200" preserveAspectRatio="none" style={{ overflow: 'visible' }}>
                <defs>
                  <linearGradient id="curveGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#00E5FF" stopOpacity="0.3" />
                    <stop offset="100%" stopColor="#00E5FF" stopOpacity="0.0" />
                  </linearGradient>
                </defs>

                {/* Grid guidelines */}
                <line x1="0" y1="50" x2="700" y2="50" stroke="rgba(255,255,255,0.06)" strokeDasharray="4 4" />
                <line x1="0" y1="100" x2="700" y2="100" stroke="rgba(255,255,255,0.06)" strokeDasharray="4 4" />
                <line x1="0" y1="150" x2="700" y2="150" stroke="rgba(255,255,255,0.06)" strokeDasharray="4 4" />

                {/* Surge Highlight Band (17:00-18:30) */}
                <rect x="420" y="20" width="120" height="170" fill="rgba(244, 63, 94, 0.08)" rx="6" />
                <text x="430" y="38" fill="var(--pz-error)" fontSize="10" fontFamily="var(--font-mono)">
                  PEAK EGRESS SURGE
                </text>

                {/* Shaded Area under forecast curve */}
                <path
                  d="M 0 140 Q 120 150, 240 100 T 480 40 T 700 120 L 700 190 L 0 190 Z"
                  fill="url(#curveGradient)"
                />

                {/* Main Predicted Curve */}
                <path
                  d="M 0 140 Q 120 150, 240 100 T 480 40 T 700 120"
                  fill="none"
                  stroke="#00E5FF"
                  strokeWidth="3"
                />

                {/* EV Saturation Curve */}
                <path
                  d="M 0 160 Q 150 140, 300 90 T 520 60 T 700 110"
                  fill="none"
                  stroke="#C084FC"
                  strokeWidth="2"
                  strokeDasharray="4 4"
                />

                {/* Target ETA indicator point */}
                <circle cx="210" cy="115" r="5" fill="#00E5FF" />
                <circle cx="210" cy="115" r="10" fill="none" stroke="#00E5FF" opacity="0.5" />
                <text x="215" y="110" fill="#FFFFFF" fontSize="11" fontWeight="600" fontFamily="var(--font-mono)">
                  Arrival ETA ({predictionData?.availability_probability ?? 88}% Free)
                </text>
              </svg>
            </div>

            {/* Time labels */}
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--pz-text-muted)', fontFamily: 'var(--font-mono)', marginTop: '8px' }}>
              <span>12:00</span>
              <span>14:00 (Now)</span>
              <span>16:00</span>
              <span>18:00 (Rush)</span>
              <span>20:00</span>
              <span>22:00</span>
            </div>
          </Card>

          {/* Congestion Heat Map */}
          <HeatMapContainer />
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
              <RecommendationCard
                rank={1}
                facilityName="Apex SkyTower Deck"
                matchScore={98}
                distanceKm={0.4}
                openBays={42}
                estimatedCost={2.80}
                reason="Optimal proximity to your destination with high bay vacancy probability."
                onSelect={() => navigate('/parking')}
              />

              <RecommendationCard
                rank={2}
                facilityName="Grand Plaza Underground"
                matchScore={89}
                distanceKm={0.7}
                openBays={28}
                estimatedCost={3.50}
                reason="Covered garage with direct concourse elevator connection."
                onSelect={() => navigate('/parking')}
              />

              <RecommendationCard
                rank={3}
                facilityName="CyberPort Terminal 2"
                matchScore={82}
                distanceKm={1.2}
                openBays={84}
                estimatedCost={1.90}
                reason="Best rate for long-duration stays with 350kW supercharging."
                onSelect={() => navigate('/parking')}
              />
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
                factor="MICRO-WEATHER"
                message="Light rain detected downtown -> +8% higher demand for covered basement bays."
              />
              <InsightCard
                type="traffic"
                severity="WARNING"
                factor="INGRESS RE-ROUTING"
                message="Gate A undergoing optical sensor recalibration; traffic seamlessly steered to Gate B Express."
              />
              <InsightCard
                type="recommendation"
                severity="SUCCESS"
                factor="OPTIMAL DEPARTURE"
                message="Plan departure before 17:15 to bypass estimated 14-min downtown bottleneck."
              />
            </div>

            {/* Neural Hold CTA */}
            <div style={{ marginTop: '1.25rem', borderTop: '1px solid var(--pz-border-subtle)', paddingTop: '1rem' }}>
              <Button
                variant="ai"
                size="md"
                onClick={() => navigate('/parking')}
                rightIcon={<ArrowRight size={16} />}
                style={{ width: '100%' }}
              >
                Lock Bay with Neural Hold
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
