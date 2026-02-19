'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

interface SidebarContextType {
  open: boolean;
  setOpen: ((open: boolean) => void) | undefined;
  isHovered: boolean;
  isMobile: boolean;
}

const SidebarContext = createContext<SidebarContextType | undefined>(undefined);

export const useSidebar = () => {
  const context = useContext(SidebarContext);
  if (!context) {
    throw new Error('useSidebar must be used within a Sidebar component');
  }
  return context;
};

interface SidebarProps {
  children: React.ReactNode;
  open?: boolean;
  setOpen?: (open: boolean) => void;
  mobile?: boolean;
}

export const Sidebar = ({ children, open: openProp, setOpen: setOpenProp, mobile = false }: SidebarProps) => {
  const [internalOpen, setInternalOpen] = useState(false);
  const [hoverOpen, setHoverOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  
  const open = openProp !== undefined ? openProp : internalOpen;
  const setOpen = setOpenProp !== undefined ? setOpenProp : setInternalOpen;
  
  // Sidebar is open if manually opened OR hovered (when manually closed on desktop)
  const isOpen = open || (hoverOpen && !isMobile);

  // Check if mobile on mount and window resize
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 1024); // Less than iPad size
    };
    
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  // Close sidebar on mobile when clicking outside
  useEffect(() => {
    if (isMobile && open) {
      const handleClickOutside = (e: MouseEvent) => {
        const target = e.target as HTMLElement;
        if (!target.closest('[data-sidebar]') && !target.closest('[data-hamburger]')) {
          setOpen(false);
        }
      };
      
      document.addEventListener('click', handleClickOutside);
      return () => document.removeEventListener('click', handleClickOutside);
    }
  }, [isMobile, open, setOpen]);

  // Prevent body scroll when mobile sidebar is open
  useEffect(() => {
    if (isMobile && open) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isMobile, open]);

  // If explicitly set as mobile, render as overlay drawer
  if (mobile) {
    // Mobile: Overlay drawer that slides in from left
    return (
      <SidebarContext.Provider value={{ open: isOpen, setOpen, isHovered: false, isMobile: true }}>
        <AnimatePresence mode="wait">
          {open && (
            <>
              {/* Backdrop */}
              <motion.div
                key="backdrop"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="fixed inset-0 bg-black/50 z-40"
                onClick={() => {
                  if (setOpen) setOpen(false);
                }}
              />
              {/* Sidebar Drawer */}
              <motion.aside
                key="sidebar"
                data-sidebar
                initial={{ x: '-100%' }}
                animate={{ x: 0 }}
                exit={{ x: '-100%' }}
                transition={{ type: 'spring', damping: 25, stiffness: 200 }}
                className={cn(
                  'fixed left-0 top-0 h-screen w-64 flex-col border-r border-border bg-sidebar text-text z-50',
                  'flex shadow-xl'
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

  // Desktop: Fixed sidebar that expands/collapses
  return (
    <SidebarContext.Provider value={{ open: isOpen, setOpen, isHovered: hoverOpen, isMobile: false }}>
      <aside
        onMouseEnter={() => {
          if (!open) {
            setHoverOpen(true);
          }
        }}
        onMouseLeave={() => {
          setHoverOpen(false);
        }}
        className={cn(
          'group/sidebar relative flex h-screen w-16 flex-col border-r border-border bg-sidebar text-text transition-all duration-300 z-50',
          'hidden lg:flex',
          isOpen && 'w-64'
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
    // Close sidebar on mobile when navigating
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
        // When collapsed, center the icon with no horizontal padding
        open ? 'gap-3 px-3 py-2' : 'justify-center px-0 py-2',
        // On mobile, always show full width
        isMobile && 'gap-3 px-3 py-2',
        className
      )}
    >
      <span className={cn(
        'flex-shrink-0 flex items-center justify-center',
        isActive && '[&>svg]:text-primary [&>div]:bg-primary/15',
        !isActive && '[&>svg]:text-textSecondary',
        // Ensure icon is centered when collapsed (desktop only)
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

