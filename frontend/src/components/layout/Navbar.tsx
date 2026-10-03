import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Radio, Menu, X, ArrowRight } from 'lucide-react';
import { Button } from '../ui/Button';
import { Avatar } from '../ui/Avatar';
import { useAuth } from '../../hooks/useAuth';

export const Navbar: React.FC = () => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const { isAuthenticated, user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <header
      className="glass-header"
      style={{
        position: 'sticky',
        top: 0,
        zIndex: 100,
        width: '100%',
        padding: '0.875rem 2rem',
      }}
    >
      <div
        style={{
          maxWidth: '1360px',
          margin: '0 auto',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        {/* Brand Logo & Telemetry Pill */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem' }}>
          <Link
            to="/"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              textDecoration: 'none',
            }}
          >
            <div
              style={{
                width: '36px',
                height: '36px',
                borderRadius: '10px',
                background: 'linear-gradient(135deg, #1A5BFF 0%, #00E5FF 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: '0 0 16px rgba(0, 229, 255, 0.4)',
              }}
            >
              <Radio size={20} color="#090B10" />
            </div>
            <div>
              <span
                style={{
                  fontSize: '1.25rem',
                  fontWeight: 800,
                  letterSpacing: '-0.02em',
                  color: '#FFFFFF',
                  fontFamily: 'var(--font-heading)',
                }}
              >
                Park<span className="text-gradient-cyan">Zenith</span>
              </span>
            </div>
          </Link>

          {/* Live Telemetry Status Badge */}
          <div
            style={{
              display: 'none',
              alignItems: 'center',
              gap: '6px',
              padding: '3px 10px',
              borderRadius: '9999px',
              backgroundColor: 'rgba(16, 185, 129, 0.1)',
              border: '1px solid rgba(16, 185, 129, 0.25)',
              fontSize: '0.75rem',
              color: 'var(--pz-success)',
              fontFamily: 'var(--font-mono)',
            }}
            className="desktop-telemetry-badge"
          >
            <span className="telemetry-pulse" />
            <span>Telemetry Online (4ms)</span>
          </div>
        </div>

        {/* Desktop Navigation Links */}
        <nav
          style={{
            display: 'none',
            alignItems: 'center',
            gap: '2rem',
          }}
          className="desktop-nav"
        >
          <a
            href="#live-slots"
            style={{ fontSize: '0.9375rem', color: 'var(--pz-text-secondary)', transition: 'color 0.2s' }}
            onMouseEnter={(e) => (e.currentTarget.style.color = '#FFFFFF')}
            onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--pz-text-secondary)')}
          >
            Live Availability
          </a>
          <a
            href="#ai-intelligence"
            style={{ fontSize: '0.9375rem', color: 'var(--pz-text-secondary)', transition: 'color 0.2s' }}
            onMouseEnter={(e) => (e.currentTarget.style.color = '#FFFFFF')}
            onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--pz-text-secondary)')}
          >
            AI Predictions
          </a>
          <a
            href="#how-it-works"
            style={{ fontSize: '0.9375rem', color: 'var(--pz-text-secondary)', transition: 'color 0.2s' }}
            onMouseEnter={(e) => (e.currentTarget.style.color = '#FFFFFF')}
            onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--pz-text-secondary)')}
          >
            How It Works
          </a>
          <Link
            to="/parking"
            style={{ fontSize: '0.9375rem', color: 'var(--pz-text-secondary)', transition: 'color 0.2s' }}
            onMouseEnter={(e) => (e.currentTarget.style.color = '#FFFFFF')}
            onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--pz-text-secondary)')}
          >
            Find Parking
          </Link>
        </nav>

        {/* Right CTA / Auth Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          {isAuthenticated ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <Link
                to="/profile"
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '4px 10px',
                  borderRadius: '8px',
                  backgroundColor: 'rgba(255, 255, 255, 0.05)',
                  border: '1px solid var(--pz-border-subtle)',
                  color: '#FFFFFF',
                  fontSize: '0.8125rem',
                  textDecoration: 'none',
                }}
              >
                <Avatar name={user?.full_name || user?.email || 'User'} size="sm" />
                <span style={{ maxWidth: '100px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {user?.full_name?.split(' ')[0] || user?.email?.split('@')[0] || 'Profile'}
                </span>
              </Link>
              <Button
                variant="primary"
                size="sm"
                onClick={() => navigate('/dashboard')}
                rightIcon={<ArrowRight size={14} />}
              >
                Dashboard
              </Button>
              <Button variant="ghost" size="sm" onClick={logout}>
                Sign Out
              </Button>
            </div>
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => navigate('/login')}
                style={{ color: '#FFFFFF' }}
              >
                Sign In
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={() => navigate('/register')}
                rightIcon={<ArrowRight size={14} />}
              >
                Get Started
              </Button>
            </div>
          )}

          {/* Mobile Menu Hamburger */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            style={{
              display: 'none',
              padding: '6px',
              color: '#FFFFFF',
            }}
            className="mobile-hamburger"
            aria-label="Toggle navigation menu"
          >
            {mobileMenuOpen ? <X size={22} /> : <Menu size={22} />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '1rem',
            padding: '1.5rem',
            backgroundColor: '#0F131E',
            borderTop: '1px solid var(--pz-border)',
            marginTop: '0.875rem',
          }}
        >
          <Link
            to="/parking"
            onClick={() => setMobileMenuOpen(false)}
            style={{ fontSize: '1rem', color: '#FFFFFF', padding: '0.5rem 0' }}
          >
            Find Parking
          </Link>
          <a
            href="#ai-intelligence"
            onClick={() => setMobileMenuOpen(false)}
            style={{ fontSize: '1rem', color: 'var(--pz-text-secondary)', padding: '0.5rem 0' }}
          >
            AI Predictions
          </a>
          <a
            href="#how-it-works"
            onClick={() => setMobileMenuOpen(false)}
            style={{ fontSize: '1rem', color: 'var(--pz-text-secondary)', padding: '0.5rem 0' }}
          >
            How It Works
          </a>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginTop: '0.5rem' }}>
            {isAuthenticated ? (
              <>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => {
                    setMobileMenuOpen(false);
                    navigate('/dashboard');
                  }}
                  rightIcon={<ArrowRight size={14} />}
                >
                  Dashboard
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setMobileMenuOpen(false);
                    navigate('/profile');
                  }}
                >
                  Profile ({user?.email})
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setMobileMenuOpen(false);
                    logout();
                  }}
                  style={{ color: 'var(--pz-error)' }}
                >
                  Sign Out
                </Button>
              </>
            ) : (
              <div style={{ display: 'flex', gap: '0.75rem' }}>
                <Button
                  variant="outline"
                  size="sm"
                  style={{ flex: 1 }}
                  onClick={() => {
                    setMobileMenuOpen(false);
                    navigate('/login');
                  }}
                >
                  Sign In
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  style={{ flex: 1 }}
                  onClick={() => {
                    setMobileMenuOpen(false);
                    navigate('/register');
                  }}
                >
                  Launch App
                </Button>
              </div>
            )}
          </div>
        </div>
      )}

      <style>{`
        @media (min-width: 860px) {
          .desktop-nav { display: flex !important; }
          .desktop-telemetry-badge { display: flex !important; }
        }
        @media (max-width: 859px) {
          .mobile-hamburger { display: flex !important; }
        }
      `}</style>
    </header>
  );
};
