'use client';

import { useRef, useState, useEffect } from 'react';
import { motion, useScroll, useTransform } from 'framer-motion';

interface ParallaxLayerProps {
  children?: React.ReactNode;
  scrollRange?: [number, number];
  offsetRange?: [number, number];
  className?: string;
}

export function ParallaxLayer({
  children,
  scrollRange = [0, 500],
  offsetRange = [0, 80],
  className = '',
}: ParallaxLayerProps) {
  const ref = useRef<HTMLDivElement>(null);
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const checkMobile = () => setIsMobile(typeof window !== 'undefined' && window.innerWidth < 768);
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  const { scrollY } = useScroll();
  const y = useTransform(
    scrollY,
    scrollRange,
    isMobile ? [0, 0] : offsetRange
  );

  return (
    <motion.div ref={ref} style={{ y }} className={className}>
      {children}
    </motion.div>
  );
}
