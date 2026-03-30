'use client';

import React, { useState } from 'react';
import Image from 'next/image';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { useProfileCompletion } from '@/contexts/ProfileCompletionContext';
import { Sidebar, SidebarBody, SidebarLink, useSidebar } from '@/components/ui/sidebar';
import {
  LayoutDashboard,
  School,
  Sparkles,
  DollarSign,
  FileText,
  PenTool,
  GraduationCap,
  LogOut,
  Menu,
  X,
  User,
  Settings,
  Lock,
  Pin,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';

interface NavLink {
  label: string;
  href: string;
  icon: React.ReactNode;
  /** Minimum profile completion level required (0 = always accessible) */
  requiredLevel?: number;
}

interface AppSidebarProps {
  open?: boolean;
  setOpen?: (open: boolean) => void;
  mobile?: boolean;
}

export default function AppSidebar({ open: openProp, setOpen: setOpenProp, mobile = false }: AppSidebarProps) {
  const { user, logout } = useAuth();
  const { completion } = useProfileCompletion();
  const router = useRouter();
  const [internalOpen, setInternalOpen] = useState(true);

  const open = openProp !== undefined ? openProp : internalOpen;
  const setOpen = setOpenProp !== undefined ? setOpenProp : setInternalOpen;

  const links: NavLink[] = [
    {
      label: 'Dashboard',
      href: '/dashboard',
      icon: <LayoutDashboard className="h-5 w-5 shrink-0 text-gray-300" />,
      requiredLevel: 0,
    },
    {
      label: 'Programs',
      href: '/schools',
      icon: <School className="h-5 w-5 shrink-0 text-gray-300" />,
      requiredLevel: 0,
    },
    {
      label: 'Institutions',
      href: '/institutions',
      icon: <svg className="h-5 w-5 shrink-0 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 21v-8.25M15.75 21v-8.25M8.25 21v-8.25M3 9l9-6 9 6m-1.5 12V10.332A48.36 48.36 0 0012 9.75c-2.551 0-5.056.2-7.5.582V21M3 21h18M12 6.75h.008v.008H12V6.75z" />
      </svg>,
      requiredLevel: 0,
    },
    {
      label: 'Recommendations',
      href: '/recommendations',
      icon: <Sparkles className="h-5 w-5 shrink-0 text-gray-300" />,
      requiredLevel: 2,
    },
    {
      label: 'Funding',
      href: '/funding',
      icon: <DollarSign className="h-5 w-5 shrink-0 text-gray-300" />,
      requiredLevel: 2,
    },
    {
      label: 'Documents',
      href: '/documents',
      icon: <FileText className="h-5 w-5 shrink-0 text-gray-300" />,
      requiredLevel: 0,
    },
    {
      label: 'Essays',
      href: '/essays',
      icon: <PenTool className="h-5 w-5 shrink-0 text-gray-300" />,
      requiredLevel: 0,
    },
    {
      label: 'Professors',
      href: '/professors',
      icon: <GraduationCap className="h-5 w-5 shrink-0 text-gray-300" />,
      requiredLevel: 2,
    },
    {
      label: 'Settings',
      href: '/settings',
      icon: <Settings className="h-5 w-5 shrink-0 text-gray-300" />,
      requiredLevel: 0,
    },
  ];

  const userLevel = completion?.level ?? 0;

  return (
    <Sidebar open={open} setOpen={setOpen} mobile={mobile}>
      <SidebarBody className="justify-between gap-10">
        <div className="flex flex-1 flex-col overflow-x-hidden overflow-y-auto">
          {/* Toggle button */}
          <HeaderSection open={open} setOpen={setOpen} />

          {/* Navigation links */}
          <div className="mt-2 flex flex-col gap-2">
            {links.map((link, idx) => {
              const locked = (link.requiredLevel ?? 0) > userLevel;
              if (locked) {
                return (
                  <LockedSidebarLink
                    key={idx}
                    link={link}
                    onLockedClick={() => router.push('/onboarding')}
                  />
                );
              }
              return <SidebarLink key={idx} link={link} />;
            })}
          </div>
        </div>

        {/* User section */}
        <div className="border-t border-gray-600 pt-4">
          {user ? (
            <>
              <SidebarLink
                link={{
                  label: user.full_name || user.email || 'User',
                  href: '/profile',
                  icon: (
                    <div className="h-7 w-7 shrink-0 rounded-full bg-primary/20 flex items-center justify-center">
                      <User className="h-4 w-4 text-primary" />
                    </div>
                  ),
                }}
              />
              {/* Profile completion indicator */}
              {completion && completion.level < 3 && (
                <SidebarCompletionIndicator open={open} completion={completion} />
              )}
              <LogoutButton open={open} logout={logout} />
            </>
          ) : null}
        </div>
      </SidebarBody>
    </Sidebar>
  );
}

/**
 * A sidebar link that appears locked — shows a lock icon and
 * redirects to onboarding on click instead of navigating.
 */
const LockedSidebarLink = ({
  link,
  onLockedClick,
}: {
  link: NavLink;
  onLockedClick: () => void;
}) => {
  const { open, isMobile } = useSidebar();

  return (
    <button
      onClick={onLockedClick}
      title="Complete your profile to unlock"
      className={cn(
        'flex items-center rounded-lg text-sm font-medium transition-colors',
        'hover:bg-sidebarHover opacity-50 cursor-not-allowed text-textSecondary',
        open || isMobile ? 'gap-3 px-3 py-2' : 'justify-center px-0 py-2',
      )}
    >
      <span
        className={cn(
          'relative flex-shrink-0 flex items-center justify-center',
          !open && !isMobile && 'w-full',
        )}
      >
        {link.icon}
        <Lock className="h-2.5 w-2.5 text-gray-400 absolute -bottom-0.5 -right-0.5" />
      </span>
      <AnimatePresence>
        {(open || isMobile) && (
          <motion.span
            initial={{ opacity: 0, width: 0 }}
            animate={{ opacity: 1, width: 'auto' }}
            exit={{ opacity: 0, width: 0 }}
            transition={{ duration: 0.2 }}
            className="whitespace-nowrap text-textSecondary flex items-center gap-1.5"
          >
            {link.label}
            <Lock className="h-3 w-3 text-gray-500" />
          </motion.span>
        )}
      </AnimatePresence>
    </button>
  );
};

const Logo = () => {
  return (
    <div className="relative z-20 flex items-center py-1">
      <Image
        src="/images/guidr-logo.png"
        alt="Guidr"
        width={175}
        height={65}
        className="h-20 w-auto object-contain"
        priority
      />
    </div>
  );
};

const LogoIcon = () => {
  return (
    <div className="relative z-20 flex items-center py-1">
      <Image
        src="/images/guidr-logo.png"
        alt="Guidr"
        width={48}
        height={48}
        className="h-10 w-auto object-contain"
        priority
      />
    </div>
  );
};

// Header section with logo and pin/unpin toggle
const HeaderSection = ({ open, setOpen }: { open: boolean; setOpen: (open: boolean) => void }) => {
  const { isHovered, isMobile, pinned, mode, pin, unpin } = useSidebar();
  const shouldShowFull = open || isHovered || isMobile;

  return (
    <div className="mb-4 flex items-center justify-between w-full">
      {shouldShowFull ? <Logo /> : <LogoIcon />}
      {isMobile ? (
        /* Mobile: always show X to close drawer */
        <button
          onClick={() => setOpen(false)}
          className="rounded-lg p-1.5 hover:bg-sidebarHover transition-colors flex-shrink-0"
          aria-label="Close menu"
        >
          <X className="h-5 w-5 text-gray-300" />
        </button>
      ) : shouldShowFull ? (
        /* Desktop: X when pinned (to collapse), Pin when collapsed (to pin) */
        <AnimatePresence mode="wait">
          {pinned && mode === 'expanded' ? (
            <motion.button
              key="unpin"
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              transition={{ duration: 0.15 }}
              onClick={unpin}
              className="rounded-lg p-1.5 hover:bg-sidebarHover transition-colors flex-shrink-0"
              aria-label="Collapse sidebar"
              title="Collapse sidebar"
            >
              <X className="h-5 w-5 text-gray-300" />
            </motion.button>
          ) : (
            <motion.button
              key="pin"
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              transition={{ duration: 0.15 }}
              onClick={pin}
              className="rounded-lg p-1.5 hover:bg-sidebarHover transition-colors flex-shrink-0"
              aria-label="Pin sidebar"
              title="Pin sidebar"
            >
              <Pin className="h-5 w-5 text-gray-300" />
            </motion.button>
          )}
        </AnimatePresence>
      ) : null}
    </div>
  );
};

// Compact profile completion indicator for sidebar
const SidebarCompletionIndicator = ({
  open,
  completion,
}: {
  open: boolean;
  completion: { percent: number; level: number };
}) => {
  const { isHovered, isMobile } = useSidebar();
  const isOpen = open || isHovered || isMobile;
  const pct = completion.percent;

  if (!isOpen) {
    // Collapsed: show a tiny ring
    return (
      <div className="flex justify-center py-1.5">
        <div className="relative h-6 w-6">
          <svg className="h-6 w-6 -rotate-90" viewBox="0 0 24 24">
            <circle cx="12" cy="12" r="10" fill="none" stroke="#374151" strokeWidth="2" />
            <circle
              cx="12"
              cy="12"
              r="10"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeDasharray={`${(pct / 100) * 62.83} 62.83`}
              className="text-primary"
            />
          </svg>
          <span className="absolute inset-0 flex items-center justify-center text-[8px] font-bold text-gray-300">
            {completion.level}
          </span>
        </div>
      </div>
    );
  }

  // Expanded: progress bar + text
  return (
    <div className="px-3 py-1.5">
      <div className="flex items-center justify-between text-[10px] text-gray-400 mb-1">
        <span>Level {completion.level}/3</span>
        <span>{pct}%</span>
      </div>
      <div className="h-1 w-full bg-gray-700 rounded-full overflow-hidden">
        <div
          className="h-full bg-primary rounded-full transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
};

// Logout button component
const LogoutButton = ({ open, logout }: { open: boolean; logout: () => void }) => {
  const { isHovered } = useSidebar();
  const isOpen = open || isHovered;

  return (
    <button
      onClick={logout}
      className={cn(
        'mt-2 flex w-full items-center rounded-lg text-sm font-medium transition-colors',
        'hover:bg-sidebarHover hover:text-primary text-gray-300',
        isOpen ? 'gap-3 px-3 py-2 justify-start' : 'justify-center px-0 py-2'
      )}
    >
      <span className={cn(
        'flex-shrink-0 flex items-center justify-center',
        !isOpen && 'w-full'
      )}>
        <LogOut className="h-5 w-5 shrink-0" />
      </span>
      {isOpen && (
        <motion.span
          initial={{ opacity: 0, width: 0 }}
          animate={{ opacity: 1, width: 'auto' }}
          exit={{ opacity: 0, width: 0 }}
          transition={{ duration: 0.2 }}
          className="whitespace-nowrap overflow-hidden"
        >
          Logout
        </motion.span>
      )}
    </button>
  );
};
