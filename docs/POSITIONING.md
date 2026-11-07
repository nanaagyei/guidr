# Guidr positioning

> Updated 2026-11-07. Decided on 2026-09-30 (owner decisions tracked in #37). Supersedes the
> self-serve "AI graduate school discovery" direction described in older documents.

## Who Guidr is for

Advisors, and the international applicants they support, applying to **funded research degrees**
(PhD and research master's). Applicants may come from any country (D1). Other program types
(taught master's, professional and business degrees) come later (#78).

During the first pilot the founder is the advisor (D2); external advisors are added later (#75).

## The core promise

> **Every application decision has an owner, a source, a deadline and a verification state.**

Guidr is an advisor-led, verified application-operations workflow: a portfolio of applications
with milestones and owners, program cards whose critical facts are checked against the program's
own sources, and an advisor review loop. It is not a discovery engine, a chance calculator or an
essay writer.

## What "verified" means

"Verified" is **reserved for human verification**: a named person read a primary source (the
program, department, graduate school or funder, or a written reply from their staff) on a recorded
date and recorded the value and the link. Machine confidence, completeness scores and model output
are never called verified. Full definition, fact types, states, second checker, display rules and
incident response: [`guidr-backend/docs/VERIFICATION_POLICY.md`](../guidr-backend/docs/VERIFICATION_POLICY.md) (#38).

## Validation gate and stage plan

Nothing beyond Stage 0 is built until validation passes. Stages are enforced by gate issues with
GitHub "blocked by" links; never start an issue whose blockers are open.

| Stage | Goal | Exit gate |
|---|---|---|
| **Stage 0** | Validation (prepay asks to partners #39 and applicants #40, manual concierge pilot run in spreadsheets, verification-cost log #41) and a truthful product surface (#42, #43, #44, #55, #56, #69, #80) | **#72** |
| **Stage 1** | One cohort runs on the software: durable entities and trust model (#45), advisor role (#46), verified program card (#47), portfolio board (#48), review queue (#49), corrections (#50), event log (#59) | **#74** |
| **Stage 2** | Renewal and unprompted use: re-verification and change history (#62), cohort operations (#63), integrations (#64), unprompted-use test (#65) | **#76** |
| **Stage 3** | Extend: outcomes (#66), evidence snapshots (#67), partner reporting and SSO (#68), destination playbooks (#77), further applicant types (#78) | — |

During validation the self-serve product is **frozen** (D6): no new work on recommendations,
tiers, fit scores, funding discovery, document parsing or essay feedback. The pilot runs in an
off-the-shelf spreadsheet (D9). Pricing for the pilot: applicant USD 249 for the 8-week
concierge, refunded in full if the cohort does not run; partner USD 5,000 for a fixed-scope
8-week cohort of up to 25 applicants (D3).

## Do not build

From the register in #70. Each item lists the only condition under which it could be reconsidered.

| Item | Why | Reconsider only if |
|---|---|---|
| Generic AI chat or an "advisor bot" | Commodity; hides uncertainty behind prose | Never as an authority. Constrained summaries with source links may be proposed after Stage 3 |
| Essay generation, rewriting or identity-writing | Trust and integrity risk; commodity | Not reconsidered |
| Admission-probability or "chance" scores | Outcomes are dominated by external factors; small biased samples | Not reconsidered. Tiers and fit scores are removed in #73 |
| A global or undifferentiated program catalog | Verification cost before demand | A paying partner's cohort needs specific programs; then only those |
| Direct-apply or submission infrastructure | Owned by incumbents | After Stage 3, with a partner request |
| Pay-to-play or institution-sponsored rankings | Destroys ranking trust | Not reconsidered |
| University CRM or student-information-system integrations | Premature; long procurement | After three renewing partners (#68) |
| Universities as the first buyer | Compromises impartiality | After Stage 3 |
| Faculty "responsiveness" scores or user-submitted rumours | Unverifiable; harmful | Not reconsidered |
| Causal claims about admission outcomes | No valid comparison | Only with a designed evaluation |

Deferred items (with and without their own issues) are tracked in #70.

## Data handling

The repository is private, but names and personal data of applicants and partners never go in it;
use opaque references (`applicant_ref`, `org_ref`). Pilot consent and data terms live in
[`docs/validation/`](validation/) (#52).
