'use client';

import { useState } from 'react';
import { DashboardCard } from '../ui/dashboard-card';
import { Bell, Mail } from 'lucide-react';
import { RadioGroup } from '../ui/radio-group';

export default function ApplicationSettings() {
  const [emailNotifications, setEmailNotifications] = useState('all');
  const [deadlineReminders, setDeadlineReminders] = useState('7days');

  return (
    <DashboardCard>
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 bg-primary/10 rounded-lg">
          <Bell className="h-5 w-5 text-primary" />
        </div>
        <div>
          <h2 className="text-xl font-semibold text-text">Application Settings</h2>
          <p className="text-sm text-gray-600">Manage notifications and reminders</p>
        </div>
      </div>

      <div className="space-y-8">
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

        <div className="pt-4 border-t border-border">
          <button
            className="px-6 py-2 bg-primary text-white font-semibold rounded-lg hover:bg-primaryHover transition"
          >
            Save Preferences
          </button>
        </div>
      </div>
    </DashboardCard>
  );
}

