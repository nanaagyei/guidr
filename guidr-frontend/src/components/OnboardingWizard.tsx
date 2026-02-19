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
  Sparkles
} from 'lucide-react';
import { DashboardCard } from './ui/dashboard-card';
import { Input } from './ui/input';
import { Select } from './ui/select';
import { RadioGroup } from './ui/radio-group';
import { saveOnboardingStep, completeOnboarding } from '@/utils/api';

interface OnboardingData {
  // Step 2: Basic Info
  intended_degree?: string;
  primary_field_of_study?: string;
  preferred_start_term?: string;
  preferred_start_year?: number;
  
  // Step 3: Preferences
  preferred_countries?: string[];
  preferred_cities?: string[];
  funding_priority?: string;
  program_style_preference?: string;
  
  // Step 4: Academic Background
  institution_name?: string;
  gpa_value?: number;
  gpa_scale?: number;
  
  // Step 5: Goals & Interests
  research_areas?: string[];
  career_goals?: string;
  secondary_fields?: string[];
}

const TOTAL_STEPS = 6;

export default function OnboardingWizard() {
  const router = useRouter();
  const [currentStep, setCurrentStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState<OnboardingData>({});

  const updateFormData = (updates: Partial<OnboardingData>) => {
    setFormData(prev => ({ ...prev, ...updates }));
  };

  const handleNext = async () => {
    if (currentStep < TOTAL_STEPS) {
      // Save progress on step 2-5
      if (currentStep >= 2 && currentStep <= 5) {
        setLoading(true);
        try {
          await saveOnboardingStep(formData);
        } catch (error) {
          console.error('Failed to save progress:', error);
        } finally {
          setLoading(false);
        }
      }
      setCurrentStep(prev => prev + 1);
    }
  };

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep(prev => prev - 1);
    }
  };

  const handleComplete = async () => {
    setLoading(true);
    try {
      await saveOnboardingStep(formData);
      await completeOnboarding();
      router.push('/dashboard');
    } catch (error) {
      console.error('Failed to complete onboarding:', error);
    } finally {
      setLoading(false);
    }
  };

  const progress = (currentStep / TOTAL_STEPS) * 100;

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="w-full max-w-3xl">
        {/* Progress Bar */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-2">
            <h1 className="text-2xl font-semibold text-text">Welcome to Guidr</h1>
            <span className="text-sm text-gray-600">
              Step {currentStep} of {TOTAL_STEPS}
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${progress}%` }}
              transition={{ duration: 0.3 }}
              className="bg-primary h-2 rounded-full"
            />
          </div>
        </div>

        {/* Step Content */}
        <AnimatePresence mode="wait">
          <motion.div
            key={currentStep}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            transition={{ duration: 0.3 }}
          >
            <DashboardCard>
              {currentStep === 1 && <WelcomeStep />}
              {currentStep === 2 && <BasicInfoStep formData={formData} updateFormData={updateFormData} />}
              {currentStep === 3 && <PreferencesStep formData={formData} updateFormData={updateFormData} />}
              {currentStep === 4 && <AcademicStep formData={formData} updateFormData={updateFormData} />}
              {currentStep === 5 && <GoalsStep formData={formData} updateFormData={updateFormData} />}
              {currentStep === 6 && <CompletionStep formData={formData} />}
            </DashboardCard>
          </motion.div>
        </AnimatePresence>

        {/* Navigation */}
        <div className="flex items-center justify-between mt-6">
          <button
            onClick={handleBack}
            disabled={currentStep === 1 || loading}
            className="flex items-center gap-2 px-6 py-3 bg-gray-100 text-gray-700 font-semibold rounded-lg hover:bg-gray-200 transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <ArrowLeft className="h-4 w-4" />
            Back
          </button>

          {currentStep < TOTAL_STEPS ? (
            <button
              onClick={handleNext}
              disabled={loading}
              className="flex items-center gap-2 px-6 py-3 bg-primary text-white font-semibold rounded-lg hover:bg-primaryHover transition disabled:opacity-50"
            >
              Next
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
    </div>
  );
}

// Step 1: Welcome
function WelcomeStep() {
  return (
    <div className="text-center py-8">
      <div className="mb-6">
        <div className="inline-flex p-4 bg-primary/10 rounded-full mb-4">
          <GraduationCap className="h-12 w-12 text-primary" />
        </div>
      </div>
      <h2 className="text-2xl font-semibold text-text mb-4">Welcome to Guidr!</h2>
      <p className="text-gray-600 mb-6 max-w-md mx-auto">
        We&apos;re excited to help you on your graduate school journey. Let&apos;s set up your profile
        to get personalized recommendations and track your applications.
      </p>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-8 text-left">
        <div className="p-4 bg-gray-50 rounded-lg">
          <CheckCircle2 className="h-5 w-5 text-primary mb-2" />
          <h3 className="font-semibold text-text mb-1">Find Programs</h3>
          <p className="text-sm text-gray-600">Discover schools that match your goals</p>
        </div>
        <div className="p-4 bg-gray-50 rounded-lg">
          <CheckCircle2 className="h-5 w-5 text-primary mb-2" />
          <h3 className="font-semibold text-text mb-1">Track Applications</h3>
          <p className="text-sm text-gray-600">Stay organized with deadlines and tasks</p>
        </div>
        <div className="p-4 bg-gray-50 rounded-lg">
          <CheckCircle2 className="h-5 w-5 text-primary mb-2" />
          <h3 className="font-semibold text-text mb-1">Get Support</h3>
          <p className="text-sm text-gray-600">AI-powered essay reviews and guidance</p>
        </div>
      </div>
    </div>
  );
}

// Step 2: Basic Info
function BasicInfoStep({ formData, updateFormData }: { formData: OnboardingData; updateFormData: (data: Partial<OnboardingData>) => void }) {
  return (
    <div className="space-y-6">
      <div className="text-center mb-6">
        <GraduationCap className="h-8 w-8 text-primary mx-auto mb-3" />
        <h2 className="text-xl font-semibold text-text mb-2">Basic Information</h2>
        <p className="text-sm text-gray-600">Tell us about your graduate school goals</p>
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
      />

      <Input
        label="Field of Study"
        placeholder="e.g., Computer Science, Business Administration"
        value={formData.primary_field_of_study || ''}
        onChange={(e) => updateFormData({ primary_field_of_study: e.target.value })}
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
          placeholder="2025"
          value={formData.preferred_start_year?.toString() || ''}
          onChange={(e) => updateFormData({ preferred_start_year: parseInt(e.target.value) || undefined })}
        />
      </div>
    </div>
  );
}

// Step 3: Preferences
function PreferencesStep({ formData, updateFormData }: { formData: OnboardingData; updateFormData: (data: Partial<OnboardingData>) => void }) {
  return (
    <div className="space-y-6">
      <div className="text-center mb-6">
        <MapPin className="h-8 w-8 text-primary mx-auto mb-3" />
        <h2 className="text-xl font-semibold text-text mb-2">Preferences</h2>
        <p className="text-sm text-gray-600">Help us recommend the right programs</p>
      </div>

      <Input
        label="Preferred Countries (comma-separated)"
        placeholder="e.g., USA, Canada, UK"
        value={formData.preferred_countries?.join(', ') || ''}
        onChange={(e) => {
          const countries = e.target.value.split(',').map(c => c.trim()).filter(Boolean);
          updateFormData({ preferred_countries: countries });
        }}
        helperText="Enter countries separated by commas"
      />

      <Input
        label="Preferred Cities (optional)"
        placeholder="e.g., San Francisco, Boston, Toronto"
        value={formData.preferred_cities?.join(', ') || ''}
        onChange={(e) => {
          const cities = e.target.value.split(',').map(c => c.trim()).filter(Boolean);
          updateFormData({ preferred_cities: cities });
        }}
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

// Step 4: Academic Background
function AcademicStep({ formData, updateFormData }: { formData: OnboardingData; updateFormData: (data: Partial<OnboardingData>) => void }) {
  return (
    <div className="space-y-6">
      <div className="text-center mb-6">
        <BookOpen className="h-8 w-8 text-primary mx-auto mb-3" />
        <h2 className="text-xl font-semibold text-text mb-2">Academic Background</h2>
        <p className="text-sm text-gray-600">Tell us about your current or previous studies</p>
      </div>

      <Input
        label="Current/Previous Institution"
        placeholder="e.g., University of California, Berkeley"
        value={formData.institution_name || ''}
        onChange={(e) => updateFormData({ institution_name: e.target.value })}
      />

      <div className="grid grid-cols-2 gap-4">
        <Input
          label="GPA (optional)"
          type="number"
          step="0.01"
          placeholder="3.75"
          value={formData.gpa_value?.toString() || ''}
          onChange={(e) => updateFormData({ gpa_value: parseFloat(e.target.value) || undefined })}
        />

        <Input
          label="GPA Scale"
          type="number"
          step="0.1"
          placeholder="4.0"
          value={formData.gpa_scale?.toString() || ''}
          onChange={(e) => updateFormData({ gpa_scale: parseFloat(e.target.value) || undefined })}
        />
      </div>

      <p className="text-xs text-gray-500">
        * You can add more detailed academic records later in your profile
      </p>
    </div>
  );
}

// Step 5: Goals & Interests
function GoalsStep({ formData, updateFormData }: { formData: OnboardingData; updateFormData: (data: Partial<OnboardingData>) => void }) {
  return (
    <div className="space-y-6">
      <div className="text-center mb-6">
        <Target className="h-8 w-8 text-primary mx-auto mb-3" />
        <h2 className="text-xl font-semibold text-text mb-2">Goals & Interests</h2>
        <p className="text-sm text-gray-600">Help us personalize your recommendations</p>
      </div>

      <Input
        label="Research Areas (comma-separated)"
        placeholder="e.g., Machine Learning, Natural Language Processing, Computer Vision"
        value={formData.research_areas?.join(', ') || ''}
        onChange={(e) => {
          const areas = e.target.value.split(',').map(a => a.trim()).filter(Boolean);
          updateFormData({ research_areas: areas });
        }}
        helperText="Enter research interests separated by commas"
      />

      <div>
        <label className="block text-sm font-medium text-text mb-1.5">
          Career Goals
        </label>
        <textarea
          className="w-full px-4 py-2.5 rounded-lg border border-border focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
          rows={4}
          placeholder="Tell us about your career goals and aspirations..."
          value={formData.career_goals || ''}
          onChange={(e) => updateFormData({ career_goals: e.target.value })}
        />
      </div>

      <Input
        label="Secondary Fields (optional)"
        placeholder="e.g., Business, Education, Public Health"
        value={formData.secondary_fields?.join(', ') || ''}
        onChange={(e) => {
          const fields = e.target.value.split(',').map(f => f.trim()).filter(Boolean);
          updateFormData({ secondary_fields: fields });
        }}
      />
    </div>
  );
}

// Step 6: Completion
function CompletionStep({ formData }: { formData: OnboardingData }) {
  return (
    <div className="text-center py-8">
      <div className="mb-6">
        <div className="inline-flex p-4 bg-green-100 rounded-full mb-4">
          <CheckCircle2 className="h-12 w-12 text-green-600" />
        </div>
      </div>
      <h2 className="text-2xl font-semibold text-text mb-4">You{"\u2019"}re All Set!</h2>
      <p className="text-gray-600 mb-6 max-w-md mx-auto">
        We{"\u2019"}ve saved your information. You can always update your profile later in Settings.
      </p>
      <div className="bg-gray-50 rounded-lg p-6 text-left max-w-md mx-auto">
        <h3 className="font-semibold text-text mb-3">Next Steps:</h3>
        <ul className="space-y-2 text-sm text-gray-700">
          <li className="flex items-start gap-2">
            <CheckCircle2 className="h-4 w-4 text-primary mt-0.5 flex-shrink-0" />
            <span>Browse and save schools that interest you</span>
          </li>
          <li className="flex items-start gap-2">
            <CheckCircle2 className="h-4 w-4 text-primary mt-0.5 flex-shrink-0" />
            <span>Get personalized program recommendations</span>
          </li>
          <li className="flex items-start gap-2">
            <CheckCircle2 className="h-4 w-4 text-primary mt-0.5 flex-shrink-0" />
            <span>Upload documents and start tracking applications</span>
          </li>
        </ul>
      </div>
    </div>
  );
}

