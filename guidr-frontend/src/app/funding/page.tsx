'use client';

import { DollarSign } from 'lucide-react';
import ComingSoon from '@/components/ComingSoon';

// NOTE: The full funding-discovery implementation is preserved in git history
// (pre-launch gating). Re-enable once funding data is seeded and the discovery
// pipeline is validated. See launch plan Workstream C.
export default function FundingPage() {
  return (
    <ComingSoon
      title="Funding Discovery"
      description="We're curating fellowships, assistantships, and scholarships matched to your programs and research. This will be available shortly after launch."
      icon={<DollarSign className="h-7 w-7" />}
    />
  );
}
