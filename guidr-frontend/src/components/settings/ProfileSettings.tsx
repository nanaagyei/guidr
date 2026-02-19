'use client';

import { useState, useEffect } from 'react';
import { Input } from '../ui/input';
import { DashboardCard } from '../ui/dashboard-card';
import { getProfile, putProfile } from '@/utils/api';
import { useAuth } from '@/contexts/AuthContext';
import { User } from 'lucide-react';

export default function ProfileSettings() {
  const { user, login } = useAuth();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [formData, setFormData] = useState({
    full_name: '',
    email: '',
  });

  useEffect(() => {
    const loadProfile = async () => {
      setLoading(true);
      try {
        const profile = await getProfile();
        setFormData({
          full_name: profile?.full_name || user?.full_name || '',
          email: user?.email || '',
        });
      } catch (error) {
        console.error('Failed to load profile:', error);
      } finally {
        setLoading(false);
      }
    };

    if (user) {
      loadProfile();
    }
  }, [user]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await putProfile({ full_name: formData.full_name });
      // Update auth context
      if (user) {
        login({ ...user, full_name: formData.full_name });
      }
      alert('Profile updated successfully!');
    } catch (error) {
      console.error('Failed to update profile:', error);
      alert('Failed to update profile. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="h-6 w-6 border-2 border-primary border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <DashboardCard>
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 bg-primary/10 rounded-lg">
          <User className="h-5 w-5 text-primary" />
        </div>
        <div>
          <h2 className="text-xl font-semibold text-text">Profile Settings</h2>
          <p className="text-sm text-gray-600">Manage your personal information</p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <Input
          label="Full Name"
          value={formData.full_name}
          onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
          placeholder="Enter your full name"
        />

        <Input
          label="Email"
          value={formData.email}
          disabled
          helperText="Email cannot be changed. Contact support if you need to update your email."
        />

        <div className="flex justify-end gap-3 pt-4 border-t border-border">
          <button
            type="button"
            onClick={() => window.location.reload()}
            className="px-6 py-2 bg-gray-100 text-gray-700 font-semibold rounded-lg hover:bg-gray-200 transition"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={saving}
            className="px-6 py-2 bg-primary text-white font-semibold rounded-lg hover:bg-primaryHover transition disabled:opacity-50"
          >
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </form>
    </DashboardCard>
  );
}

