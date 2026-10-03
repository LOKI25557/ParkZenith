import React, { useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import { useToast } from '../components/ui/Toast';
import { Card } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { FormField } from '../components/ui/FormField';
import { Input } from '../components/ui/Input';
import { Breadcrumb } from '../components/ui/Breadcrumb';
import { Avatar } from '../components/ui/Avatar';
import { User, Mail, Phone, Car, ShieldCheck, Zap, LogOut, CheckCircle2 } from 'lucide-react';

const Profile: React.FC = () => {
  const { user, logout } = useAuth();
  const { success } = useToast();

  const [fullName, setFullName] = useState(user?.full_name || '');
  const [phone, setPhone] = useState(user?.phone || '+1 (555) 234-5678');
  const [vehicleNumber, setVehicleNumber] = useState(user?.vehicle_number || 'KA-01-MJ-5555');
  const [isSaving, setIsSaving] = useState(false);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    setTimeout(() => {
      setIsSaving(false);
      success('Profile preferences updated.', 'Saved');
    }, 600);
  };

  const isAdmin = Boolean(user?.is_superuser || user?.role === 'admin');

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem', maxWidth: '880px', margin: '0 auto' }}>
      <div>
        <Breadcrumb items={[{ label: 'User Profile' }]} />
        <h1 className="text-page-title" style={{ marginTop: '0.75rem' }}>Profile &amp; Vehicle Settings</h1>
        <p className="text-body" style={{ marginTop: '4px' }}>
          Manage your driver credentials, registered vehicles, and telemetry preferences.
        </p>
      </div>

      {/* Driver Identity Card */}
      <Card glow="cyan" style={{ padding: '2rem' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '1.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem' }}>
            <Avatar name={user?.full_name || user?.email || 'User'} size="xl" status="online" />
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <h2 style={{ fontSize: '1.5rem', fontWeight: 700, color: '#FFFFFF' }}>
                  {user?.full_name || 'Driver'}
                </h2>
                {isAdmin ? (
                  <span
                    style={{
                      fontSize: '0.6875rem',
                      fontWeight: 700,
                      padding: '2px 8px',
                      borderRadius: '9999px',
                      backgroundColor: 'rgba(139, 92, 246, 0.25)',
                      color: '#C084FC',
                      border: '1px solid rgba(139, 92, 246, 0.5)',
                    }}
                  >
                    System Administrator
                  </span>
                ) : (
                  <span
                    style={{
                      fontSize: '0.6875rem',
                      fontWeight: 600,
                      padding: '2px 8px',
                      borderRadius: '9999px',
                      backgroundColor: 'rgba(0, 229, 255, 0.15)',
                      color: 'var(--pz-secondary)',
                      border: '1px solid rgba(0, 229, 255, 0.3)',
                    }}
                  >
                    Fleet Member
                  </span>
                )}
              </div>
              <p style={{ fontSize: '0.875rem', color: 'var(--pz-text-secondary)', marginTop: '2px' }}>
                {user?.email}
              </p>
            </div>
          </div>

          <Button variant="ghost" size="sm" leftIcon={<LogOut size={16} />} onClick={logout} style={{ color: 'var(--pz-error)' }}>
            Sign Out
          </Button>
        </div>
      </Card>

      {/* Vehicle Fast-Pass Card */}
      <Card>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '1.25rem' }}>
          <Car size={20} color="var(--pz-secondary)" />
          <h3 style={{ fontSize: '1.1875rem', fontWeight: 600, color: '#FFFFFF' }}>
            Registered Vehicle &amp; ALPR Fast-Pass
          </h3>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
          <div style={{ padding: '12px', backgroundColor: 'rgba(255, 255, 255, 0.03)', borderRadius: '12px', border: '1px solid var(--pz-border-subtle)' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-muted)', display: 'block' }}>Primary License Plate</span>
            <span style={{ fontSize: '1.375rem', fontWeight: 800, color: '#FFFFFF', fontFamily: 'var(--font-mono)', marginTop: '2px', display: 'block' }}>
              {vehicleNumber}
            </span>
          </div>

          <div style={{ padding: '12px', backgroundColor: 'rgba(255, 255, 255, 0.03)', borderRadius: '12px', border: '1px solid var(--pz-border-subtle)' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-muted)', display: 'block' }}>ALPR Gate Status</span>
            <span style={{ fontSize: '0.875rem', color: 'var(--pz-success)', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '4px', marginTop: '6px' }}>
              <ShieldCheck size={16} /> Sub-300ms Barrier Sync Active
            </span>
          </div>

          <div style={{ padding: '12px', backgroundColor: 'rgba(255, 255, 255, 0.03)', borderRadius: '12px', border: '1px solid var(--pz-border-subtle)' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--pz-text-muted)', display: 'block' }}>Charging Profile</span>
            <span style={{ fontSize: '0.875rem', color: 'var(--pz-secondary)', fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: '4px', marginTop: '6px' }}>
              <Zap size={16} /> CCS2 / 350kW Fast-Charge Enabled
            </span>
          </div>
        </div>
      </Card>

      {/* Account Settings Form */}
      <Card>
        <h3 style={{ fontSize: '1.1875rem', fontWeight: 600, color: '#FFFFFF', marginBottom: '1.5rem' }}>
          Contact &amp; Account Details
        </h3>

        <form onSubmit={handleSave} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <FormField label="Full Name">
              <Input
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                leftIcon={<User size={16} />}
              />
            </FormField>

            <FormField label="Email Address">
              <Input
                value={user?.email || ''}
                disabled
                leftIcon={<Mail size={16} />}
              />
            </FormField>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
            <FormField label="Phone Number">
              <Input
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                leftIcon={<Phone size={16} />}
              />
            </FormField>

            <FormField label="Vehicle License Plate">
              <Input
                value={vehicleNumber}
                onChange={(e) => setVehicleNumber(e.target.value)}
                leftIcon={<Car size={16} />}
              />
            </FormField>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '1rem' }}>
            <Button variant="primary" type="submit" isLoading={isSaving} leftIcon={<CheckCircle2 size={16} />}>
              Save Preferences
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
};

export default Profile;
