/**
 * Per-step validation for the onboarding wizard.
 */

export interface OnboardingData {
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

export interface StepValidation {
  valid: boolean;
  errors: Record<string, string>;
}

export function validateStep(step: number, data: OnboardingData): StepValidation {
  const errors: Record<string, string> = {};

  switch (step) {
    case 2: {
      if (!data.intended_degree) {
        errors.intended_degree = 'Please select a degree type';
      }
      if (!data.primary_field_of_study?.trim()) {
        errors.primary_field_of_study = 'Please enter your field of study';
      }
      break;
    }
    case 3: {
      if (!data.preferred_countries || data.preferred_countries.length === 0) {
        errors.preferred_countries = 'Please add at least one preferred country';
      }
      break;
    }
    case 4: {
      // Academic background is optional, but if GPA is provided both value and scale are needed
      if (data.gpa_value != null && data.gpa_value > 0) {
        if (!data.gpa_scale || data.gpa_scale <= 0) {
          errors.gpa_scale = 'Please enter the GPA scale (e.g., 4.0)';
        } else if (data.gpa_value > data.gpa_scale) {
          errors.gpa_value = 'GPA cannot exceed the scale';
        }
      }
      if (data.gpa_scale != null && data.gpa_scale > 0 && (data.gpa_value == null || data.gpa_value <= 0)) {
        errors.gpa_value = 'Please enter your GPA value';
      }
      break;
    }
    case 5: {
      // Goals step is optional — no hard requirements
      break;
    }
    default:
      break;
  }

  return { valid: Object.keys(errors).length === 0, errors };
}
