import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Navbar } from '../components/layout/Navbar';
import { Footer } from '../components/layout/Footer';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import {
  MapPin,
  Calendar,
  Zap,
  ArrowRight,
  Brain,
  Timer,
  Sparkles,
  TrendingUp,
} from 'lucide-react';

const Home: React.FC = () => {
  const navigate = useNavigate();
  const [selectedCity, setSelectedCity] = useState('Metropolis Central');
  const [activeSlot, setActiveSlot] = useState<number | null>(14);

  // Live bay mock items for hero HUD preview
  const heroSlots = [
    { id: 10, num: 'A-10', status: 'occupied' },
    { id: 11, num: 'A-11', status: 'available' },
    { id: 12, num: 'A-12', status: 'reserved' },
    { id: 13, num: 'A-13', status: 'occupied' },
    { id: 14, num: 'A-14', status: 'ai-recommended', match: '98%' },
    { id: 15, num: 'A-15', status: 'available' },
    { id: 16, num: 'A-16', status: 'occupied' },
    { id: 17, num: 'A-17', status: 'available' },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh', backgroundColor: 'var(--pz-bg)' }}>
      <Navbar />

      {/* Hero Section */}
      <section
        style={{
          position: 'relative',
          padding: '5rem 2rem 4rem 2rem',
          maxWidth: '1360px',
          margin: '0 auto',
          width: '100%',
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
          gap: '3.5rem',
          alignItems: 'center',
        }}
      >
        {/* Left Column: Headline & Search */}
        <div>
          {/* Eyebrow Pill */}
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '8px',
              padding: '4px 14px',
              borderRadius: '9999px',
              backgroundColor: 'rgba(0, 229, 255, 0.1)',
              border: '1px solid rgba(0, 229, 255, 0.3)',
              marginBottom: '1.5rem',
            }}
          >
            <Sparkles size={14} color="var(--pz-secondary)" />
            <span style={{ fontSize: '0.8125rem', fontWeight: 600, color: 'var(--pz-secondary)', letterSpacing: '0.02em' }}>
              Autonomous Mobility • Powered by Neural IoT Telemetry
            </span>
          </div>

          {/* Hero Headline */}
          <h1 className="text-hero" style={{ marginBottom: '1.25rem' }}>
            Find it. Reserve it. <br />
            <span className="text-gradient-ai">Predict it.</span>
          </h1>

          <p className="text-body-lg" style={{ marginBottom: '2.5rem', maxWidth: '580px' }}>
            Next-generation urban parking orchestration. Eliminate parking search times with real-time sensor telemetry, guaranteed neural slot reservations, and dynamic arrival forecasting.
          </p>

          {/* Interactive Quick-Search Widget */}
          <div
            className="glass-panel"
            style={{
              padding: '1.25rem',
              borderRadius: '16px',
              boxShadow: 'var(--pz-shadow-card)',
              display: 'flex',
              flexDirection: 'column',
              gap: '1rem',
              maxWidth: '560px',
            }}
          >
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '10px' }}>
              {/* Destination */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '10px 14px', backgroundColor: 'rgba(255, 255, 255, 0.03)', borderRadius: '10px', border: '1px solid var(--pz-border-subtle)' }}>
                <MapPin size={18} color="var(--pz-secondary)" />
                <div>
                  <span style={{ fontSize: '0.6875rem', color: 'var(--pz-text-muted)', display: 'block' }}>Destination</span>
                  <input
                    type="text"
                    value={selectedCity}
                    onChange={(e) => setSelectedCity(e.target.value)}
                    style={{ background: 'transparent', border: 'none', color: '#FFFFFF', fontSize: '0.875rem', fontWeight: 500, width: '100%' }}
                  />
                </div>
              </div>

              {/* Time Window */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '10px 14px', backgroundColor: 'rgba(255, 255, 255, 0.03)', borderRadius: '10px', border: '1px solid var(--pz-border-subtle)' }}>
                <Calendar size={18} color="var(--pz-secondary)" />
                <div>
                  <span style={{ fontSize: '0.6875rem', color: 'var(--pz-text-muted)', display: 'block' }}>Arrival Window</span>
                  <span style={{ fontSize: '0.875rem', color: '#FFFFFF', fontWeight: 500 }}>Today, 15:30 EDT</span>
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '10px', paddingTop: '4px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.8125rem', color: 'var(--pz-text-secondary)' }}>
                <Zap size={14} color="var(--pz-secondary)" />
                <span>EV 350kW Fast-Charge Filter Active</span>
              </div>

              <Button
                variant="primary"
                size="md"
                onClick={() => navigate('/parking')}
                rightIcon={<ArrowRight size={16} />}
              >
                Search 12,000+ Slots
              </Button>
            </div>
          </div>
        </div>

        {/* Right Column: Hero Interactive Preview HUD */}
        <div style={{ position: 'relative' }}>
          <div
            className="glass-card border-glow-cyan"
            style={{
              padding: '1.75rem',
              borderRadius: '20px',
              position: 'relative',
              overflow: 'hidden',
            }}
          >
            {/* HUD Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem', borderBottom: '1px solid var(--pz-border-subtle)', paddingBottom: '1rem' }}>
              <div>
                <span style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--pz-secondary)', fontFamily: 'var(--font-mono)' }}>
                  LIVE DECK SIMULATOR
                </span>
                <h3 style={{ fontSize: '1.1875rem', fontWeight: 600, color: '#FFFFFF', marginTop: '2px' }}>
                  Metropolis Central • Level 3-B VIP
                </h3>
              </div>

              <div style={{ textAlign: 'right' }}>
                <span style={{ fontSize: '1.25rem', fontWeight: 700, color: '#10B981', fontFamily: 'var(--font-mono)' }}>
                  84.6% Full
                </span>
                <span style={{ fontSize: '0.6875rem', color: 'var(--pz-text-muted)', display: 'block' }}>
                  14 Open Bays
                </span>
              </div>
            </div>

            {/* Interactive Slot Grid Preview */}
            <div style={{ marginBottom: '1.25rem' }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-secondary)', display: 'block', marginBottom: '8px' }}>
                Sub-Meter Ultrasonic Bay Telemetry:
              </span>
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(4, 1fr)',
                  gap: '8px',
                }}
              >
                {heroSlots.map((s) => {
                  const isRec = s.status === 'ai-recommended';
                  const isFree = s.status === 'available' || isRec;
                  const isPicked = activeSlot === s.id;

                  return (
                    <div
                      key={s.id}
                      onClick={() => isFree && setActiveSlot(s.id)}
                      style={{
                        padding: '10px 6px',
                        borderRadius: '10px',
                        textAlign: 'center',
                        cursor: isFree ? 'pointer' : 'default',
                        backgroundColor: isRec
                          ? 'rgba(139, 92, 246, 0.25)'
                          : s.status === 'available'
                          ? 'rgba(16, 185, 129, 0.15)'
                          : s.status === 'reserved'
                          ? 'rgba(245, 158, 11, 0.15)'
                          : 'rgba(100, 116, 139, 0.1)',
                        border: isPicked
                          ? '2px solid var(--pz-secondary)'
                          : isRec
                          ? '1px solid rgba(139, 92, 246, 0.6)'
                          : s.status === 'available'
                          ? '1px solid rgba(16, 185, 129, 0.4)'
                          : '1px solid var(--pz-border-subtle)',
                        boxShadow: isRec ? '0 0 12px rgba(139, 92, 246, 0.35)' : 'none',
                        transition: 'all 0.2s',
                      }}
                    >
                      <span style={{ fontSize: '0.875rem', fontWeight: 700, fontFamily: 'var(--font-mono)', color: isRec ? '#C084FC' : s.status === 'available' ? '#10B981' : 'var(--pz-text-secondary)', display: 'block' }}>
                        {s.num}
                      </span>
                      <span style={{ fontSize: '0.625rem', textTransform: 'uppercase', color: 'var(--pz-text-muted)', display: 'block', marginTop: '2px' }}>
                        {isRec ? 'AI Match' : s.status}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Neural Lock Banner */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '12px',
                borderRadius: '12px',
                backgroundColor: 'rgba(26, 91, 255, 0.15)',
                border: '1px solid rgba(26, 91, 255, 0.35)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Brain size={18} color="var(--pz-secondary)" />
                <div>
                  <span style={{ fontSize: '0.8125rem', fontWeight: 600, color: '#FFFFFF', display: 'block' }}>
                    Slot A-14 (AI Recommended)
                  </span>
                  <span style={{ fontSize: '0.6875rem', color: 'var(--pz-text-secondary)' }}>
                    Closest to elevator • 350kW DC Fast Charge
                  </span>
                </div>
              </div>

              <Button
                variant="secondary"
                size="sm"
                onClick={() => navigate('/parking')}
              >
                Hold Bay
              </Button>
            </div>
          </div>
        </div>
      </section>

      {/* Stats Ticker Ribbon */}
      <section
        style={{
          borderTop: '1px solid var(--pz-border-subtle)',
          borderBottom: '1px solid var(--pz-border-subtle)',
          backgroundColor: 'rgba(10, 14, 25, 0.75)',
          padding: '2.5rem 2rem',
        }}
      >
        <div
          style={{
            maxWidth: '1360px',
            margin: '0 auto',
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: '2rem',
            textAlign: 'center',
          }}
        >
          <div>
            <div style={{ fontSize: '2.5rem', fontWeight: 800, color: '#00E5FF', fontFamily: 'var(--font-mono)' }}>
              99.8%
            </div>
            <div style={{ fontSize: '0.875rem', color: 'var(--pz-text-secondary)', marginTop: '4px' }}>
              ALPR &amp; Prediction Accuracy
            </div>
          </div>

          <div>
            <div style={{ fontSize: '2.5rem', fontWeight: 800, color: '#FFFFFF', fontFamily: 'var(--font-mono)' }}>
              12,450+
            </div>
            <div style={{ fontSize: '0.875rem', color: 'var(--pz-text-secondary)', marginTop: '4px' }}>
              Connected Parking Bays
            </div>
          </div>

          <div>
            <div style={{ fontSize: '2.5rem', fontWeight: 800, color: '#10B981', fontFamily: 'var(--font-mono)' }}>
              14 min
            </div>
            <div style={{ fontSize: '0.875rem', color: 'var(--pz-text-secondary)', marginTop: '4px' }}>
              Avg Urban Search Time Saved
            </div>
          </div>

          <div>
            <div style={{ fontSize: '2.5rem', fontWeight: 800, color: '#8B5CF6', fontFamily: 'var(--font-mono)' }}>
              420k+
            </div>
            <div style={{ fontSize: '0.875rem', color: 'var(--pz-text-secondary)', marginTop: '4px' }}>
              Ultrasonic IoT Telemetry Pulses / Day
            </div>
          </div>
        </div>
      </section>

      {/* AI Intelligence Showcase */}
      <section
        id="ai-intelligence"
        style={{
          padding: '6rem 2rem',
          maxWidth: '1360px',
          margin: '0 auto',
          width: '100%',
        }}
      >
        <div style={{ textAlign: 'center', maxWidth: '680px', margin: '0 auto 4rem auto' }}>
          <span style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--pz-secondary)' }}>
            Neural Telemetry &amp; Machine Learning
          </span>
          <h2 className="text-page-title" style={{ marginTop: '0.5rem', marginBottom: '1rem' }}>
            Autonomous Predictions That Keep You Ahead
          </h2>
          <p className="text-body">
            Using recurrent LSTM temporal models and live environmental telemetry, ParkZenith forecasts parking availability before you even begin your commute.
          </p>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.5rem' }}>
          <Card glow="purple">
            <div style={{ width: '40px', height: '40px', borderRadius: '10px', backgroundColor: 'rgba(139, 92, 246, 0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '1rem' }}>
              <Brain size={22} color="#C084FC" />
            </div>
            <h3 style={{ fontSize: '1.1875rem', fontWeight: 600, color: '#FFFFFF', marginBottom: '0.5rem' }}>
              Arrival Probability Engine
            </h3>
            <p style={{ fontSize: '0.875rem', color: 'var(--pz-text-secondary)', lineHeight: 1.5 }}>
              Calculates millisecond precision assurance scores factoring in historical traffic patterns, city events, and real-time bay release rates.
            </p>
          </Card>

          <Card glow="cyan">
            <div style={{ width: '40px', height: '40px', borderRadius: '10px', backgroundColor: 'rgba(0, 229, 255, 0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '1rem' }}>
              <TrendingUp size={22} color="var(--pz-secondary)" />
            </div>
            <h3 style={{ fontSize: '1.1875rem', fontWeight: 600, color: '#FFFFFF', marginBottom: '0.5rem' }}>
              Dynamic Demand Forecasting
            </h3>
            <p style={{ fontSize: '0.875rem', color: 'var(--pz-text-secondary)', lineHeight: 1.5 }}>
              12-hour occupancy curves warn you of upcoming surges, allowing you to lock guaranteed parking slots at off-peak rates.
            </p>
          </Card>

          <Card glow="emerald">
            <div style={{ width: '40px', height: '40px', borderRadius: '10px', backgroundColor: 'rgba(16, 185, 129, 0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '1rem' }}>
              <Timer size={22} color="var(--pz-success)" />
            </div>
            <h3 style={{ fontSize: '1.1875rem', fontWeight: 600, color: '#FFFFFF', marginBottom: '0.5rem' }}>
              Queue &amp; Clearance Latency
            </h3>
            <p style={{ fontSize: '0.875rem', color: 'var(--pz-text-secondary)', lineHeight: 1.5 }}>
              Automatic License Plate Recognition (ALPR) lifts barriers in under 300ms, maintaining average queue latency under 2.4 minutes.
            </p>
          </Card>
        </div>
      </section>

      {/* How It Works Section */}
      <section
        id="how-it-works"
        style={{
          padding: '6rem 2rem',
          backgroundColor: 'rgba(15, 19, 30, 0.5)',
          borderTop: '1px solid var(--pz-border-subtle)',
          borderBottom: '1px solid var(--pz-border-subtle)',
        }}
      >
        <div style={{ maxWidth: '1360px', margin: '0 auto', width: '100%' }}>
          <div style={{ textAlign: 'center', maxWidth: '640px', margin: '0 auto 4rem auto' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--pz-secondary)' }}>
              Seamless Urban Flow
            </span>
            <h2 className="text-page-title" style={{ marginTop: '0.5rem', marginBottom: '1rem' }}>
              Find &rarr; Check &rarr; Reserve &rarr; Park &rarr; Predict
            </h2>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '2rem' }}>
            {[
              { step: '01', title: 'Find', desc: 'Browse live occupancy across connected municipal hubs with verified sensor vacancy.' },
              { step: '02', title: 'Reserve', desc: '1-tap guaranteed reservation synced instantly with your vehicle license plate.' },
              { step: '03', title: 'Park', desc: 'Touchless entry barrier lift with indoor sub-meter AR navigation to your bay.' },
              { step: '04', title: 'Predict', desc: 'Neural AI recommends departure windows and guarantees EV charging access.' },
            ].map((s) => (
              <div
                key={s.step}
                className="glass-card"
                style={{ padding: '1.75rem', position: 'relative' }}
              >
                <div style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--pz-secondary)', fontFamily: 'var(--font-mono)', marginBottom: '0.75rem' }}>
                  {s.step}
                </div>
                <h3 style={{ fontSize: '1.25rem', fontWeight: 600, color: '#FFFFFF', marginBottom: '0.5rem' }}>
                  {s.title}
                </h3>
                <p style={{ fontSize: '0.875rem', color: 'var(--pz-text-secondary)', lineHeight: 1.5 }}>
                  {s.desc}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Conversion Banner */}
      <section style={{ padding: '6rem 2rem', textAlign: 'center', maxWidth: '960px', margin: '0 auto', width: '100%' }}>
        <div
          className="glass-card border-glow-cyan"
          style={{
            padding: '4rem 2rem',
            borderRadius: '24px',
            position: 'relative',
            overflow: 'hidden',
          }}
        >
          <h2 className="text-page-title" style={{ marginBottom: '1rem' }}>
            Ready to Transform Your Urban Transit?
          </h2>
          <p className="text-body-lg" style={{ maxWidth: '580px', margin: '0 auto 2.5rem auto' }}>
            Join thousands of smart drivers and fleet operators enjoying stress-free, predictable urban parking.
          </p>

          <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: '1rem' }}>
            <Button
              variant="secondary"
              size="lg"
              onClick={() => navigate('/register')}
              rightIcon={<ArrowRight size={18} />}
            >
              Get Started Free
            </Button>
            <Button
              variant="outline"
              size="lg"
              onClick={() => navigate('/parking')}
            >
              Explore Live Garages
            </Button>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
};

export default Home;
