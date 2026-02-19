'use client';

import { useState, useEffect } from 'react';
import { getDocuments } from '@/utils/api';
import Link from 'next/link';

export default function TranscriptStatus() {
  const [transcript, setTranscript] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadTranscript();
  }, []);

  async function loadTranscript() {
    try {
      const documents = await getDocuments();
      const transcriptDoc = documents.find(
        (doc: any) => doc.document_type === 'transcript' && doc.processing_status === 'completed'
      );
      setTranscript(transcriptDoc);
    } catch (err) {
      console.error('Failed to load transcript:', err);
    } finally {
      setLoading(false);
    }
  }

  if (loading || !transcript || !transcript.extracted_summary) {
    return null;
  }

  const gpa = transcript.extracted_summary.gpa_value;
  const institution = transcript.extracted_summary.institution_name;

  return (
    <div className="mb-6 bg-card rounded-xl p-4 border-l-4 border-primary">
      <p className="text-sm font-medium text-text mb-1">Transcript Uploaded</p>
      {gpa && (
        <p className="text-gray-700">
          GPA extracted: <strong>{gpa}</strong> / {transcript.extracted_summary.gpa_scale}
          {institution && ` from ${institution}`}
        </p>
      )}
      <Link
        href="/documents"
        className="text-sm text-text hover:underline mt-2 inline-block"
      >
        View all documents →
      </Link>
    </div>
  );
}

