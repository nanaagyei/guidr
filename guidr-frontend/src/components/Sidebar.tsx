'use client';

import React, { useState } from 'react';
import Image from 'next/image';
import { useAuth } from '@/contexts/AuthContext';
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
} from 'lucide-react';
import { motion } from 'framer-motion';
import { cn } from '@/lib/utils';

interface AppSidebarProps {
  open?: boolean;
  setOpen?: (open: boolean) => void;
  mobile?: boolean;
}

export default function AppSidebar({ open: openProp, setOpen: setOpenProp, mobile = false }: AppSidebarProps) {
  const { user, logout } = useAuth();
  const [internalOpen, setInternalOpen] = useState(true);
  
  // Use props if provided (for mobile), otherwise use internal state (for desktop)
  const open = openProp !== undefined ? openProp : internalOpen;
  const setOpen = setOpenProp !== undefined ? setOpenProp : setInternalOpen;

  const links = [
    {
      label: 'Dashboard',
      href: '/dashboard',
      icon: <LayoutDashboard className="h-5 w-5 shrink-0 text-gray-300" />,
    },
    {
      label: 'Programs',
      href: '/schools',
      icon: <School className="h-5 w-5 shrink-0 text-gray-300" />,
    },
    {
      label: 'Institutions',
      href: '/institutions',
      icon: <svg className="h-5 w-5 shrink-0 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 21v-8.25M15.75 21v-8.25M8.25 21v-8.25M3 9l9-6 9 6m-1.5 12V10.332A48.36 48.36 0 0012 9.75c-2.551 0-5.056.2-7.5.582V21M3 21h18M12 6.75h.008v.008H12V6.75z" />
      </svg>,
    },
    {
      label: 'Recommendations',
      href: '/recommendations',
      icon: <Sparkles className="h-5 w-5 shrink-0 text-gray-300" />,
    },
    {
      label: 'Funding',
      href: '/funding',
      icon: <DollarSign className="h-5 w-5 shrink-0 text-gray-300" />,
    },
    {
      label: 'Documents',
      href: '/documents',
      icon: <FileText className="h-5 w-5 shrink-0 text-gray-300" />,
    },
    {
      label: 'Essays',
      href: '/essays',
      icon: <PenTool className="h-5 w-5 shrink-0 text-gray-300" />,
    },
    {
      label: 'Professors',
      href: '/professors',
      icon: <GraduationCap className="h-5 w-5 shrink-0 text-gray-300" />,
    },
    {
      label: 'Settings',
      href: '/settings',
      icon: <Settings className="h-5 w-5 shrink-0 text-gray-300" />,
    },
  ];

  return (
    <Sidebar open={open} setOpen={setOpen} mobile={mobile}>
      <SidebarBody className="justify-between gap-10">
        <div className="flex flex-1 flex-col overflow-x-hidden overflow-y-auto">
          {/* Toggle button */}
          <HeaderSection open={open} setOpen={setOpen} />

          {/* Navigation links */}
          <div className="mt-2 flex flex-col gap-2">
            {links.map((link, idx) => (
              <SidebarLink key={idx} link={link} />
            ))}
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
              <LogoutButton open={open} logout={logout} />
            </>
          ) : null}
        </div>
      </SidebarBody>
    </Sidebar>
  );
}

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

// Header section with logo and hamburger
const HeaderSection = ({ open, setOpen }: { open: boolean; setOpen: (open: boolean) => void }) => {
  const { isHovered, isMobile } = useSidebar();
  const shouldShowHamburger = open || isHovered || isMobile;

  return (
    <div className="mb-4 flex items-center justify-between w-full">
      {shouldShowHamburger ? <Logo /> : <LogoIcon />}
      {isMobile ? (
        <button
          onClick={() => setOpen(false)}
          className="rounded-lg p-1.5 hover:bg-sidebarHover transition-colors flex-shrink-0"
          aria-label="Close menu"
        >
          <X className="h-5 w-5 text-gray-300" />
        </button>
      ) : shouldShowHamburger ? (
        <button
          onClick={() => setOpen(!open)}
          className="rounded-lg p-1.5 hover:bg-sidebarHover transition-colors flex-shrink-0"
        >
          <X className="h-5 w-5 text-gray-300" />
        </button>
      ) : null}
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
        // Always align left when open (expanded or hovered)
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

