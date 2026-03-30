'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { OnboardingData } from '@/components/onboarding/validation';

const STORAGE_KEY = 'guidr:onboarding:draft';
const DEBOUNCE_MS = 500;
const STALE_DAYS = 30;

interface DraftState {
  formData: OnboardingData;
  currentStep: number;
  savedAt: number;
}

function readDraft(): DraftState | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed: DraftState = JSON.parse(raw);
    // Auto-clear stale drafts
    if (Date.now() - parsed.savedAt > STALE_DAYS * 24 * 60 * 60 * 1000) {
      localStorage.removeItem(STORAGE_KEY);
      return null;
    }
    return parsed;
  } catch {
    localStorage.removeItem(STORAGE_KEY);
    return null;
  }
}

function writeDraft(state: DraftState) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch { /* quota exceeded — ignore */ }
}

export interface UseOnboardingDraft {
  formData: OnboardingData;
  currentStep: number;
  updateFormData: (updates: Partial<OnboardingData>) => void;
  setStep: (step: number) => void;
  clearDraft: () => void;
  hasDraft: boolean;
}

export function useOnboardingDraft(): UseOnboardingDraft {
  const [formData, setFormData] = useState<OnboardingData>({});
  const [currentStep, setCurrentStep] = useState(1);
  const [hasDraft, setHasDraft] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Hydrate from localStorage on mount
  useEffect(() => {
    const draft = readDraft();
    if (draft) {
      setFormData(draft.formData);
      setCurrentStep(draft.currentStep);
      setHasDraft(true);
    }
  }, []);

  // Debounced persistence
  const persistDraft = useCallback(
    (data: OnboardingData, step: number) => {
      if (timerRef.current) clearTimeout(timerRef.current);
      timerRef.current = setTimeout(() => {
        writeDraft({ formData: data, currentStep: step, savedAt: Date.now() });
      }, DEBOUNCE_MS);
    },
    [],
  );

  const updateFormData = useCallback(
    (updates: Partial<OnboardingData>) => {
      setFormData((prev) => {
        const next = { ...prev, ...updates };
        persistDraft(next, currentStep);
        return next;
      });
    },
    [currentStep, persistDraft],
  );

  const setStep = useCallback(
    (step: number) => {
      setCurrentStep(step);
      // Persist step change immediately
      if (timerRef.current) clearTimeout(timerRef.current);
      writeDraft({ formData, currentStep: step, savedAt: Date.now() });
    },
    [formData],
  );

  const clearDraft = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    localStorage.removeItem(STORAGE_KEY);
    setHasDraft(false);
  }, []);

  return { formData, currentStep, updateFormData, setStep, clearDraft, hasDraft };
}
