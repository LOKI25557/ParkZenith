import { Routes, Route } from 'react-router-dom';
import { ProtectedRoute } from './ProtectedRoute';

// Pages
import Home from '../pages/Home';
import Login from '../pages/Login';
import Register from '../pages/Register';
import Dashboard from '../pages/Dashboard';
import Parking from '../pages/Parking';
import ParkingDetail from '../pages/ParkingDetail';
import Reservations from '../pages/Reservations';
import ReservationDetail from '../pages/ReservationDetail';
import Sessions from '../pages/Sessions';
import Payments from '../pages/Payments';
import Predictions from '../pages/Predictions';
import Profile from '../pages/Profile';
import Admin from '../pages/Admin';

export const AppRoutes = () => {
  return (
    <Routes>
      {/* Public Routes */}
      <Route path="/" element={<Home />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />

      {/* Protected Routes */}
      <Route element={<ProtectedRoute />}>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/parking" element={<Parking />} />
        <Route path="/parking/:id" element={<ParkingDetail />} />
        <Route path="/reservations" element={<Reservations />} />
        <Route path="/reservations/:id" element={<ReservationDetail />} />
        <Route path="/sessions" element={<Sessions />} />
        <Route path="/payments" element={<Payments />} />
        <Route path="/predictions" element={<Predictions />} />
        <Route path="/profile" element={<Profile />} />
        
        {/* Admin routes would typically have their own role-based guard */}
        <Route path="/admin/*" element={<Admin />} />
      </Route>
    </Routes>
  );
};
