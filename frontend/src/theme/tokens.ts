// ParkZenith Centralized Design Tokens
// Smart Mobility + Parking + Real-Time Telemetry + AI Intelligence

export const colors = {
  // Brand & Accent Foundations
  primary: '#1A5BFF',
  primaryHover: '#004DEA',
  primaryLight: '#B7C4FF',
  primarySubtle: 'rgba(26, 91, 255, 0.15)',
  
  secondary: '#00E5FF',
  secondaryHover: '#00C8E0',
  secondarySubtle: 'rgba(0, 229, 255, 0.12)',
  
  // Dark Canvas & Surfaces
  background: '#090B10',
  backgroundElevated: '#0F131E',
  surface: '#131722',
  surfaceCard: '#181C25',
  surfaceDark: '#1E2330',
  surfaceHover: '#262A35',
  
  // Borders
  border: '#2A3143',
  borderSubtle: 'rgba(255, 255, 255, 0.08)',
  borderGlow: 'rgba(0, 229, 255, 0.4)',
  
  // Typography Colors
  textPrimary: '#FFFFFF',
  textSecondary: '#94A3B8',
  textMuted: '#64748B',
  textInverse: '#090B10',
  
  // Feedback & Status
  success: '#10B981',
  successSubtle: 'rgba(16, 185, 129, 0.15)',
  warning: '#F59E0B',
  warningSubtle: 'rgba(245, 158, 11, 0.15)',
  error: '#F43F5E',
  errorSubtle: 'rgba(244, 63, 94, 0.15)',
  info: '#0EA5E9',
  infoSubtle: 'rgba(14, 165, 233, 0.15)',

  // Parking Domain States
  parking: {
    available: '#10B981',      // Emerald Green
    availableSubtle: 'rgba(16, 185, 129, 0.15)',
    occupied: '#64748B',       // Muted Slate / Dark
    occupiedSubtle: 'rgba(100, 116, 139, 0.15)',
    reserved: '#F59E0B',       // Amber
    reservedSubtle: 'rgba(245, 158, 11, 0.15)',
    maintenance: '#F43F5E',    // Rose Red
    maintenanceSubtle: 'rgba(244, 63, 94, 0.15)',
    disabled: '#3B82F6',       // Accessible Blue
    disabledSubtle: 'rgba(59, 130, 246, 0.15)',
  },

  // AI & Predictive Intelligence States
  ai: {
    prediction: '#8B5CF6',     // Violet / Neon Purple
    predictionSubtle: 'rgba(139, 92, 246, 0.15)',
    insight: '#D946EF',        // Fuchsia
    recommendation: '#00E5FF',  // Cyan
    forecast: '#38BDF8',       // Sky Blue
    confidenceHigh: '#10B981',
    confidenceMedium: '#F59E0B',
    confidenceLow: '#F43F5E',
  },
} as const;

export const typography = {
  fonts: {
    heading: "'Outfit', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
    body: "'Outfit', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
    telemetry: "'JetBrains Mono', monospace",
  },
  weights: {
    regular: 400,
    medium: 500,
    semibold: 600,
    bold: 700,
    extrabold: 800,
  },
} as const;

export const shadows = {
  glowCyan: '0 0 24px -4px rgba(0, 229, 255, 0.35)',
  glowBlue: '0 0 24px -4px rgba(26, 91, 255, 0.4)',
  glowEmerald: '0 0 20px -4px rgba(16, 185, 129, 0.35)',
  glowPurple: '0 0 24px -4px rgba(139, 92, 246, 0.4)',
  card: '0 12px 32px -4px rgba(0, 0, 0, 0.5)',
  elevated: '0 20px 48px -8px rgba(0, 0, 0, 0.7)',
} as const;

export const transitions = {
  fast: '150ms cubic-bezier(0.4, 0, 0.2, 1)',
  normal: '250ms cubic-bezier(0.4, 0, 0.2, 1)',
  slow: '400ms cubic-bezier(0.16, 1, 0.3, 1)',
  spring: '500ms cubic-bezier(0.34, 1.56, 0.64, 1)',
} as const;
