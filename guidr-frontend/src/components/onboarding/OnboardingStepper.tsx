'use client';

import { motion } from 'framer-motion';
import {
  Sparkles,
  GraduationCap,
  MapPin,
  BookOpen,
  Target,
  CheckCircle2,
} from 'lucide-react';
import { cn } from '@/lib/utils';

const STEPS = [
  { label: 'Welcome', icon: Sparkles },
  { label: 'Basics', icon: GraduationCap },
  { label: 'Preferences', icon: MapPin },
  { label: 'Academic', icon: BookOpen },
  { label: 'Goals', icon: Target },
  { label: 'Done', icon: CheckCircle2 },
];

interface OnboardingStepperProps {
  currentStep: number; // 1-indexed
  totalSteps?: number;
}

export default function OnboardingStepper({
  currentStep,
  totalSteps = 6,
}: OnboardingStepperProps) {
  return (
    <>
      {/* Desktop stepper */}
      <div className="hidden md:flex items-center justify-center gap-0 w-full max-w-2xl mx-auto mb-8">
        {STEPS.map((step, idx) => {
          const stepNum = idx + 1;
          const isCompleted = stepNum < currentStep;
          const isActive = stepNum === currentStep;
          const Icon = isCompleted ? CheckCircle2 : step.icon;

          return (
            <div key={idx} className="flex items-center">
              {/* Step circle */}
              <div className="flex flex-col items-center">
                <div
                  className={cn(
                    'relative flex items-center justify-center w-10 h-10 rounded-full border-2 transition-all duration-300',
                    isCompleted && 'bg-success/10 border-success',
                    isActive && 'border-accent bg-accent/10',
                    !isCompleted && !isActive && 'border-border bg-card',
                  )}
                >
                  <Icon
                    className={cn(
                      'h-4 w-4 transition-colors duration-300',
                      isCompleted && 'text-success',
                      isActive && 'text-accent',
                      !isCompleted && !isActive && 'text-textMuted',
                    )}
                  />
                  {isActive && (
                    <motion.div
                      className="absolute inset-0 rounded-full border-2 border-accent"
                      initial={{ scale: 1 }}
                      animate={{ scale: [1, 1.15, 1] }}
                      transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
                    />
                  )}
                </div>
                <span
                  className={cn(
                    'mt-1.5 text-xs font-medium transition-colors',
                    isCompleted && 'text-success',
                    isActive && 'text-accent',
                    !isCompleted && !isActive && 'text-textMuted',
                  )}
                >
                  {step.label}
                </span>
              </div>

              {/* Connecting line */}
              {idx < STEPS.length - 1 && (
                <div className="w-8 h-0.5 mx-1 mt-[-1rem] relative overflow-hidden bg-border rounded-full">
                  <motion.div
                    className="absolute inset-y-0 left-0 bg-success rounded-full"
                    initial={{ width: '0%' }}
                    animate={{ width: isCompleted ? '100%' : '0%' }}
                    transition={{ duration: 0.4, ease: 'easeOut' }}
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Mobile stepper: compact */}
      <div className="md:hidden flex items-center justify-between mb-6 px-1">
        <span className="text-sm font-medium text-textSecondary">
          Step {currentStep} of {totalSteps}
        </span>
        <span className="text-sm font-display font-semibold text-accent">
          {STEPS[currentStep - 1]?.label}
        </span>
        {/* Thin progress bar */}
        <div className="absolute left-0 right-0 bottom-0 h-0.5 bg-border">
          <motion.div
            className="h-full bg-accent rounded-full"
            initial={{ width: '0%' }}
            animate={{ width: `${((currentStep - 1) / (totalSteps - 1)) * 100}%` }}
            transition={{ duration: 0.3 }}
          />
        </div>
      </div>
    </>
  );
}
