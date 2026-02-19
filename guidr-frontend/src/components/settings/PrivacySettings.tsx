'use client';

import { useState } from 'react';
import { DashboardCard } from '../ui/dashboard-card';
import { Shield, Key, Download, Trash2, Lock } from 'lucide-react';
import { Input } from '../ui/input';

export default function PrivacySettings() {
  const [passwordForm, setPasswordForm] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: '',
  });

  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault();
    // TODO: Implement password change API call
    alert('Password change functionality will be implemented with backend support');
  };

  return (
    <DashboardCard>
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 bg-primary/10 rounded-lg">
          <Shield className="h-5 w-5 text-primary" />
        </div>
        <div>
          <h2 className="text-xl font-semibold text-text">Privacy & Security</h2>
          <p className="text-sm text-gray-600">Manage your account security and privacy</p>
        </div>
      </div>

      <div className="space-y-8">
        {/* Password Change */}
        <div>
          <div className="flex items-center gap-2 mb-4">
            <Key className="h-5 w-5 text-primary" />
            <h3 className="font-semibold text-text">Change Password</h3>
          </div>
          <form onSubmit={handlePasswordChange} className="space-y-4">
            <Input
              label="Current Password"
              type="password"
              value={passwordForm.currentPassword}
              onChange={(e) => setPasswordForm({ ...passwordForm, currentPassword: e.target.value })}
            />
            <Input
              label="New Password"
              type="password"
              value={passwordForm.newPassword}
              onChange={(e) => setPasswordForm({ ...passwordForm, newPassword: e.target.value })}
            />
            <Input
              label="Confirm New Password"
              type="password"
              value={passwordForm.confirmPassword}
              onChange={(e) => setPasswordForm({ ...passwordForm, confirmPassword: e.target.value })}
            />
            <button
              type="submit"
              className="px-6 py-2 bg-primary text-white font-semibold rounded-lg hover:bg-primaryHover transition"
            >
              Update Password
            </button>
          </form>
        </div>

        {/* Two-Factor Authentication */}
        <div className="pt-6 border-t border-border">
          <div className="flex items-center gap-2 mb-4">
            <Lock className="h-5 w-5 text-primary" />
            <h3 className="font-semibold text-text">Two-Factor Authentication</h3>
          </div>
          <div className="p-4 bg-gray-50 rounded-lg border border-border">
            <p className="text-sm text-gray-700 mb-3">
              2FA is currently enabled for your account. You{"\u2019"}ll receive a verification code when logging in.
            </p>
            <button
              className="text-sm text-primary hover:text-primaryHover font-medium"
            >
              Manage 2FA Settings
            </button>
          </div>
        </div>

        {/* Data Management */}
        <div className="pt-6 border-t border-border">
          <h3 className="font-semibold text-text mb-4">Data Management</h3>
          <div className="space-y-3">
            <button
              className="w-full flex items-center justify-between p-4 border border-border rounded-lg hover:border-primary/30 transition-colors text-left group"
            >
              <div className="flex items-center gap-3">
                <Download className="h-5 w-5 text-primary" />
                <div>
                  <p className="font-medium text-text">Export Data</p>
                  <p className="text-xs text-gray-600">Download all your data as a ZIP file</p>
                </div>
              </div>
            </button>
            <button
              className="w-full flex items-center justify-between p-4 border border-red-300 rounded-lg hover:border-red-400 hover:bg-red-50 transition-colors text-left group"
            >
              <div className="flex items-center gap-3">
                <Trash2 className="h-5 w-5 text-red-600" />
                <div>
                  <p className="font-medium text-red-700">Delete Account</p>
                  <p className="text-xs text-red-600">Permanently delete your account and all data</p>
                </div>
              </div>
            </button>
          </div>
        </div>
      </div>
    </DashboardCard>
  );
}

