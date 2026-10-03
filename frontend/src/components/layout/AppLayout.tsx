import React, { useState } from 'react';
import { NavLink, Outlet, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import {
  LayoutDashboard,
  MapPin,
  CalendarCheck,
  Clock,
  CreditCard,
  Brain,
  User,
  Shield,
  LogOut,
  Radio,
  Bell,
  Menu,
  X,
  Search,
} from 'lucide-react';
import { Avatar } from '../ui/Avatar';
import { Dropdown } from '../ui/Dropdown';
import { useWebSocket } from '../../hooks/useWebSocket';

export const AppLayout: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const { connectionStatus } = useWebSocket();

  const isAdmin = Boolean(user?.is_superuser || user?.role === 'admin');

  const navItems = [
    { label: 'Dashboard', path: '/dashboard', icon: <LayoutDashboard size={18} /> },
    { label: 'Find Parking', path: '/parking', icon: <MapPin size={18} /> },
    { label: 'Reservations', path: '/reservations', icon: <CalendarCheck size={18} /> },
    { label: 'Sessions', path: '/sessions', icon: <Clock size={18} /> },
    { label: 'Payments', path: '/payments', icon: <CreditCard size={18} /> },
    { label: 'AI Predictions', path: '/predictions', icon: <Brain size={18} /> },
    { label: 'Profile', path: '/profile', icon: <User size={18} /> },
  ];

  if (isAdmin) {
    navItems.push({ label: 'Admin Console', path: '/admin', icon: <Shield size={18} /> });
  }

  const getStatusIndicator = () => {
    switch (connectionStatus) {
      case 'connected':
        return { label: 'Live Telemetry (4ms)', color: 'var(--pz-success)', bg: 'rgba(16, 185, 129, 0.12)' };
      case 'connecting':
      case 'reconnecting':
        return { label: 'Syncing Mesh...', color: 'var(--pz-warning)', bg: 'rgba(245, 158, 11, 0.12)' };
      case 'disconnected':
      default:
        return { label: 'Telemetry Synced (DB)', color: 'var(--pz-secondary)', bg: 'rgba(0, 229, 255, 0.12)' };
    }
  };

  const status = getStatusIndicator();

  const userMenuItems = [
    { id: 'profile', label: 'My Account', icon: <User size={15} />, onClick: () => navigate('/profile') },
    { id: 'reservations', label: 'My Bookings', icon: <CalendarCheck size={15} />, onClick: () => navigate('/reservations') },
    { id: 'logout', label: 'Sign Out', icon: <LogOut size={15} />, danger: true, onClick: logout },
  ];

  return (
    <div style={{ display: 'flex', minHeight: '100vh', width: '100%', backgroundColor: 'var(--pz-bg)' }}>
      {/* Desktop Fixed Sidebar */}
      <aside
        style={{
          width: '260px',
          backgroundColor: '#0A0E19',
          borderRight: '1px solid var(--pz-border-subtle)',
          display: 'flex',
          flexDirection: 'column',
          position: 'sticky',
          top: 0,
          height: '100vh',
          zIndex: 40,
          flexShrink: 0,
        }}
        className="app-desktop-sidebar"
      >
        {/* Brand Area */}
        <div style={{ padding: '1.25rem 1.5rem', borderBottom: '1px solid var(--pz-border-subtle)' }}>
          <NavLink to="/dashboard" style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div
              style={{
                width: '34px',
                height: '34px',
                borderRadius: '10px',
                background: 'linear-gradient(135deg, #1A5BFF 0%, #00E5FF 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: '0 0 16px rgba(0, 229, 255, 0.35)',
              }}
            >
              <Radio size={18} color="#090B10" />
            </div>
            <div>
              <span style={{ fontSize: '1.1875rem', fontWeight: 800, color: '#FFFFFF', fontFamily: 'var(--font-heading)' }}>
                Park<span className="text-gradient-cyan">Zenith</span>
              </span>
              <span style={{ fontSize: '0.6875rem', color: 'var(--pz-text-muted)', display: 'block', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Autonomous Command
              </span>
            </div>
          </NavLink>

          {/* WebSocket Status Indicator */}
          <div
            style={{
              marginTop: '0.875rem',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '4px 10px',
              borderRadius: '9999px',
              backgroundColor: status.bg,
              fontSize: '0.6875rem',
              color: status.color,
              fontFamily: 'var(--font-mono)',
            }}
          >
            <span
              style={{
                width: '6px',
                height: '6px',
                borderRadius: '50%',
                backgroundColor: status.color,
              }}
              className="animate-pulse-glow"
            />
            <span>{status.label}</span>
          </div>
        </div>

        {/* Navigation List */}
        <nav style={{ flex: 1, padding: '1rem 0.875rem', display: 'flex', flexDirection: 'column', gap: '4px', overflowY: 'auto' }}>
          {navItems.map((item) => {
            const isActive = location.pathname === item.path || (item.path !== '/dashboard' && location.pathname.startsWith(item.path));
            return (
              <NavLink
                key={item.path}
                to={item.path}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                  padding: '10px 14px',
                  borderRadius: '10px',
                  fontSize: '0.9375rem',
                  fontWeight: 500,
                  color: isActive ? '#FFFFFF' : 'var(--pz-text-secondary)',
                  backgroundColor: isActive ? 'rgba(26, 91, 255, 0.2)' : 'transparent',
                  border: isActive ? '1px solid rgba(26, 91, 255, 0.4)' : '1px solid transparent',
                  boxShadow: isActive ? '0 0 12px rgba(26, 91, 255, 0.25)' : 'none',
                  transition: 'all 0.15s ease',
                }}
              >
                <span style={{ color: isActive ? 'var(--pz-secondary)' : 'currentColor' }}>
                  {item.icon}
                </span>
                <span>{item.label}</span>
              </NavLink>
            );
          })}
        </nav>

        {/* Bottom User Area */}
        <div style={{ padding: '1rem 1.25rem', borderTop: '1px solid var(--pz-border-subtle)', backgroundColor: 'rgba(0, 0, 0, 0.2)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', overflow: 'hidden' }}>
              <Avatar name={user?.full_name || user?.email || 'User'} size="sm" status="online" />
              <div style={{ overflow: 'hidden' }}>
                <span style={{ fontSize: '0.875rem', fontWeight: 600, color: '#FFFFFF', display: 'block', textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}>
                  {user?.full_name || 'Driver'}
                </span>
                <span style={{ fontSize: '0.6875rem', color: 'var(--pz-text-muted)', display: 'block', textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}>
                  {user?.vehicle_number || user?.email || 'KA-01-MJ-5555'}
                </span>
              </div>
            </div>

            <button
              onClick={logout}
              title="Sign Out"
              style={{
                color: 'var(--pz-text-muted)',
                padding: '6px',
                borderRadius: '6px',
                display: 'flex',
                transition: 'color 0.2s',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--pz-error)')}
              onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--pz-text-muted)')}
            >
              <LogOut size={16} />
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        {/* Top Header */}
        <header
          className="glass-header"
          style={{
            position: 'sticky',
            top: 0,
            zIndex: 30,
            padding: '0.75rem 2rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '1rem',
          }}
        >
          {/* Mobile Menu Button + Title */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <button
              onClick={() => setMobileSidebarOpen(true)}
              style={{ display: 'none', color: '#FFFFFF', padding: '6px' }}
              className="app-mobile-menu-btn"
              aria-label="Open navigation menu"
            >
              <Menu size={22} />
            </button>

            {/* Quick Search Trigger */}
            <div
              onClick={() => navigate('/parking')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '6px 14px',
                borderRadius: '9999px',
                backgroundColor: 'rgba(255, 255, 255, 0.04)',
                border: '1px solid var(--pz-border-subtle)',
                color: 'var(--pz-text-muted)',
                fontSize: '0.8125rem',
                cursor: 'pointer',
                width: '280px',
              }}
              className="header-search-box"
            >
              <Search size={15} color="var(--pz-text-muted)" />
              <span style={{ flex: 1 }}>Search facilities or slots...</span>
              <kbd style={{ fontSize: '0.625rem', padding: '1px 5px', borderRadius: '4px', backgroundColor: 'rgba(255,255,255,0.08)', fontFamily: 'var(--font-mono)' }}>
                ⌘K
              </kbd>
            </div>
          </div>

          {/* Right Header Badges & Actions */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            {/* Notifications Bell */}
            <div style={{ position: 'relative' }}>
              <button
                onClick={() => setNotificationsOpen(!notificationsOpen)}
                style={{
                  position: 'relative',
                  width: '36px',
                  height: '36px',
                  borderRadius: '10px',
                  backgroundColor: 'rgba(255, 255, 255, 0.04)',
                  border: '1px solid var(--pz-border-subtle)',
                  color: 'var(--pz-text-secondary)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
                aria-label="View notifications"
              >
                <Bell size={18} />
                <span
                  style={{
                    position: 'absolute',
                    top: '6px',
                    right: '6px',
                    width: '7px',
                    height: '7px',
                    borderRadius: '50%',
                    backgroundColor: 'var(--pz-secondary)',
                    boxShadow: '0 0 6px var(--pz-secondary)',
                  }}
                />
              </button>

              {notificationsOpen && (
                <div
                  style={{
                    position: 'absolute',
                    right: 0,
                    top: 'calc(100% + 8px)',
                    width: '320px',
                    backgroundColor: '#131722',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    borderRadius: '14px',
                    padding: '12px',
                    boxShadow: '0 12px 32px rgba(0, 0, 0, 0.7)',
                    zIndex: 60,
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingBottom: '8px', borderBottom: '1px solid var(--pz-border-subtle)' }}>
                    <span style={{ fontSize: '0.875rem', fontWeight: 600, color: '#FFFFFF' }}>Notifications</span>
                    <span style={{ fontSize: '0.75rem', color: 'var(--pz-secondary)' }}>Live Feed</span>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '8px', maxHeight: '240px', overflowY: 'auto' }}>
                    <div style={{ padding: '8px', borderRadius: '8px', backgroundColor: 'rgba(255,255,255,0.03)', fontSize: '0.8125rem' }}>
                      <span style={{ color: 'var(--pz-success)', fontWeight: 600, display: 'block' }}>Reservation Synced</span>
                      <span style={{ color: 'var(--pz-text-secondary)', fontSize: '0.75rem' }}>License plate matched for upcoming booking.</span>
                    </div>
                    <div style={{ padding: '8px', borderRadius: '8px', backgroundColor: 'rgba(255,255,255,0.03)', fontSize: '0.8125rem' }}>
                      <span style={{ color: 'var(--pz-secondary)', fontWeight: 600, display: 'block' }}>Neural Telemetry Update</span>
                      <span style={{ color: 'var(--pz-text-secondary)', fontSize: '0.75rem' }}>Favorable arrival window predicted for Downtown Central.</span>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Profile Dropdown */}
            <Dropdown
              trigger={
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                  <Avatar name={user?.full_name || user?.email || 'User'} size="sm" status="online" />
                  <span style={{ fontSize: '0.875rem', fontWeight: 500, color: '#FFFFFF', display: 'none' }} className="header-username">
                    {user?.full_name || 'Driver'}
                  </span>
                </div>
              }
              items={userMenuItems}
            />
          </div>
        </header>

        {/* Content Body */}
        <main style={{ flex: 1, padding: '1.5rem 2rem 4rem 2rem', maxWidth: '1440px', width: '100%', margin: '0 auto' }}>
          <Outlet />
        </main>
      </div>

      {/* Mobile Drawer Navigation */}
      {mobileSidebarOpen && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 100,
            display: 'flex',
          }}
        >
          <div
            style={{
              position: 'fixed',
              inset: 0,
              backgroundColor: 'rgba(0, 0, 0, 0.7)',
              backdropFilter: 'blur(4px)',
            }}
            onClick={() => setMobileSidebarOpen(false)}
          />
          <div
            style={{
              position: 'relative',
              width: '280px',
              maxWidth: '80%',
              backgroundColor: '#0A0E19',
              borderRight: '1px solid var(--pz-border)',
              display: 'flex',
              flexDirection: 'column',
              padding: '1.5rem',
              zIndex: 101,
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Radio size={20} color="var(--pz-secondary)" />
                <span style={{ fontSize: '1.125rem', fontWeight: 800, color: '#FFFFFF' }}>
                  Park<span className="text-gradient-cyan">Zenith</span>
                </span>
              </div>
              <button onClick={() => setMobileSidebarOpen(false)} style={{ color: 'var(--pz-text-muted)' }}>
                <X size={20} />
              </button>
            </div>

            <nav style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {navItems.map((item) => (
                <NavLink
                  key={item.path}
                  to={item.path}
                  onClick={() => setMobileSidebarOpen(false)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '12px',
                    padding: '10px 14px',
                    borderRadius: '8px',
                    fontSize: '0.9375rem',
                    color: location.pathname === item.path ? '#FFFFFF' : 'var(--pz-text-secondary)',
                    backgroundColor: location.pathname === item.path ? 'rgba(26, 91, 255, 0.25)' : 'transparent',
                  }}
                >
                  {item.icon}
                  <span>{item.label}</span>
                </NavLink>
              ))}
            </nav>

            <div style={{ marginTop: 'auto', borderTop: '1px solid var(--pz-border-subtle)', paddingTop: '1rem' }}>
              <button
                onClick={() => {
                  setMobileSidebarOpen(false);
                  logout();
                }}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                  color: 'var(--pz-error)',
                  fontSize: '0.875rem',
                  padding: '8px',
                }}
              >
                <LogOut size={16} /> Sign Out
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Media Queries for Sidebar and Responsive controls */}
      <style>{`
        @media (max-width: 992px) {
          .app-desktop-sidebar { display: none !important; }
          .app-mobile-menu-btn { display: flex !important; }
          .header-search-box { width: 200px !important; }
        }
        @media (min-width: 993px) {
          .header-username { display: inline !important; }
        }
        @media (max-width: 640px) {
          .header-search-box { display: none !important; }
        }
      `}</style>
    </div>
  );
};
