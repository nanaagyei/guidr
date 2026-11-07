/**
 * AI research consent: whether research areas, preferred countries and funding priority
 * may be included in prompts sent to research model providers (backend issue #92).
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface AiResearchConsent {
  consented: boolean;
  consented_at: string | null;
}

async function request(options: RequestInit = {}): Promise<AiResearchConsent> {
  const response = await fetch(`${API_BASE_URL}/profile/ai-research-consent`, {
    ...options,
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...options.headers },
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || 'Failed to load AI research consent');
  }
  return response.json();
}

export function getAiResearchConsent(): Promise<AiResearchConsent> {
  return request();
}

export function putAiResearchConsent(consent: boolean): Promise<AiResearchConsent> {
  return request({ method: 'PUT', body: JSON.stringify({ consent }) });
}
