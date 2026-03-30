'use client';

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

const STORAGE_KEY = 'guidr:sidebar:state';

type SidebarMode = 'expanded' | 'collapsed';

interface SidebarPersistedState {
  mode: SidebarMode;
  pinned: boolean;
}

interface SidebarContextType {
  /** Whether the sidebar is visually open (expanded, pinned, or hovered). */
  open: boolean;
  setOpen: ((open: boolean) => void) | undefined;
  isHovered: boolean;
  isMobile: boolean;
  mode: SidebarMode;
  pinned: boolean;
  /** Pin the sidebar in expanded state. */
  pin: () => void;
  /** Unpin and collapse the sidebar. */
  unpin: () => void;
}

const SidebarContext = createContext<SidebarContextType | undefined>(undefined);

export const useSidebar = () => {
  const context = useContext(SidebarContext);
  if (!context) {
    throw new Error('useSidebar must be used within a Sidebar component');
  }
  return context;
};

function readPersistedState(): SidebarPersistedState {
  if (typeof window === 'undefined') return { mode: 'expanded', pinned: true };
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (parsed && typeof parsed.mode === 'string') return parsed;
    }
  } catch { /* ignore */ }
  return { mode: 'expanded', pinned: true };
}

function persistState(state: SidebarPersistedState) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch { /* ignore */ }
}

interface SidebarProps {
  children: React.ReactNode;
  open?: boolean;
  setOpen?: (open: boolean) => void;
  mobile?: boolean;
}

export const Sidebar = ({ children, open: openProp, setOpen: setOpenProp, mobile = false }: SidebarProps) => {
  const [persisted, setPersisted] = useState<SidebarPersistedState>({ mode: 'expanded', pinned: true });
  const [hoverOpen, setHoverOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [hydrated, setHydrated] = useState(false);

  // Hydrate from localStorage on mount
  useEffect(() => {
    setPersisted(readPersistedState());
    setHydrated(true);
  }, []);

  // For mobile, openProp controls visibility
  const mobileOpen = openProp ?? false;
  const setMobileOpen = setOpenProp;

  // Desktop: open if pinned+expanded, or hovered while collapsed
  const desktopOpen = persisted.mode === 'expanded' || (persisted.mode === 'collapsed' && hoverOpen);

  // Unified isOpen
  const isOpen = mobile ? mobileOpen : desktopOpen;

  // Backward-compat setOpen for external callers (mobile)
  const setOpen = useCallback(
    (val: boolean) => {
      if (mobile && setMobileOpen) {
        setMobileOpen(val);
      } else {
        // Desktop: toggling open/close maps to pin/unpin
        const newState: SidebarPersistedState = val
          ? { mode: 'expanded', pinned: true }
          : { mode: 'collapsed', pinned: false };
        setPersisted(newState);
        persistState(newState);
      }
    },
    [mobile, setMobileOpen],
  );

  const pin = useCallback(() => {
    const newState: SidebarPersistedState = { mode: 'expanded', pinned: true };
    setPersisted(newState);
    persistState(newState);
  }, []);

  const unpin = useCallback(() => {
    const newState: SidebarPersistedState = { mode: 'collapsed', pinned: false };
    setPersisted(newState);
    persistState(newState);
    setHoverOpen(false);
  }, []);

  // Responsive check
  useEffect(() => {
    const checkMobile = () => setIsMobile(window.innerWidth < 1024);
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  // Close sidebar on mobile when clicking outside
  useEffect(() => {
    if (isMobile && mobileOpen) {
      const handleClickOutside = (e: MouseEvent) => {
        const target = e.target as HTMLElement;
        if (!target.closest('[data-sidebar]') && !target.closest('[data-hamburger]')) {
          setOpen(false);
        }
      };
      document.addEventListener('click', handleClickOutside);
      return () => document.removeEventListener('click', handleClickOutside);
    }
  }, [isMobile, mobileOpen, setOpen]);

  // Prevent body scroll when mobile sidebar is open
  useEffect(() => {
    if (isMobile && mobileOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => { document.body.style.overflow = ''; };
  }, [isMobile, mobileOpen]);

  const ctx: SidebarContextType = {
    open: isOpen,
    setOpen,
    isHovered: hoverOpen,
    isMobile: mobile ? true : isMobile,
    mode: persisted.mode,
    pinned: persisted.pinned,
    pin,
    unpin,
  };

  // Mobile: Overlay drawer
  if (mobile) {
    return (
      <SidebarContext.Provider value={ctx}>
        <AnimatePresence mode="wait">
          {mobileOpen && (
            <>
              <motion.div
                key="backdrop"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="fixed inset-0 bg-black/50 z-40"
                onClick={() => setOpen(false)}
              />
              <motion.aside
                key="sidebar"
                data-sidebar
                initial={{ x: '-100%' }}
                animate={{ x: 0 }}
                exit={{ x: '-100%' }}
                transition={{ type: 'spring', damping: 25, stiffness: 200 }}
                className={cn(
                  'fixed left-0 top-0 h-screen w-64 flex-col border-r border-border bg-sidebar text-text z-50',
                  'flex shadow-xl',
                )}
              >
                {children}
              </motion.aside>
            </>
          )}
        </AnimatePresence>
      </SidebarContext.Provider>
    );
  }

  // Desktop: Fixed sidebar
  return (
    <SidebarContext.Provider value={ctx}>
      <aside
        onMouseEnter={() => {
          if (persisted.mode === 'collapsed') setHoverOpen(true);
        }}
        onMouseLeave={() => {
          setHoverOpen(false);
        }}
        className={cn(
          'group/sidebar relative flex h-screen flex-col border-r border-border bg-sidebar text-text transition-all duration-300 z-50',
          'hidden lg:flex',
          isOpen ? 'w-64' : 'w-16',
        )}
      >
        {children}
      </aside>
    </SidebarContext.Provider>
  );
};

interface SidebarBodyProps {
  children: React.ReactNode;
  className?: string;
}

export const SidebarBody = ({ children, className }: SidebarBodyProps) => {
  return (
    <div className={cn('flex h-full flex-col p-4', className)}>
      {children}
    </div>
  );
};

interface SidebarLinkProps {
  link: {
    label: string;
    href: string;
    icon: React.ReactNode;
  };
  className?: string;
}

export const SidebarLink = ({ link, className }: SidebarLinkProps) => {
  const { open, setOpen, isMobile } = useSidebar();
  const pathname = usePathname();
  const isActive = pathname === link.href;

  const handleClick = () => {
    if (isMobile && setOpen) {
      setOpen(false);
    }
  };

  return (
    <Link
      href={link.href}
      onClick={handleClick}
      className={cn(
        'flex items-center rounded-lg text-sm font-medium transition-colors',
        'hover:bg-sidebarHover',
        isActive && 'bg-primary/10',
        !isActive && 'text-textSecondary',
        open ? 'gap-3 px-3 py-2' : 'justify-center px-0 py-2',
        isMobile && 'gap-3 px-3 py-2',
        className
      )}
    >
      <span className={cn(
        'flex-shrink-0 flex items-center justify-center',
        isActive && '[&>svg]:text-primary [&>div]:bg-primary/15',
        !isActive && '[&>svg]:text-textSecondary',
        !open && !isMobile && 'w-full'
      )}>
        {link.icon}
      </span>
      <AnimatePresence>
        {(open || isMobile) && (
          <motion.span
            initial={{ opacity: 0, width: 0 }}
            animate={{ opacity: 1, width: 'auto' }}
            exit={{ opacity: 0, width: 0 }}
            transition={{ duration: 0.2 }}
            className={cn(
              'whitespace-nowrap',
              isActive && 'text-primary',
              !isActive && 'text-textSecondary'
            )}
          >
            {link.label}
          </motion.span>
        )}
      </AnimatePresence>
    </Link>
  );
};
