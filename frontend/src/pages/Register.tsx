import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { authApi } from '../api/auth';
import { useAuth } from '../hooks/useAuth';
import { useToast } from '../components/ui/Toast';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { FormField } from '../components/ui/FormField';
import { Input } from '../components/ui/Input';
import { Radio, Lock, Mail, User, Phone, Car, Eye, EyeOff, ArrowRight } from 'lucide-react';

const Register: React.FC = () => {
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    confirmPassword: '',
    fullName: '',
    phone: '',
    vehicleNumber: '',
  });

  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { login } = useAuth();
  const { success, error: toastError } = useToast();
  const navigate = useNavigate();

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const extractRegisterError = (err: any): string => {
    if (err.response?.status === 409) {
      return 'This email address is already registered. Please sign in or use a different email.';
    }
    if (err.response?.data?.detail) {
      if (typeof err.response.data.detail === 'string') {
        return err.response.data.detail;
      }
      if (Array.isArray(err.response.data.detail) && err.response.data.detail.length > 0) {
        const firstErr = err.response.data.detail[0];
        return firstErr?.msg ? String(firstErr.msg) : 'Please check your input details.';
      }
    }
    if (err.message === 'Network Error' || !err.response) {
      return 'Unable to connect to the registration server. Please check your network connection.';
    }
    return 'Registration failed. Please check your details and try again.';
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const trimmedEmail = formData.email.trim();
    if (!trimmedEmail || !formData.password) {
      setError('Email and password are required.');
      return;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(trimmedEmail)) {
      setError('Please provide a valid email address.');
      return;
    }

    if (formData.password.length < 8) {
      setError('Password must be at least 8 characters long.');
      return;
    }

    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    setError(null);
    setIsLoading(true);

    try {
      await authApi.register({
        email: trimmedEmail,
        password: formData.password,
        full_name: formData.fullName.trim() || undefined,
        phone: formData.phone.trim() || undefined,
        vehicle_number: formData.vehicleNumber.trim().toUpperCase() || undefined,
      });

      // Automatically sign in upon registration
      await login(trimmedEmail, formData.password);
      success('Account created successfully! Welcome to ParkZenith.', 'Registration Complete');
      navigate('/dashboard');
    } catch (err: any) {
      const msg = extractRegisterError(err);
      setError(msg);
      toastError(msg, 'Registration Error');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '2rem 1.5rem',
        backgroundColor: 'var(--pz-bg)',
      }}
    >
      <div style={{ maxWidth: '480px', width: '100%' }}>
        {/* Brand Link */}
        <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <Link to="/" style={{ display: 'inline-flex', alignItems: 'center', gap: '10px' }}>
            <div
              style={{
                width: '40px',
                height: '40px',
                borderRadius: '12px',
                background: 'linear-gradient(135deg, #1A5BFF 0%, #00E5FF 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: '0 0 20px rgba(0, 229, 255, 0.4)',
              }}
            >
              <Radio size={22} color="#090B10" />
            </div>
            <span style={{ fontSize: '1.5rem', fontWeight: 800, color: '#FFFFFF', fontFamily: 'var(--font-heading)' }}>
              Park<span className="text-gradient-cyan">Zenith</span>
            </span>
          </Link>
          <p style={{ fontSize: '0.875rem', color: 'var(--pz-text-secondary)', marginTop: '0.5rem' }}>
            Register your vehicle and experience autonomous parking
          </p>
        </div>

        {/* Register Card */}
        <Card glow="cyan" style={{ padding: '2rem' }}>
          <form onSubmit={handleSubmit}>
            {error && (
              <div
                style={{
                  padding: '10px 14px',
                  backgroundColor: 'rgba(244, 63, 94, 0.12)',
                  border: '1px solid rgba(244, 63, 94, 0.3)',
                  borderRadius: '8px',
                  color: 'var(--pz-error)',
                  fontSize: '0.8125rem',
                  marginBottom: '1.25rem',
                }}
              >
                {error}
              </div>
            )}

            <FormField label="Full Name">
              <Input
                name="fullName"
                placeholder="Alex Vance"
                value={formData.fullName}
                onChange={handleChange}
                leftIcon={<User size={16} />}
              />
            </FormField>

            <FormField label="Email Address" required>
              <Input
                name="email"
                type="email"
                placeholder="alex@company.com"
                value={formData.email}
                onChange={handleChange}
                leftIcon={<Mail size={16} />}
                required
                autoComplete="email"
              />
            </FormField>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              <FormField label="Phone">
                <Input
                  name="phone"
                  placeholder="+1 (555) 000-0000"
                  value={formData.phone}
                  onChange={handleChange}
                  leftIcon={<Phone size={16} />}
                />
              </FormField>

              <FormField label="Vehicle Plate Number">
                <Input
                  name="vehicleNumber"
                  placeholder="KA-01-MJ-5555"
                  value={formData.vehicleNumber}
                  onChange={handleChange}
                  leftIcon={<Car size={16} />}
                />
              </FormField>
            </div>

            <FormField label="Password" required hint="Minimum 8 characters">
              <Input
                name="password"
                type={showPassword ? 'text' : 'password'}
                placeholder="••••••••"
                value={formData.password}
                onChange={handleChange}
                leftIcon={<Lock size={16} />}
                rightIcon={
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    style={{ color: 'var(--pz-text-muted)', display: 'flex' }}
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                }
                required
                autoComplete="new-password"
              />
            </FormField>

            <FormField label="Confirm Password" required>
              <Input
                name="confirmPassword"
                type={showPassword ? 'text' : 'password'}
                placeholder="••••••••"
                value={formData.confirmPassword}
                onChange={handleChange}
                leftIcon={<Lock size={16} />}
                required
                autoComplete="new-password"
              />
            </FormField>

            <Button
              type="submit"
              variant="primary"
              size="lg"
              isLoading={isLoading}
              style={{ width: '100%', marginTop: '0.75rem' }}
              rightIcon={<ArrowRight size={16} />}
            >
              Create Account
            </Button>
          </form>

          <div
            style={{
              marginTop: '1.5rem',
              textAlign: 'center',
              borderTop: '1px solid var(--pz-border-subtle)',
              paddingTop: '1.25rem',
              fontSize: '0.875rem',
              color: 'var(--pz-text-secondary)',
            }}
          >
            Already have an account?{' '}
            <Link to="/login" style={{ color: 'var(--pz-secondary)', fontWeight: 600 }}>
              Sign In
            </Link>
          </div>
        </Card>
      </div>
    </div>
  );
};

export default Register;
