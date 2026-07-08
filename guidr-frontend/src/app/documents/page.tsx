'use client';

import { FileText } from 'lucide-react';
import ComingSoon from '@/components/ComingSoon';

// NOTE: The full document upload + parsing implementation is preserved in git
// history (pre-launch gating). Re-enable once document parsing/extraction is
// wired end-to-end. See launch plan Workstream C.
export default function DocumentsPage() {
  return (
    <ComingSoon
      title="Documents"
      description="Upload your CV, transcripts, and resume to auto-fill your profile and power smarter matching. We're putting the finishing touches on parsing — check back soon."
      icon={<FileText className="h-7 w-7" />}
    />
  );
}
