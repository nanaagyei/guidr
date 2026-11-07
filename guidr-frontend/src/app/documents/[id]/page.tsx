'use client';

import { FileText } from 'lucide-react';
import ComingSoon from '@/components/ComingSoon';

// NOTE: The full document detail implementation is preserved in git history
// (pre-launch gating, issue #69). Re-enable together with the documents list page
// and the backend `ENABLE_DOCUMENTS_API` flag.
export default function DocumentDetailPage() {
  return (
    <ComingSoon
      title="Documents"
      description="Upload your CV, transcripts, and resume to auto-fill your profile and power smarter matching. We're putting the finishing touches on parsing — check back soon."
      icon={<FileText className="h-7 w-7" />}
    />
  );
}
