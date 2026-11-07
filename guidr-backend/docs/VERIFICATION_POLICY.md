# Critical-fact verification and incident policy — v0

> **Status:** draft v0 for owner review (issue #38). Last updated 2026-11-07.
> Values marked *owner-adjustable* are proposed defaults. Change them only as described in
> §10 (change control).

**The rule:** every critical fact shown to an applicant is **correct, explicitly unverified, or
abstained**. A critical fact shown as verified that turns out to be wrong is an incident (§8).

**"Verified" is reserved for human verification.** At Guidr, *verified* means only what §4
defines: a named person read a primary source on a recorded date. Machine confidence, model
output, field completeness, agreement between sources, and cached or "promoted" pipeline data
are **never** called verified, in the product, in the API, in documents, or in conversation
with applicants or partners.

This policy is written so that one person can follow it by hand with a spreadsheet: one row per
fact, with the columns listed in §4.

---

## 1. Scope

- **Applicants:** funded research degrees only, meaning PhD and research master's programs,
  for applicants of any origin (decision D1 in #37).
- **Facts:** the seven critical fact types in §2, for each program an applicant is actively
  applying to.
- **Not covered:** other degree types (taught master's, professional and business degrees; see
  #78), catalogue-wide coverage, non-critical facts (rankings, descriptions, faculty
  biographies), and any automation. Automation may later produce *unverified* values (#61). It
  never produces *verified* ones.

## 2. Critical fact types

There are exactly these seven. The key is the exact string used in spreadsheets and, later, in
code.

| Key | Fact type | Example |
|---|---|---|
| `deadline` | Application deadline for a named intake and round, with time zone if stated | "Fall 2027 intake, round 1 (funding consideration): 1 December 2026, 23:59 US Eastern" |
| `funding` | Funding type and whether it is guaranteed, competitive or absent | "All admitted PhD students receive 5 years of guaranteed tuition waiver plus stipend" / "Competitive departmental scholarships; no guaranteed funding" |
| `citizenship_eligibility` | Whether applicants of a given citizenship may apply and may receive the funding | "International applicants may apply; the named studentship is open to home-fee-status students only" |
| `required_tests` | Tests required or waived (GRE, English-language tests and minimum scores) | "GRE not accepted; IELTS 7.0 overall, no band below 6.5, waived for degrees taught in English" |
| `required_documents` | Documents required (transcripts, statements, number of references, writing sample, proposal) | "CV, statement of purpose (2 pages max), 3 references, research proposal (1,500 words)" |
| `fee_waiver` | Application fee and waiver availability | "USD 90 fee; waiver for applicants from listed countries, request before 15 November" |
| `supervisor_contact` | Whether a supervisor must be contacted or must agree before applying | "Applicants must secure a supervisor's agreement before submitting" / "Do not contact faculty before admission" |

A fact always belongs to one **program + intake + round** (and, for `citizenship_eligibility`,
one citizenship). "Deadline: December" is not a recordable value; record what the source says,
in full.

## 3. Primary source

A **primary source** is one of:

1. a page or document published by the **program, department, graduate school or funder**
   itself (including official PDFs, handbooks and application-portal pages); or
2. a **written reply from their staff** (email or portal message), kept with the date and the
   sender's role. Store the reply itself in a private location outside the repo, never in it.

The following are **never** a primary source: aggregators and ranking sites, forums and social
media, other applicants, consultants, Guidr's own earlier records, and any model or AI-research
output, including Guidr's research pipeline. These may point a verifier towards a primary
source. They cannot replace one.

If two primary sources conflict (for example the department page and the graduate school page),
the fact is not verified. Record both, ask the program in writing, and mark the fact
`abstained` until the program replies.

## 4. States

Each fact has exactly one of four **stored** states. A fifth state is **computed**.

| State | Stored? | Meaning |
|---|---|---|
| `verified` | stored | A named person read a primary source on a recorded date and recorded the value and the source link. |
| `unverified` | stored | A value exists (from a model, an aggregator or the applicant) with no human check. |
| `abstained` | stored | A person looked and could not confirm. No value is shown, and the applicant is told who to ask. |
| `under_review` | stored | The fact has been challenged and is being re-checked. |
| `stale` | **computed** | `verified`, but older than the maximum age for its type (§5). |

**Recording a `verified` fact requires all of:** the value as stated by the source; the source
URL (or a reference to the stored staff reply); the date observed; the verifier's name; and,
for the types in §6, the second checker's name and date. **If any of these is missing, the fact
is `unverified`.**

Minimum spreadsheet columns per fact: `program`, `intake_round`, `fact_type`, `value`, `state`,
`source_url`, `date_observed`, `verifier`, `second_checker`, `second_check_date`, `notes`.

## 5. Maximum age per type

A `verified` fact becomes `stale` when today minus `date_observed` exceeds:

| Key | Maximum age (days), owner-adjustable |
|---|---|
| `deadline` | 30 |
| `funding` | 60 |
| `citizenship_eligibility` | 90 |
| `required_tests` | 90 |
| `required_documents` | 90 |
| `fee_waiver` | 90 |
| `supervisor_contact` | 60 |

**Final-stretch rule:** within 21 days of an application's deadline, that application's
`deadline` fact is re-checked **weekly**, whatever its age.

To bring a stale fact back to `verified`, re-read the primary source. Recording "still the same"
counts as a new verification with a new date.

## 6. Second checker

`deadline`, `citizenship_eligibility` and `funding` are shown as **verified only after a second
person, not the first verifier, has confirmed the same primary source** and recorded their name
and date. Until then they are displayed as `unverified`, even if the first verifier is
confident.

**During the founder-only pilot** (D2 in #37) the founder is the first verifier. The second
checker is: **`<OWNER TO NAME: person or role, e.g. "paid freelance checker A">`**. Record the
second checker by an opaque reference in the repo and keep their real name off it. If no second
checker is available, these three types stay `unverified` for the applicant. They are not
waived.

## 7. Display rules

What an applicant sees, in the spreadsheet during the pilot and in the product later:

| State | Shown to the applicant |
|---|---|
| `verified` | The value, a link to the source, the date observed, and who verified it (with the second checker, for §6 types). |
| `unverified` | The value, clearly labelled **"Not yet verified: confirm on the program's website"**, with where it came from if known. Never styled like a verified fact. |
| `abstained` | **No value.** A line saying it could not be confirmed, and who to ask (for example, the department's admissions email). |
| `under_review` | The last value with a visible **"Under review"** mark, plus the date the challenge was raised. |
| `stale` | The value with a visible **"Last checked <date>, may be out of date"** mark. Not called verified. |

Machine confidence scores, completeness percentages and model agreement are **never** called
"verified", "confirmed", "checked" or "accurate". At most they may be described as
"found automatically".

## 8. Incident definition and response

**An incident** is any critical fact that was shown as `verified` and turned out to be wrong when
it was shown. A fact that was `unverified`, `abstained`, `stale` (and displayed as stale) or
`under_review` and turned out wrong is **not** an incident; record it as a correction.

**Response:**

1. **Immediately:** mark the fact `under_review`.
2. **Within 24 hours:** tell every applicant who was shown the wrong value what changed and what
   to do. Use the same channel as the pilot (email). Keep the message factual.
3. **Correct** the fact with a new verification from a primary source. For §6 types this needs a
   new second check.
4. **Record** in the incident log (a private sheet; see #50 for the later in-product log): date
   found, fact, wrong value, correct value, applicants affected, how it was found, cause, and
   the change that prevents a repeat.
5. **Gate effect:** one incident fails the trust gate in #72 until this policy is revised (§10)
   **and** a fresh 20% sample of verified facts (§9) has been re-checked with no further error.

## 9. Sampling

During the pilot, a second person re-checks **20% of `verified` facts**, chosen at random each
week from facts verified that week. They re-check against the primary source and record:
fact id, re-check date, re-checker, and whether the value matched. A mismatch on a fact shown as
verified is an incident (§8). Facts already second-checked under §6 still count towards the
sample population.

## 10. Change control

This policy changes only through:

- **an incident review** (§8, step 4) that names the change; or
- **an owner decision recorded in #37**.

Each change bumps the version at the top of this file and adds a dated line below. If the policy
proves too heavy to follow during the pilot, **cut fact types before cutting the second
checker**.

### Change log

- 2026-11-07: v0 drafted from issue #38 for owner review.
