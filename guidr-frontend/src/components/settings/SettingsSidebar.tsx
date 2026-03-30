'use client';

import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { cn } from '@/lib/utils';
import {
  User,
  GraduationCap,
  Bell,
  Shield,
} from 'lucide-react';

const settingsSections = [
  {
    id: 'profile',
    label: 'Profile',
    icon: <User className="h-5 w-5" />,
  },
  {
    id: 'academic',
    label: 'Academic',
    icon: <GraduationCap className="h-5 w-5" />,
  },
  {
    id: 'application',
    label: 'Application',
    icon: <Bell className="h-5 w-5" />,
  },
  {
    id: 'privacy',
    label: 'Privacy & Security',
    icon: <Shield className="h-5 w-5" />,
  },
];

export default function SettingsSidebar() {
  const searchParams = useSearchParams();
  const activeSection = searchParams.get('section') || 'profile';

  return (
    <aside className="w-64 bg-card rounded-xl p-4 border border-border h-fit">
      <h2 className="text-lg font-semibold text-text mb-4">Settings</h2>
      <nav className="space-y-1">
        {settingsSections.map((section) => {
          const isActive = activeSection === section.id;
          return (
            <Link
              key={section.id}
              href={`/settings?section=${section.id}`}
              className={cn(
                'flex items-center gap-3 px-4 py-3 rounded-lg transition-colors',
                isActive
                  ? 'bg-primary/10 text-primary font-semibold'
                  : 'text-gray-700 hover:bg-gray-100'
              )}
            >
              {section.icon}
              <span>{section.label}</span>
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}

