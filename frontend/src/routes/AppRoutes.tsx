import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { ProtectedRoute } from './ProtectedRoute';
import { useAuth } from '../hooks/useAuth';
import { LoadingSpinner } from '../components/ui/LoadingSpinner';

// Pages
import Home from '../pages/Home';
import Login from '../pages/Login';
import Register from '../pages/Register';
import Dashboard from '../pages/Dashboard';
import Parking from '../pages/Parking';
import ParkingDetail from '../pages/ParkingDetail';
import Reservations from '../pages/Reservations';
import CreateReservation from '../pages/CreateReservation';
import ReservationDetail from '../pages/ReservationDetail';
import Sessions from '../pages/Sessions';
import Payments from '../pages/Payments';
import Predictions from '../pages/Predictions';
import Profile from '../pages/Profile';
import Admin from '../pages/Admin';

const PublicAuthRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div
        style={{
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: 'var(--pz-bg)',
        }}
      >
        <LoadingSpinner size="lg" label="Loading..." />
      </div>
    );
  }

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  return <>{children}</>;
};

export const AppRoutes: React.FC = () => {
  return (
    <Routes>
      {/* Public Landing Route */}
      <Route path="/" element={<Home />} />

      {/* Public Authentication Routes (redirect to dashboard if already logged in) */}
      <Route
        path="/login"
        element={
          <PublicAuthRoute>
            <Login />
          </PublicAuthRoute>
        }
      />
      <Route
        path="/register"
        element={
          <PublicAuthRoute>
            <Register />
          </PublicAuthRoute>
        }
      />

      {/* Protected User Routes */}
      <Route element={<ProtectedRoute />}>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/parking" element={<Parking />} />
        <Route path="/parking/:id" element={<ParkingDetail />} />
        <Route path="/reservations" element={<Reservations />} />
        <Route path="/reservations/new" element={<CreateReservation />} />
        <Route path="/reservations/:id" element={<ReservationDetail />} />
        <Route path="/sessions" element={<Sessions />} />
        <Route path="/payments" element={<Payments />} />
        <Route path="/predictions" element={<Predictions />} />
        <Route path="/profile" element={<Profile />} />
      </Route>

      {/* Protected Admin Routes (Requires is_superuser) */}
      <Route element={<ProtectedRoute requireAdmin />}>
        <Route path="/admin/*" element={<Admin />} />
      </Route>

      {/* Fallback to Home */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};
