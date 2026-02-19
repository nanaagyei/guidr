/**
 * API client utilities for making HTTP requests to the backend.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface ApiError {
  detail: string;
}

/**
 * Make a fetch request with credentials included.
 */
async function fetchWithCredentials(
  url: string,
  options: RequestInit = {}
): Promise<Response> {
  return fetch(`${API_BASE_URL}${url}`, {
    ...options,
    credentials: 'include', // Include cookies
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });
}

/**
 * Send 2FA code to email.
 */
export async function send2FACode(data: {
  email: string;
  purpose: 'register' | 'login' | 'password_reset';
}): Promise<any> {
  const response = await fetchWithCredentials('/auth/2fa/send', {
    method: 'POST',
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new Error(error.detail || 'Failed to send verification code');
  }

  return response.json();
}

/**
 * Check if an email is already registered.
 */
export async function checkEmail(data: {
  email: string;
}): Promise<{ exists: boolean; message: string }> {
  const response = await fetchWithCredentials('/auth/check-email', {
    method: 'POST',
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new Error(error.detail || 'Failed to check email');
  }

  return response.json();
}

/**
 * Verify 2FA code.
 */
export async function verify2FACode(data: {
  email: string;
  code: string;
  purpose: 'register' | 'login';
}): Promise<any> {
  const response = await fetchWithCredentials('/auth/2fa/verify', {
    method: 'POST',
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new Error(error.detail || 'Invalid verification code');
  }

  return response.json();
}

/**
 * Register a new user (requires 2FA code).
 */
export async function postRegister(data: {
  email: string;
  password: string;
  full_name?: string;
  verification_code: string;
}): Promise<any> {
  const response = await fetchWithCredentials('/auth/register', {
    method: 'POST',
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new Error(error.detail || 'Registration failed');
  }

  return response.json();
}

/**
 * Verify credentials before sending 2FA code.
 */
export async function verifyCredentials(data: {
  email: string;
  password: string;
}): Promise<any> {
  const response = await fetchWithCredentials('/auth/verify-credentials', {
    method: 'POST',
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new Error(error.detail || 'Invalid credentials');
  }

  return response.json();
}

/**
 * Login user (requires 2FA code).
 */
export async function postLogin(data: {
  email: string;
  password: string;
  verification_code: string;
  remember_me?: boolean;
}): Promise<any> {
  const response = await fetchWithCredentials('/auth/login', {
    method: 'POST',
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new Error(error.detail || 'Login failed');
  }

  return response.json();
}

/**
 * Logout user.
 */
export async function postLogout(): Promise<void> {
  await fetchWithCredentials('/auth/logout', {
    method: 'POST',
  });
}

/**
 * Get current authenticated user.
 */
export async function getMe(): Promise<any> {
  const response = await fetchWithCredentials('/auth/me');

  if (!response.ok) {
    if (response.status === 401) {
      return null; // Not authenticated
    }
    const error: ApiError = await response.json();
    throw new Error(error.detail || 'Failed to fetch user');
  }

  return response.json();
}

/**
 * Request password reset (sends 2FA code).
 */
export async function requestPasswordReset(data: {
  email: string;
}): Promise<any> {
  const response = await fetchWithCredentials('/auth/password-reset/request', {
    method: 'POST',
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new Error(error.detail || 'Failed to request password reset');
  }

  return response.json();
}

/**
 * Verify password reset code.
 */
export async function verifyPasswordResetCode(data: {
  email: string;
  code: string;
}): Promise<any> {
  const response = await fetchWithCredentials('/auth/password-reset/verify', {
    method: 'POST',
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new Error(error.detail || 'Invalid verification code');
  }

  return response.json();
}

/**
 * Reset password.
 */
export async function resetPassword(data: {
  email: string;
  reset_token: string;
  new_password: string;
}): Promise<any> {
  const response = await fetchWithCredentials('/auth/password-reset/reset', {
    method: 'POST',
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new Error(error.detail || 'Failed to reset password');
  }

  return response.json();
}

/**
 * Get user profile.
 */
export async function getProfile(): Promise<any> {
  const response = await fetchWithCredentials('/profile');

  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new Error(error.detail || 'Failed to fetch profile');
  }

  return response.json();
}

/**
 * Update user profile.
 */
export async function putProfile(data: any): Promise<any> {
  const response = await fetchWithCredentials('/profile', {
    method: 'PUT',
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new Error(error.detail || 'Failed to update profile');
  }

  return response.json();
}

/**
 * Get academic records.
 */
export async function getAcademicRecords(): Promise<any[]> {
  const response = await fetchWithCredentials('/academic-records');

  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new Error(error.detail || 'Failed to fetch academic records');
  }

  return response.json();
}

/**
 * Create academic record.
 */
export async function postAcademicRecord(data: any): Promise<any> {
  const response = await fetchWithCredentials('/academic-records', {
    method: 'POST',
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new Error(error.detail || 'Failed to create academic record');
  }

  return response.json();
}

/**
 * Delete academic record.
 */
export async function deleteAcademicRecord(id: string): Promise<void> {
  const response = await fetchWithCredentials(`/academic-records/${id}`, {
    method: 'DELETE',
  });

  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new Error(error.detail || 'Failed to delete academic record');
  }
}

/**
 * Search programs.
 */
export async function searchPrograms(params: {
  degree_level?: string;
  field_of_study?: string;
  country?: string;
  min_tuition?: number;
  max_tuition?: number;
  keyword?: string;
  page?: number;
  page_size?: number;
}): Promise<any> {
  const queryParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      queryParams.append(key, String(value));
    }
  });

  const response = await fetchWithCredentials(`/programs?${queryParams.toString()}`);

  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new Error(error.detail || 'Failed to search programs');
  }

  return response.json();
}

/**
 * Get program details.
 */
export async function getProgram(id: string): Promise<any> {
  const response = await fetchWithCredentials(`/programs/${id}`);

  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new Error(error.detail || 'Failed to fetch program');
  }

  return response.json();
}

/**
 * Get upload URL for document.
 */
export async function getDocumentUploadUrl(data: {
  filename: string;
  document_type: string;
}): Promise<any> {
  const response = await fetchWithCredentials('/documents/upload-url', {
    method: 'POST',
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new Error(error.detail || 'Failed to get upload URL');
  }

  return response.json();
}

/**
 * Confirm document upload.
 */
export async function confirmDocumentUpload(documentId: string): Promise<any> {
  const response = await fetchWithCredentials(`/documents/${documentId}/confirm`, {
    method: 'POST',
  });

  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new Error(error.detail || 'Failed to confirm upload');
  }

  return response.json();
}

/**
 * Get documents list.
 */
export async function getDocuments(): Promise<any[]> {
  const response = await fetchWithCredentials('/documents');

  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new Error(error.detail || 'Failed to fetch documents');
  }

  return response.json();
}

/**
 * Get document details.
 */
export async function getDocument(id: string): Promise<any> {
  const response = await fetchWithCredentials(`/documents/${id}`);

  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new Error(error.detail || 'Failed to fetch document');
  }

  return response.json();
}

/**
 * Delete document.
 */
export async function deleteDocument(id: string): Promise<void> {
  const response = await fetchWithCredentials(`/documents/${id}`, {
    method: 'DELETE',
  });

  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new Error(error.detail || 'Failed to delete document');
  }
}

/**
 * Get all essays.
 */
export async function getEssays(): Promise<any[]> {
  const response = await fetchWithCredentials('/essays');

  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new Error(error.detail || 'Failed to fetch essays');
  }

  return response.json();
}

/**
 * Get essay by ID.
 */
export async function getEssay(id: string, includeVersions: boolean = false, includeReviews: boolean = false): Promise<any> {
  const params = new URLSearchParams();
  if (includeVersions) params.append('include_versions', 'true');
  if (includeReviews) params.append('include_reviews', 'true');
  
  const queryString = params.toString();
  const url = `/essays/${id}${queryString ? `?${queryString}` : ''}`;
  
  const response = await fetchWithCredentials(url);

  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new Error(error.detail || 'Failed to fetch essay');
  }

  return response.json();
}

/**
 * Create essay.
 */
export async function createEssay(data: {
  title: string;
  essay_type: string;
  content: string;
  target_program_id?: string;
}): Promise<any> {
  const response = await fetchWithCredentials('/essays', {
    method: 'POST',
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new Error(error.detail || 'Failed to create essay');
  }

  return response.json();
}

/**
 * Update essay.
 */
export async function updateEssay(id: string, data: {
  title?: string;
  content?: string;
}): Promise<any> {
  const response = await fetchWithCredentials(`/essays/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new Error(error.detail || 'Failed to update essay');
  }

  return response.json();
}

/**
 * Delete essay.
 */
export async function deleteEssay(id: string): Promise<void> {
  const response = await fetchWithCredentials(`/essays/${id}`, {
    method: 'DELETE',
  });

  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new Error(error.detail || 'Failed to delete essay');
  }
}

/**
 * Request essay review.
 */
export async function requestEssayReview(id: string): Promise<any> {
  const response = await fetchWithCredentials(`/essays/${id}/review`, {
    method: 'POST',
  });

  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new Error(error.detail || 'Failed to request review');
  }

  return response.json();
}

/**
 * Request recommendations.
 */
export async function requestRecommendations(triggerSource?: string): Promise<any> {
  const params = triggerSource ? `?trigger_source=${triggerSource}` : '';
  const response = await fetchWithCredentials(`/recommendations/request${params}`, {
    method: 'POST',
  });

  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new Error(error.detail || 'Failed to request recommendations');
  }

  return response.json();
}

/**
 * Get latest recommendations.
 */
export async function getLatestRecommendations(): Promise<any> {
  const response = await fetchWithCredentials('/recommendations/latest');

  if (!response.ok) {
    if (response.status === 404) {
      return null;
    }
    const error: ApiError = await response.json();
    throw new Error(error.detail || 'Failed to fetch recommendations');
  }

  return response.json();
}

/**
 * Get recommendation session by ID.
 */
export async function getRecommendationSession(sessionId: string): Promise<any> {
  const response = await fetchWithCredentials(`/recommendations/session/${sessionId}`);

  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new Error(error.detail || 'Failed to fetch session');
  }

  return response.json();
}

/**
 * Get recommendation history.
 */
export async function getRecommendationHistory(): Promise<any> {
  const response = await fetchWithCredentials('/recommendations/history');

  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new Error(error.detail || 'Failed to fetch history');
  }

  return response.json();
}

/**
 * Get professors with filters.
 */
export async function getProfessors(params?: {
  institution_id?: string;
  country?: string;
  research_keyword?: string;
  page?: number;
  page_size?: number;
}): Promise<any> {
  const queryParams = new URLSearchParams();
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        queryParams.append(key, String(value));
      }
    });
  }
  
  const queryString = queryParams.toString();
  const url = `/professors${queryString ? `?${queryString}` : ''}`;
  
  const response = await fetchWithCredentials(url);

  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new Error(error.detail || 'Failed to fetch professors');
  }

  return response.json();
}

/**
 * Get professor by ID.
 */
export async function getProfessor(id: string): Promise<any> {
  const response = await fetchWithCredentials(`/professors/${id}`);

  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new Error(error.detail || 'Failed to fetch professor');
  }

  return response.json();
}

/**
 * Generate email draft for professor.
 */
export async function generateProfessorEmail(professorId: string, programId?: string): Promise<any> {
  const params = programId ? `?program_id=${programId}` : '';
  const response = await fetchWithCredentials(`/professors/${professorId}/generate-email${params}`, {
    method: 'POST',
  });

  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new Error(error.detail || 'Failed to generate email');
  }

  return response.json();
}

/**
 * Get outreach emails.
 */
export async function getOutreachEmails(): Promise<any[]> {
  const response = await fetchWithCredentials('/professors/outreach/emails');

  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new Error(error.detail || 'Failed to fetch outreach emails');
  }

  return response.json();
}

/**
 * Get outreach email by ID.
 */
export async function getOutreachEmail(id: string): Promise<any> {
  const response = await fetchWithCredentials(`/professors/outreach/emails/${id}`);

  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new Error(error.detail || 'Failed to fetch email');
  }

  return response.json();
}

/**
 * Update outreach email.
 */
export async function updateOutreachEmail(id: string, subject?: string, body?: string): Promise<any> {
  const params = new URLSearchParams();
  if (subject) params.append('subject', subject);
  if (body) params.append('body', body);
  
  const queryString = params.toString();
  const response = await fetchWithCredentials(`/professors/outreach/emails/${id}?${queryString}`, {
    method: 'PUT',
  });

  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new Error(error.detail || 'Failed to update email');
  }

  return response.json();
}

/**
 * Delete outreach email.
 */
export async function deleteOutreachEmail(id: string): Promise<void> {
  const response = await fetchWithCredentials(`/professors/outreach/emails/${id}`, {
    method: 'DELETE',
  });

  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new Error(error.detail || 'Failed to delete email');
  }
}

/**
 * Get institutions (for filters).
 */
export async function getInstitutions(params?: {
  country?: string;
  city?: string;
  name?: string;
}): Promise<any[]> {
  const queryParams = new URLSearchParams();
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        queryParams.append(key, String(value));
      }
    });
  }
  
  const queryString = queryParams.toString();
  const url = `/schools${queryString ? `?${queryString}` : ''}`;
  
  const response = await fetchWithCredentials(url);

  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new Error(error.detail || 'Failed to fetch institutions');
  }

  return response.json();
}

/**
 * Search institutions with filters.
 */
export async function searchInstitutions(params: {
  query?: string;
  country?: string;
  type?: string;
  control?: string;
  page?: number;
  page_size?: number;
}): Promise<any> {
  const queryParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      queryParams.append(key, String(value));
    }
  });

  const response = await fetchWithCredentials(`/schools?${queryParams.toString()}`);

  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new Error(error.detail || 'Failed to search institutions');
  }

  return response.json();
}

/**
 * Get funding opportunities with filters.
 */
export async function getFundingOpportunities(params?: {
  institution_id?: string;
  funding_type?: string;
  covers_tuition?: boolean;
  covers_stipend?: boolean;
  keyword?: string;
  country?: string;
  min_amount?: number;
  max_amount?: number;
  page?: number;
  page_size?: number;
  use_search?: boolean;
}): Promise<{
  results: any[];
  page: number;
  total_pages: number;
  total_results: number;
}> {
  const queryParams = new URLSearchParams();
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        queryParams.append(key, String(value));
      }
    });
  }
  const queryString = queryParams.toString();
  const url = `/funding${queryString ? `?${queryString}` : ''}`;
  const response = await fetchWithCredentials(url);

  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new Error(error.detail || 'Failed to fetch funding opportunities');
  }

  return response.json();
}

/**
 * Get funding opportunity by ID.
 */
export async function getFundingOpportunity(id: string): Promise<any> {
  const response = await fetchWithCredentials(`/funding/${id}`);

  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new Error(error.detail || 'Failed to fetch funding opportunity');
  }

  return response.json();
}

/**
 * Get funding opportunities by institution ID.
 */
export async function getFundingByInstitution(institutionId: string): Promise<{
  institution: { id: string; name: string };
  funding_opportunities: any[];
  total: number;
}> {
  const response = await fetchWithCredentials(
    `/funding/institution/${institutionId}`
  );

  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new Error(error.detail || 'Failed to fetch funding for institution');
  }

  return response.json();
}

/**
 * Check if user needs onboarding (based on profile completion).
 */
export async function checkOnboardingStatus(): Promise<{ needsOnboarding: boolean; completionScore: number }> {
  try {
    const profile = await getProfile();
    const completionScore = profile?.profile_completion_score || 0;
    return {
      needsOnboarding: completionScore < 30,
      completionScore,
    };
  } catch (error) {
    // If profile doesn't exist, user needs onboarding
    return {
      needsOnboarding: true,
      completionScore: 0,
    };
  }
}

/**
 * Save onboarding step data.
 */
export async function saveOnboardingStep(data: any): Promise<any> {
  return putProfile(data);
}

/**
 * Complete onboarding (mark as complete).
 */
export async function completeOnboarding(): Promise<any> {
  // Onboarding is considered complete when profile_completion_score >= 30
  // This happens automatically when profile is saved
  return getProfile();
}

// --- Pipeline / Enrichment ---

/**
 * Trigger enrichment for a single entity.
 */
export async function triggerEnrichment(
  entityKind: string,
  entityId: string,
  priority: string = 'high',
  forceRefresh: boolean = false
): Promise<any> {
  const response = await fetchWithCredentials('/pipeline/enrich', {
    method: 'POST',
    body: JSON.stringify({
      entity_kind: entityKind,
      entity_id: entityId,
      priority,
      force_refresh: forceRefresh,
    }),
  });

  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new Error(error.detail || 'Failed to trigger enrichment');
  }

  return response.json();
}

/**
 * Poll enrichment job status.
 */
export async function pollJobStatus(jobId: string): Promise<any> {
  const response = await fetchWithCredentials(`/pipeline/jobs/${jobId}`);

  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new Error(error.detail || 'Failed to fetch job status');
  }

  return response.json();
}

/**
 * Get cache freshness status for an entity.
 */
export async function getCacheStatus(
  entityKind: string,
  entityId: string
): Promise<any> {
  const params = new URLSearchParams({
    entity_kind: entityKind,
    entity_id: entityId,
  });

  const response = await fetchWithCredentials(`/pipeline/cache/status?${params.toString()}`);

  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new Error(error.detail || 'Failed to fetch cache status');
  }

  return response.json();
}