'use client';

import { motion } from 'framer-motion';
import { ReactNode } from 'react';
import { cn } from '@/lib/utils';

interface DashboardCardProps {
  children: ReactNode;
  className?: string;
  hover?: boolean;
  index?: number;
}

export function DashboardCard({ children, className, hover = true, index = 0 }: DashboardCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05, duration: 0.3 }}
      whileHover={hover ? { scale: 1.02, y: -4 } : undefined}
      className={cn(
        'bg-card rounded-xl p-6 shadow-sm border border-border',
        'transition-all duration-200',
        hover && 'hover:shadow-md hover:border-primary/30',
        className
      )}
    >
      {children}
    </motion.div>
  );
}

