import React from 'react';
import { Radio, ShieldCheck, Heart } from 'lucide-react';
import { Link } from 'react-router-dom';

export const Footer: React.FC = () => {
  return (
    <footer
      style={{
        backgroundColor: '#090B10',
        borderTop: '1px solid var(--pz-border-subtle)',
        padding: '4rem 2rem 2rem 2rem',
        marginTop: 'auto',
      }}
    >
      <div
        style={{
          maxWidth: '1360px',
          margin: '0 auto',
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: '2.5rem',
          marginBottom: '3rem',
        }}
      >
        {/* Brand Column */}
        <div style={{ maxWidth: '320px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '1rem' }}>
            <div
              style={{
                width: '32px',
                height: '32px',
                borderRadius: '8px',
                background: 'linear-gradient(135deg, #1A5BFF 0%, #00E5FF 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Radio size={18} color="#090B10" />
            </div>
            <span style={{ fontSize: '1.25rem', fontWeight: 800, color: '#FFFFFF', fontFamily: 'var(--font-heading)' }}>
              Park<span className="text-gradient-cyan">Zenith</span>
            </span>
          </div>
          <p style={{ fontSize: '0.875rem', color: 'var(--pz-text-secondary)', lineHeight: 1.5, marginBottom: '1.25rem' }}>
            Next-gen smart parking management and neural AI prediction system. Find it. Reserve it. Predict it.
          </p>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '0.75rem', color: 'var(--pz-success)', padding: '4px 10px', borderRadius: '9999px', backgroundColor: 'rgba(16, 185, 129, 0.1)', border: '1px solid rgba(16, 185, 129, 0.25)' }}>
            <span className="telemetry-pulse" />
            <span>Operational SLA 99.98%</span>
          </div>
        </div>

        {/* Platform Links */}
        <div>
          <h4 style={{ fontSize: '0.875rem', fontWeight: 600, color: '#FFFFFF', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '1rem' }}>
            Platform
          </h4>
          <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '0.625rem', fontSize: '0.875rem', color: 'var(--pz-text-secondary)' }}>
            <li><Link to="/parking">Find Parking</Link></li>
            <li><Link to="/predictions">Neural Predictions</Link></li>
            <li><Link to="/reservations">Real-time Reservations</Link></li>
            <li><Link to="/sessions">Active Sessions</Link></li>
            <li><Link to="/payments">Billing &amp; Payments</Link></li>
          </ul>
        </div>

        {/* Technology */}
        <div>
          <h4 style={{ fontSize: '0.875rem', fontWeight: 600, color: '#FFFFFF', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '1rem' }}>
            Technology
          </h4>
          <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '0.625rem', fontSize: '0.875rem', color: 'var(--pz-text-secondary)' }}>
            <li>Neural LSTM Forecasting</li>
            <li>ALPR Express Gate Lift</li>
            <li>Ultrasonic Bay Telemetry</li>
            <li>Dynamic Demand Pricing</li>
            <li>Sub-GHz LoRa Mesh Sync</li>
          </ul>
        </div>

        {/* Trust & Compliance */}
        <div>
          <h4 style={{ fontSize: '0.875rem', fontWeight: 600, color: '#FFFFFF', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '1rem' }}>
            Compliance &amp; Trust
          </h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.8125rem', color: 'var(--pz-text-secondary)' }}>
              <ShieldCheck size={16} color="var(--pz-success)" />
              <span>SOC2 Type II Certified</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.8125rem', color: 'var(--pz-text-secondary)' }}>
              <ShieldCheck size={16} color="var(--pz-success)" />
              <span>ISO 27001 Autonomous Security</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.8125rem', color: 'var(--pz-text-secondary)' }}>
              <ShieldCheck size={16} color="var(--pz-success)" />
              <span>End-to-End Encrypted Telemetry</span>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Bar */}
      <div
        style={{
          maxWidth: '1360px',
          margin: '0 auto',
          borderTop: '1px solid var(--pz-border-subtle)',
          paddingTop: '1.5rem',
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '1rem',
          fontSize: '0.8125rem',
          color: 'var(--pz-text-muted)',
        }}
      >
        <div>
          &copy; 2026 ParkZenith Inc. All rights reserved.
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          Crafted for Smart Mobility &amp; Autonomous Transportation <Heart size={12} color="#F43F5E" fill="#F43F5E" />
        </div>
      </div>
    </footer>
  );
};
