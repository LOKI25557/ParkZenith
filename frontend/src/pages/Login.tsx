import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { useToast } from '../components/ui/Toast';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { FormField } from '../components/ui/FormField';
import { Input } from '../components/ui/Input';
import { Radio, Lock, Mail, Eye, EyeOff, ArrowRight } from 'lucide-react';

const Login: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { login } = useAuth();
  const { success, error: toastError } = useToast();
  const navigate = useNavigate();
  const location = useLocation();

  const from = (location.state as any)?.from?.pathname || '/dashboard';

  const extractErrorMessage = (err: any): string => {
    if (err.response?.data?.detail) {
      if (typeof err.response.data.detail === 'string') {
        return err.response.data.detail;
      }
      if (Array.isArray(err.response.data.detail) && err.response.data.detail.length > 0) {
        return err.response.data.detail[0]?.msg || 'Validation failed';
      }
    }
    if (err.message === 'Network Error' || !err.response) {
      return 'Unable to connect to the authentication server. Please check your connection.';
    }
    return 'Invalid email or password. Please try again.';
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      setError('Please provide both email and password.');
      return;
    }

    setError(null);
    setIsLoading(true);

    try {
      await login(email.trim(), password);
      success('Welcome back to ParkZenith!', 'Authenticated');
      navigate(from, { replace: true });
    } catch (err: any) {
      const msg = extractErrorMessage(err);
      setError(msg);
      toastError(msg, 'Authentication Failed');
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
        padding: '2rem',
        backgroundColor: 'var(--pz-bg)',
      }}
    >
      <div style={{ maxWidth: '440px', width: '100%' }}>
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
            Sign in to access your smart parking cockpit
          </p>
        </div>

        {/* Login Card */}
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

            <FormField label="Email Address" required>
              <Input
                type="email"
                placeholder="name@company.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                leftIcon={<Mail size={16} />}
                required
                autoComplete="email"
              />
            </FormField>

            <FormField label="Password" required>
              <Input
                type={showPassword ? 'text' : 'password'}
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                leftIcon={<Lock size={16} />}
                rightIcon={
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    style={{ color: 'var(--pz-text-muted)', display: 'flex' }}
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                }
                required
                autoComplete="current-password"
              />
            </FormField>

            <Button
              type="submit"
              variant="primary"
              size="lg"
              isLoading={isLoading}
              style={{ width: '100%', marginTop: '0.5rem' }}
              rightIcon={<ArrowRight size={16} />}
            >
              Sign In
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
            Don't have an account?{' '}
            <Link to="/register" style={{ color: 'var(--pz-secondary)', fontWeight: 600 }}>
              Create Account
            </Link>
          </div>
        </Card>
      </div>
    </div>
  );
};

export default Login;
