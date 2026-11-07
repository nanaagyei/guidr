'use client';

import { useState } from 'react';
import { createPortal } from 'react-dom';
import { useRouter } from 'next/navigation';
import { DashboardCard } from '../ui/dashboard-card';
import { Shield, Key, Download, Trash2, Lock } from 'lucide-react';
import { Input } from '../ui/input';
import { useToast } from '@/contexts/ToastContext';
import { useAuth } from '@/contexts/AuthContext';
import { changePassword, deleteAccount, exportAccountData } from '@/utils/api';

const EMPTY_PASSWORD_FORM = {
  currentPassword: '',
  newPassword: '',
  confirmPassword: '',
};

export default function PrivacySettings() {
  const router = useRouter();
  const { addToast } = useToast();
  const { logout } = useAuth();

  const [passwordForm, setPasswordForm] = useState(EMPTY_PASSWORD_FORM);
  const [changingPassword, setChangingPassword] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [deletePassword, setDeletePassword] = useState('');
  const [deleteConfirmation, setDeleteConfirmation] = useState('');
  const [deleting, setDeleting] = useState(false);

  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault();
    if (passwordForm.newPassword !== passwordForm.confirmPassword) {
      addToast('The new passwords do not match', 'error');
      return;
    }
    setChangingPassword(true);
    try {
      await changePassword(passwordForm.currentPassword, passwordForm.newPassword);
      setPasswordForm(EMPTY_PASSWORD_FORM);
      addToast('Password changed successfully', 'success');
    } catch (err: any) {
      addToast(err.message || 'Failed to change password', 'error');
    } finally {
      setChangingPassword(false);
    }
  };

  const handleExport = async () => {
    setExporting(true);
    try {
      const blob = await exportAccountData();
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `guidr-export-${new Date().toISOString().slice(0, 10).replace(/-/g, '')}.json`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (err: any) {
      addToast(err.message || 'Failed to export your data', 'error');
    } finally {
      setExporting(false);
    }
  };

  const closeDeleteDialog = () => {
    setShowDeleteDialog(false);
    setDeletePassword('');
    setDeleteConfirmation('');
  };

  const handleDelete = async (e: React.FormEvent) => {
    e.preventDefault();
    if (deleteConfirmation !== 'DELETE' || !deletePassword) return;
    setDeleting(true);
    try {
      await deleteAccount(deletePassword);
      await logout();
      router.push('/');
    } catch (err: any) {
      addToast(err.message || 'Failed to delete account', 'error');
      setDeleting(false);
    }
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
              autoComplete="current-password"
              required
              value={passwordForm.currentPassword}
              onChange={(e) => setPasswordForm({ ...passwordForm, currentPassword: e.target.value })}
            />
            <Input
              label="New Password"
              type="password"
              autoComplete="new-password"
              required
              value={passwordForm.newPassword}
              onChange={(e) => setPasswordForm({ ...passwordForm, newPassword: e.target.value })}
            />
            <Input
              label="Confirm New Password"
              type="password"
              autoComplete="new-password"
              required
              value={passwordForm.confirmPassword}
              onChange={(e) => setPasswordForm({ ...passwordForm, confirmPassword: e.target.value })}
            />
            <button
              type="submit"
              disabled={changingPassword}
              className="px-6 py-2 bg-primary text-white font-semibold rounded-lg hover:bg-primaryHover transition disabled:opacity-50"
            >
              {changingPassword ? 'Updating...' : 'Update Password'}
            </button>
          </form>
        </div>

        {/* Verification codes */}
        <div className="pt-6 border-t border-border">
          <div className="flex items-center gap-2 mb-4">
            <Lock className="h-5 w-5 text-primary" />
            <h3 className="font-semibold text-text">Verification Codes</h3>
          </div>
          <div className="p-4 bg-gray-50 rounded-lg border border-border">
            <p className="text-sm text-gray-700">
              A verification code is emailed when you register or reset your password. Signing in
              does not use a second factor.
            </p>
          </div>
        </div>

        {/* Data Management */}
        <div className="pt-6 border-t border-border">
          <h3 className="font-semibold text-text mb-4">Data Management</h3>
          <div className="space-y-3">
            <button
              type="button"
              onClick={handleExport}
              disabled={exporting}
              className="w-full flex items-center justify-between p-4 border border-border rounded-lg hover:border-primary/30 transition-colors text-left group disabled:opacity-50"
            >
              <div className="flex items-center gap-3">
                <Download className="h-5 w-5 text-primary" />
                <div>
                  <p className="font-medium text-text">{exporting ? 'Preparing export...' : 'Export Data'}</p>
                  <p className="text-xs text-gray-600">Download all your data as a JSON file</p>
                </div>
              </div>
            </button>
            <button
              type="button"
              onClick={() => setShowDeleteDialog(true)}
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

      {/* Portal: DashboardCard's transform would otherwise trap the fixed overlay */}
      {showDeleteDialog && createPortal(
        <div
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
          role="dialog"
          aria-modal="true"
          aria-labelledby="delete-account-title"
        >
          <form onSubmit={handleDelete} className="bg-white rounded-xl p-6 max-w-md w-full mx-4 space-y-4">
            <h2 id="delete-account-title" className="text-2xl font-semibold text-red-700">
              Delete your account?
            </h2>
            <p className="text-sm text-gray-700">
              This permanently deletes your profile, academic records, essays, recommendations,
              outreach drafts and any uploaded files. It cannot be undone. Export your data first if
              you want a copy.
            </p>
            <Input
              label="Password"
              type="password"
              autoComplete="current-password"
              required
              value={deletePassword}
              onChange={(e) => setDeletePassword(e.target.value)}
            />
            <Input
              label='Type "DELETE" to confirm'
              type="text"
              autoComplete="off"
              required
              value={deleteConfirmation}
              onChange={(e) => setDeleteConfirmation(e.target.value)}
            />
            <div className="flex justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={closeDeleteDialog}
                disabled={deleting}
                className="px-6 py-2 bg-gray-200 text-gray-700 font-medium rounded-lg hover:bg-gray-300 transition disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={deleting || deleteConfirmation !== 'DELETE' || !deletePassword}
                className="px-6 py-2 bg-red-600 text-white font-semibold rounded-lg hover:bg-red-700 transition disabled:opacity-50"
              >
                {deleting ? 'Deleting...' : 'Delete account'}
              </button>
            </div>
          </form>
        </div>,
        document.body,
      )}
    </DashboardCard>
  );
}
