'use client';

import { useEffect, useState } from 'react';
import { Sparkles } from 'lucide-react';
import {
  getAiResearchConsent,
  putAiResearchConsent,
  type AiResearchConsent as Consent,
} from '@/utils/aiResearchConsent';

export default function AiResearchConsent() {
  const [consent, setConsent] = useState<Consent | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getAiResearchConsent()
      .then(setConsent)
      .catch((e: Error) => setError(e.message));
  }, []);

  const toggle = async () => {
    if (!consent) return;
    setSaving(true);
    setError(null);
    try {
      setConsent(await putAiResearchConsent(!consent.consented));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const on = consent?.consented ?? false;

  return (
    <div className="pt-6 border-t border-border">
      <div className="flex items-center gap-2 mb-4">
        <Sparkles className="h-5 w-5 text-primary" />
        <h3 className="font-semibold text-text">AI research</h3>
      </div>
      <div className="flex items-start justify-between gap-4 p-4 bg-gray-50 rounded-lg border border-border">
        <div className="text-sm text-gray-700 space-y-2">
          <p>
            Let Guidr include your <strong>research areas</strong>, <strong>preferred countries</strong>{' '}
            and <strong>funding priority (high, medium or low)</strong> when it asks our AI research
            provider to look up programs and faculty. Research areas are also used as search
            keywords with OpenAlex, an academic database.
          </p>
          <p>
            Without this, research uses only your intended degree and field of study. We never send
            your name, email, GPA, citizenship, test scores or anything you typed as free text.
          </p>
          {consent?.consented_at && (
            <p className="text-xs text-gray-500">
              Allowed since {new Date(consent.consented_at).toLocaleDateString()}.
            </p>
          )}
          {error && <p className="text-xs text-red-600">{error}</p>}
        </div>
        <button
          type="button"
          role="switch"
          aria-checked={on}
          aria-label="Allow AI research to use my research areas and preferences"
          disabled={!consent || saving}
          onClick={toggle}
          className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors disabled:opacity-50 ${
            on ? 'bg-primary' : 'bg-gray-300'
          }`}
        >
          <span
            className={`inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform ${
              on ? 'translate-x-5' : 'translate-x-0.5'
            }`}
          />
        </button>
      </div>
    </div>
  );
}
