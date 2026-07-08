'use client';

import { motion } from 'framer-motion';

interface TierBadgeProps {
  tier: 'dream' | 'reach' | 'target' | 'safety';
  count?: number;
}

export default function TierBadge({ tier, count }: TierBadgeProps) {
  const getTierConfig = (tier: string) => {
    switch (tier) {
      case 'dream':
        return {
          color: 'bg-yellow-100 text-yellow-800 border-yellow-200',
          icon: '✨',
        };
      case 'reach':
        return {
          color: 'bg-orange-100 text-orange-800 border-orange-200',
          icon: '🎯',
        };
      case 'target':
        return {
          color: 'bg-blue-100 text-blue-700 border-blue-200',
          icon: '🎓',
        };
      case 'safety':
        return {
          color: 'bg-green-100 text-green-700 border-green-200',
          icon: '🛡️',
        };
      default:
        return {
          color: 'bg-gray-100 text-gray-800 border-gray-200',
          icon: '📌',
        };
    }
  };

  const config = getTierConfig(tier);
  const label = tier.charAt(0).toUpperCase() + tier.slice(1);

  return (
    <motion.div
      whileHover={{ scale: 1.05 }}
      className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold border ${config.color}`}
    >
      <span>{config.icon}</span>
      <span>{label}</span>
      {count !== undefined && (
        <span className="px-2 py-0.5 bg-white/50 rounded text-xs">
          {count}
        </span>
      )}
    </motion.div>
  );
}
