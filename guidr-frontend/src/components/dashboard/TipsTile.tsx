'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { Card, CardHeader, CardContent } from '@/components/ui/card';
import { TileHeader } from '@/components/ui/tile-header';
import { Skeleton } from '@/components/ui/loading-skeleton';
import { getMockTips, type HelpTip } from '@/utils/mockData';
import { motion, AnimatePresence } from 'framer-motion';
import { Lightbulb, BookOpen, HelpCircle, ChevronRight } from 'lucide-react';

export default function TipsTile() {
  const [tips, setTips] = useState<HelpTip[]>([]);
  const [currentTipIndex, setCurrentTipIndex] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchTips = async () => {
      setLoading(true);
      setTimeout(() => {
        const data = getMockTips();
        setTips(data);
        setLoading(false);
      }, 500);
    };

    fetchTips();
  }, []);

  useEffect(() => {
    if (tips.length === 0) return;

    const interval = setInterval(() => {
      setCurrentTipIndex((prev) => (prev + 1) % tips.length);
    }, 6000);

    return () => clearInterval(interval);
  }, [tips.length]);

  const currentTip = tips[currentTipIndex];

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="pb-2">
        <TileHeader
          title="Tips & Guidance"
          icon={<Lightbulb className="h-5 w-5" />}
        />
      </CardHeader>
      <CardContent className="flex-1 pt-0">
        {loading ? (
          <div className="flex-1 space-y-4">
            <div className="p-4 rounded-xl bg-muted/50">
              <Skeleton variant="text" className="w-3/4 h-4 mb-2" />
              <Skeleton variant="text" className="w-full h-3" />
              <Skeleton variant="text" className="w-2/3 h-3 mt-1" />
            </div>
            <div className="space-y-2">
              <Skeleton className="w-full h-12 rounded-xl" />
              <Skeleton className="w-full h-12 rounded-xl" />
            </div>
          </div>
        ) : (
          <div className="flex-1 flex flex-col">
            {currentTip && (
              <div className="mb-4 flex-1">
                <AnimatePresence mode="wait">
                  <motion.div
                    key={currentTipIndex}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    transition={{ duration: 0.3 }}
                    className="p-4 rounded-xl bg-accentLight border border-accent/20"
                  >
                    <div className="flex items-start gap-3">
                      <div className="p-2 bg-accent/20 rounded-xl flex-shrink-0">
                        <Lightbulb className="w-4 h-4 text-accent" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <h3 className="font-semibold text-text text-sm mb-1">
                          {currentTip.title}
                        </h3>
                        <p className="text-xs text-textSecondary line-clamp-3">
                          {currentTip.content}
                        </p>
                      </div>
                    </div>
                  </motion.div>
                </AnimatePresence>

                {tips.length > 1 && (
                  <div className="flex justify-center gap-1.5 mt-3">
                    {tips.map((_, index) => (
                      <button
                        key={index}
                        onClick={() => setCurrentTipIndex(index)}
                        className={`h-1.5 rounded-full transition-all duration-300 ${
                          index === currentTipIndex
                            ? 'w-6 bg-accent'
                            : 'w-1.5 bg-border hover:bg-borderHover'
                        }`}
                        aria-label={`Go to tip ${index + 1}`}
                      />
                    ))}
                  </div>
                )}
              </div>
            )}

            <div className="space-y-2 pt-4 border-t border-border">
              <Link
                href="/help/getting-started"
                className="flex items-center justify-between p-3 rounded-xl border border-border hover:border-primary/30 hover:bg-muted/50 transition-all group"
              >
                <div className="flex items-center gap-3">
                  <div className="p-1.5 rounded-lg bg-primaryLight">
                    <BookOpen className="w-3.5 h-3.5 text-primary" />
                  </div>
                  <span className="text-sm font-medium text-text">Getting Started</span>
                </div>
                <ChevronRight className="w-4 h-4 text-textMuted group-hover:text-primary group-hover:translate-x-0.5 transition-all" />
              </Link>
              <Link
                href="/help/faq"
                className="flex items-center justify-between p-3 rounded-xl border border-border hover:border-primary/30 hover:bg-muted/50 transition-all group"
              >
                <div className="flex items-center gap-3">
                  <div className="p-1.5 rounded-lg bg-primaryLight">
                    <HelpCircle className="w-3.5 h-3.5 text-primary" />
                  </div>
                  <span className="text-sm font-medium text-text">FAQs</span>
                </div>
                <ChevronRight className="w-4 h-4 text-textMuted group-hover:text-primary group-hover:translate-x-0.5 transition-all" />
              </Link>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
