'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useRouter } from 'next/navigation';
import {
  ArrowRight,
  ArrowLeft,
  CheckCircle2,
  GraduationCap,
  MapPin,
  BookOpen,
  Target,
  Sparkles,
  Info,
  Clock,
} from 'lucide-react';
import { DashboardCard } from './ui/dashboard-card';
import { Input } from './ui/input';
import { TagInput } from './ui/tag-input';
import { Select } from './ui/select';
import { RadioGroup } from './ui/radio-group';
import { saveOnboardingStep, completeOnboarding } from '@/utils/api';
import { useProfileCompletion } from '@/contexts/ProfileCompletionContext';
import { useOnboardingDraft } from '@/hooks/useOnboardingDraft';
import { validateStep, OnboardingData } from './onboarding/validation';
import OnboardingStepper from './onboarding/OnboardingStepper';
import ProfilePreview from './onboarding/ProfilePreview';
import { cn } from '@/lib/utils';

const TOTAL_STEPS = 6;

export default function OnboardingWizard() {
  const router = useRouter();
  const { refresh: refreshCompletion } = useProfileCompletion();
  const {
    formData,
    currentStep,
    updateFormData,
    setStep,
    clearDraft,
    hasDraft,
  } = useOnboardingDraft();

  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [direction, setDirection] = useState(1); // 1 = forward, -1 = backward

  const handleNext = async () => {
    if (currentStep < TOTAL_STEPS) {
      // Validate current step
      if (currentStep >= 2 && currentStep <= 5) {
        const validation = validateStep(currentStep, formData);
        if (!validation.valid) {
          setErrors(validation.errors);
          return;
        }
        setErrors({});

        // Save progress to backend
        setLoading(true);
        try {
          await saveOnboardingStep(formData);
          refreshCompletion();
        } catch (error) {
          console.error('Failed to save progress:', error);
        } finally {
          setLoading(false);
        }
      }

      setDirection(1);
      setStep(currentStep + 1);
    }
  };

  const handleBack = () => {
    if (currentStep > 1) {
      setErrors({});
      setDirection(-1);
      setStep(currentStep - 1);
    }
  };

  const handleComplete = async () => {
    setLoading(true);
    try {
      await saveOnboardingStep(formData);
      await completeOnboarding();
      clearDraft();
      refreshCompletion();
      router.push('/dashboard');
    } catch (error) {
      console.error('Failed to complete onboarding:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleFinishLater = async () => {
    // Save current data and redirect to dashboard
    setLoading(true);
    try {
      if (currentStep >= 2) {
        await saveOnboardingStep(formData);
        refreshCompletion();
      }
      router.push('/dashboard');
    } catch (error) {
      console.error('Failed to save progress:', error);
      router.push('/dashboard');
    } finally {
      setLoading(false);
    }
  };

  // Direction-aware spring transitions
  const variants = {
    enter: (dir: number) => ({
      x: dir > 0 ? 60 : -60,
      opacity: 0,
      scale: 0.98,
    }),
    center: {
      x: 0,
      opacity: 1,
      scale: 1,
    },
    exit: (dir: number) => ({
      x: dir > 0 ? -60 : 60,
      opacity: 0,
      scale: 0.98,
    }),
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-background to-accent/5 flex items-start justify-center p-4 pt-8 lg:pt-12">
      <div className="w-full max-w-5xl">
        {/* Stepper */}
        <OnboardingStepper currentStep={currentStep} totalSteps={TOTAL_STEPS} />

        {/* Draft restored notice */}
        {hasDraft && currentStep > 1 && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-4 flex items-center gap-2 text-sm text-secondary bg-secondary/10 rounded-lg px-4 py-2"
          >
            <Clock className="h-4 w-4" />
            <span>We restored your previous progress. Pick up where you left off!</span>
          </motion.div>
        )}

        {/* Main content: form + preview panel */}
        <div className="flex gap-8">
          {/* Form area */}
          <div className="flex-1 min-w-0">
            <AnimatePresence mode="wait" custom={direction}>
              <motion.div
                key={currentStep}
                custom={direction}
                variants={variants}
                initial="enter"
                animate="center"
                exit="exit"
                transition={{ type: 'spring', stiffness: 300, damping: 30 }}
              >
                <DashboardCard>
                  {currentStep === 1 && <WelcomeStep />}
                  {currentStep === 2 && (
                    <BasicInfoStep formData={formData} updateFormData={updateFormData} errors={errors} />
                  )}
                  {currentStep === 3 && (
                    <PreferencesStep formData={formData} updateFormData={updateFormData} errors={errors} />
                  )}
                  {currentStep === 4 && (
                    <AcademicStep formData={formData} updateFormData={updateFormData} errors={errors} />
                  )}
                  {currentStep === 5 && (
                    <GoalsStep formData={formData} updateFormData={updateFormData} errors={errors} />
                  )}
                  {currentStep === 6 && <CompletionStep formData={formData} />}
                </DashboardCard>
              </motion.div>
            </AnimatePresence>

            {/* Navigation */}
            <div className="flex items-center justify-between mt-6">
              <div className="flex items-center gap-3">
                <button
                  onClick={handleBack}
                  disabled={currentStep === 1 || loading}
                  className="flex items-center gap-2 px-6 py-3 bg-card border border-border text-textSecondary font-semibold rounded-lg hover:bg-sidebarHover transition disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ArrowLeft className="h-4 w-4" />
                  Back
                </button>

                {/* Finish Later — visible on steps 2-5 */}
                {currentStep >= 2 && currentStep < TOTAL_STEPS && (
                  <button
                    onClick={handleFinishLater}
                    disabled={loading}
                    className="text-sm font-medium text-textMuted hover:text-textSecondary transition"
                  >
                    Finish later
                  </button>
                )}
              </div>

              {currentStep < TOTAL_STEPS ? (
                <button
                  onClick={handleNext}
                  disabled={loading}
                  className="flex items-center gap-2 px-6 py-3 bg-primary text-white font-semibold rounded-lg hover:bg-primaryHover transition disabled:opacity-50"
                >
                  {loading ? 'Saving...' : 'Next'}
                  <ArrowRight className="h-4 w-4" />
                </button>
              ) : (
                <button
                  onClick={handleComplete}
                  disabled={loading}
                  className="flex items-center gap-2 px-6 py-3 bg-primary text-white font-semibold rounded-lg hover:bg-primaryHover transition disabled:opacity-50"
                >
                  {loading ? 'Saving...' : 'Get Started'}
                  <Sparkles className="h-4 w-4" />
                </button>
              )}
            </div>
          </div>

          {/* Live preview panel — desktop only */}
          <ProfilePreview data={formData} />
        </div>
      </div>
    </div>
  );
}

// -- Tooltip helper --
function WhyTooltip({ text }: { text: string }) {
  const [show, setShow] = useState(false);
  return (
    <span className="relative inline-flex ml-1.5">
      <button
        type="button"
        onMouseEnter={() => setShow(true)}
        onMouseLeave={() => setShow(false)}
        onClick={() => setShow(!show)}
        className="text-textMuted hover:text-textSecondary transition"
        aria-label="Why we ask this"
      >
        <Info className="h-3.5 w-3.5" />
      </button>
      <AnimatePresence>
        {show && (
          <motion.div
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 4 }}
            className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 bg-primary text-white text-xs rounded-lg shadow-lg w-56 z-50"
          >
            {text}
            <div className="absolute top-full left-1/2 -translate-x-1/2 w-2 h-2 bg-primary rotate-45 -mt-1" />
          </motion.div>
        )}
      </AnimatePresence>
    </span>
  );
}

// -- Step Components --

function WelcomeStep() {
  return (
    <div className="text-center py-8">
      <div className="mb-6">
        <div className="inline-flex p-4 bg-accent/10 rounded-full mb-4">
          <GraduationCap className="h-12 w-12 text-accent" />
        </div>
      </div>
      <h2 className="text-2xl font-display font-semibold text-text mb-4">
        Welcome to Guidr!
      </h2>
      <p className="text-textSecondary mb-6 max-w-md mx-auto">
        We&apos;re excited to help you on your graduate school journey. Let&apos;s set up your profile
        to get personalized recommendations and track your applications.
      </p>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-8 text-left">
        {[
          { title: 'Find Programs', desc: 'Discover schools that match your goals' },
          { title: 'Track Applications', desc: 'Stay organized with deadlines and tasks' },
          { title: 'Get Support', desc: 'AI-powered essay reviews and guidance' },
        ].map((item) => (
          <div key={item.title} className="p-4 bg-card border border-border rounded-xl">
            <CheckCircle2 className="h-5 w-5 text-accent mb-2" />
            <h3 className="font-semibold text-text mb-1">{item.title}</h3>
            <p className="text-sm text-textSecondary">{item.desc}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

interface StepProps {
  formData: OnboardingData;
  updateFormData: (data: Partial<OnboardingData>) => void;
  errors: Record<string, string>;
}

function BasicInfoStep({ formData, updateFormData, errors }: StepProps) {
  return (
    <div className="space-y-6">
      <div className="text-center mb-6">
        <GraduationCap className="h-8 w-8 text-accent mx-auto mb-3" />
        <h2 className="text-xl font-display font-semibold text-text mb-2">Basic Information</h2>
        <p className="text-sm text-textSecondary">Tell us about your graduate school goals</p>
      </div>

      <RadioGroup
        name="intended_degree"
        label="What degree are you pursuing?"
        value={formData.intended_degree || ''}
        onChange={(value) => updateFormData({ intended_degree: value })}
        options={[
          { value: 'masters', label: "Master's Degree", description: 'M.S., M.A., MBA, etc.' },
          { value: 'phd', label: 'Doctorate (PhD)', description: 'Research-focused doctoral degree' },
        ]}
        error={errors.intended_degree}
      />

      <Input
        label="Field of Study"
        placeholder="e.g., Computer Science, Business Administration"
        value={formData.primary_field_of_study || ''}
        onChange={(e) => updateFormData({ primary_field_of_study: e.target.value })}
        error={errors.primary_field_of_study}
      />

      <div className="grid grid-cols-2 gap-4">
        <Select
          label="Preferred Start Term"
          value={formData.preferred_start_term || ''}
          onChange={(e) => updateFormData({ preferred_start_term: e.target.value })}
          options={[
            { value: '', label: 'Select term' },
            { value: 'fall', label: 'Fall' },
            { value: 'spring', label: 'Spring' },
            { value: 'summer', label: 'Summer' },
          ]}
        />

        <Input
          label="Preferred Start Year"
          type="number"
          placeholder="2026"
          value={formData.preferred_start_year?.toString() || ''}
          onChange={(e) => updateFormData({ preferred_start_year: parseInt(e.target.value) || undefined })}
        />
      </div>
    </div>
  );
}

function PreferencesStep({ formData, updateFormData, errors }: StepProps) {
  return (
    <div className="space-y-6">
      <div className="text-center mb-6">
        <MapPin className="h-8 w-8 text-accent mx-auto mb-3" />
        <h2 className="text-xl font-display font-semibold text-text mb-2">Preferences</h2>
        <p className="text-sm text-textSecondary">Help us recommend the right programs</p>
      </div>

      <TagInput
        label="Preferred Countries"
        placeholder="e.g., USA, Canada, UK — press comma or Enter"
        value={formData.preferred_countries || []}
        onChange={(countries) => updateFormData({ preferred_countries: countries })}
        helperText="Press comma or Enter after each country"
        error={errors.preferred_countries}
      />

      <TagInput
        label="Preferred Cities (optional)"
        placeholder="e.g., San Francisco, Boston — press comma or Enter"
        value={formData.preferred_cities || []}
        onChange={(cities) => updateFormData({ preferred_cities: cities })}
      />

      <RadioGroup
        name="funding_priority"
        label="Funding Priority"
        value={formData.funding_priority || ''}
        onChange={(value) => updateFormData({ funding_priority: value })}
        options={[
          { value: 'must_have', label: 'Must Have', description: 'Funding is required' },
          { value: 'nice_to_have', label: 'Nice to Have', description: 'Prefer funding but not required' },
          { value: 'no_preference', label: 'No Preference', description: 'Not a deciding factor' },
        ]}
      />

      <RadioGroup
        name="program_style"
        label="Program Style Preference"
        value={formData.program_style_preference || ''}
        onChange={(value) => updateFormData({ program_style_preference: value })}
        options={[
          { value: 'research', label: 'Research-Focused', description: 'Thesis-based programs' },
          { value: 'coursework', label: 'Coursework-Based', description: 'Course-focused programs' },
          { value: 'both', label: 'Both', description: 'Open to either style' },
        ]}
      />
    </div>
  );
}

function AcademicStep({ formData, updateFormData, errors }: StepProps) {
  return (
    <div className="space-y-6">
      <div className="text-center mb-6">
        <BookOpen className="h-8 w-8 text-accent mx-auto mb-3" />
        <h2 className="text-xl font-display font-semibold text-text mb-2">Academic Background</h2>
        <p className="text-sm text-textSecondary">Tell us about your current or previous studies</p>
      </div>

      <Input
        label="Current/Previous Institution"
        placeholder="e.g., University of California, Berkeley"
        value={formData.institution_name || ''}
        onChange={(e) => updateFormData({ institution_name: e.target.value })}
      />

      <div className="grid grid-cols-2 gap-4">
        <div>
          <div className="flex items-center">
            <Input
              label="GPA (optional)"
              type="number"
              step="0.01"
              placeholder="3.75"
              value={formData.gpa_value?.toString() || ''}
              onChange={(e) => updateFormData({ gpa_value: parseFloat(e.target.value) || undefined })}
              error={errors.gpa_value}
            />
            <WhyTooltip text="Your GPA helps calibrate program recommendations. It is never shared externally." />
          </div>
        </div>

        <Input
          label="GPA Scale"
          type="number"
          step="0.1"
          placeholder="4.0"
          value={formData.gpa_scale?.toString() || ''}
          onChange={(e) => updateFormData({ gpa_scale: parseFloat(e.target.value) || undefined })}
          error={errors.gpa_scale}
        />
      </div>

      <p className="text-xs text-textMuted">
        You can add more detailed academic records later in your profile.
      </p>
    </div>
  );
}

function GoalsStep({ formData, updateFormData, errors }: StepProps) {
  return (
    <div className="space-y-6">
      <div className="text-center mb-6">
        <Target className="h-8 w-8 text-accent mx-auto mb-3" />
        <h2 className="text-xl font-display font-semibold text-text mb-2">Goals & Interests</h2>
        <p className="text-sm text-textSecondary">
          Help us personalize your recommendations
        </p>
      </div>

      <TagInput
        label="Research Areas"
        placeholder="e.g., Machine Learning, NLP — press comma or Enter"
        value={formData.research_areas || []}
        onChange={(areas) => updateFormData({ research_areas: areas })}
        helperText="Examples: Computer Vision, Medical Imaging, LLMs"
        maxTags={15}
      />

      <div>
        <label className="block text-sm font-medium text-text mb-1.5">
          Career Goals
        </label>
        <textarea
          className="w-full px-4 py-2.5 rounded-lg border border-border bg-card text-text focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent transition-colors"
          rows={4}
          placeholder="Tell us about your career goals and aspirations..."
          value={formData.career_goals || ''}
          onChange={(e) => updateFormData({ career_goals: e.target.value })}
        />
      </div>

      <TagInput
        label="Secondary Fields (optional)"
        placeholder="e.g., Business, Education — press comma or Enter"
        value={formData.secondary_fields || []}
        onChange={(fields) => updateFormData({ secondary_fields: fields })}
        maxTags={8}
      />
    </div>
  );
}

function CompletionStep({ formData }: { formData: OnboardingData }) {
  return (
    <div className="text-center py-8">
      <div className="mb-6">
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: 'spring', stiffness: 200, damping: 15, delay: 0.1 }}
          className="inline-flex p-4 bg-success/10 rounded-full mb-4"
        >
          <CheckCircle2 className="h-12 w-12 text-success" />
        </motion.div>
      </div>
      <h2 className="text-2xl font-display font-semibold text-text mb-4">
        You{'\u2019'}re All Set!
      </h2>
      <p className="text-textSecondary mb-6 max-w-md mx-auto">
        We{'\u2019'}ve saved your information. You can always update your profile later in Settings.
      </p>
      <div className="bg-card border border-border rounded-xl p-6 text-left max-w-md mx-auto">
        <h3 className="font-display font-semibold text-text mb-3">Next Steps:</h3>
        <ul className="space-y-2 text-sm text-textSecondary">
          {[
            'Browse and save schools that interest you',
            'Get personalized program recommendations',
            'Upload documents and start tracking applications',
          ].map((item) => (
            <li key={item} className="flex items-start gap-2">
              <CheckCircle2 className="h-4 w-4 text-accent mt-0.5 flex-shrink-0" />
              <span>{item}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
