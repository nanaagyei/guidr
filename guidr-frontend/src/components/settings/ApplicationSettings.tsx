'use client';

import { useState, useEffect } from 'react';
import { DashboardCard } from '../ui/dashboard-card';
import { Bell, Mail, BookOpen, Target } from 'lucide-react';
import { RadioGroup } from '../ui/radio-group';
import { TagInput } from '../ui/tag-input';
import { getProfile, putProfile } from '@/utils/api';

export default function ApplicationSettings() {
  const [emailNotifications, setEmailNotifications] = useState('all');
  const [deadlineReminders, setDeadlineReminders] = useState('7days');
  const [researchAreas, setResearchAreas] = useState<string[]>([]);
  const [careerGoals, setCareerGoals] = useState('');
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  useEffect(() => {
    getProfile()
      .then((profile) => {
        if (profile?.research_areas) setResearchAreas(profile.research_areas);
        if (profile?.career_goals) setCareerGoals(profile.career_goals);
      })
      .catch(() => {});
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setSaveError(null);
    setSaveSuccess(false);
    try {
      await putProfile({ research_areas: researchAreas, career_goals: careerGoals });
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err: any) {
      setSaveError(err.message || 'Failed to save preferences');
    } finally {
      setSaving(false);
    }
  };

  return (
    <DashboardCard>
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 bg-primary/10 rounded-lg">
          <Bell className="h-5 w-5 text-primary" />
        </div>
        <div>
          <h2 className="text-xl font-semibold text-text">Application Settings</h2>
          <p className="text-sm text-gray-600">Manage notifications, reminders, and research interests</p>
        </div>
      </div>

      <div className="space-y-8">
        {/* Research Interests */}
        <div>
          <div className="flex items-center gap-2 mb-4">
            <BookOpen className="h-5 w-5 text-primary" />
            <h3 className="font-semibold text-text">Research Interests</h3>
          </div>
          <TagInput
            label="Research Areas"
            placeholder="e.g., Machine Learning, NLP — press comma or Enter"
            value={researchAreas}
            onChange={setResearchAreas}
            helperText="Press comma or Enter after each research area"
            maxTags={15}
          />
        </div>

        {/* Career Goals */}
        <div>
          <div className="flex items-center gap-2 mb-4">
            <Target className="h-5 w-5 text-primary" />
            <h3 className="font-semibold text-text">Career Goals</h3>
          </div>
          <div>
            <label className="block text-sm font-medium text-text mb-1.5">
              Describe your career aspirations
            </label>
            <textarea
              className="w-full px-4 py-2.5 rounded-lg border border-border focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
              rows={4}
              placeholder="Tell us about your career goals and aspirations..."
              value={careerGoals}
              onChange={(e) => setCareerGoals(e.target.value)}
            />
          </div>
        </div>

        {/* Email Notifications */}
        <div>
          <div className="flex items-center gap-2 mb-4">
            <Mail className="h-5 w-5 text-primary" />
            <h3 className="font-semibold text-text">Email Notifications</h3>
          </div>
          <RadioGroup
            name="email_notifications"
            value={emailNotifications}
            onChange={setEmailNotifications}
            options={[
              { value: 'all', label: 'All Notifications', description: 'Receive all email notifications' },
              { value: 'important', label: 'Important Only', description: 'Only critical updates and deadlines' },
              { value: 'none', label: 'No Emails', description: 'Disable all email notifications' },
            ]}
          />
        </div>

        {/* Deadline Reminders */}
        <div>
          <div className="flex items-center gap-2 mb-4">
            <Bell className="h-5 w-5 text-primary" />
            <h3 className="font-semibold text-text">Deadline Reminders</h3>
          </div>
          <RadioGroup
            name="deadline_reminders"
            value={deadlineReminders}
            onChange={setDeadlineReminders}
            options={[
              { value: '14days', label: '14 Days Before', description: 'Get reminders 14 days before deadlines' },
              { value: '7days', label: '7 Days Before', description: 'Get reminders 7 days before deadlines' },
              { value: '3days', label: '3 Days Before', description: 'Get reminders 3 days before deadlines' },
              { value: 'none', label: 'No Reminders', description: 'Disable deadline reminders' },
            ]}
          />
        </div>

        {saveError && (
          <p className="text-sm text-red-600">{saveError}</p>
        )}
        {saveSuccess && (
          <p className="text-sm text-green-600">Preferences saved successfully.</p>
        )}

        <div className="pt-4 border-t border-border">
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-6 py-2 bg-primary text-white font-semibold rounded-lg hover:bg-primaryHover transition disabled:opacity-50"
          >
            {saving ? 'Saving...' : 'Save Preferences'}
          </button>
        </div>
      </div>
    </DashboardCard>
  );
}
