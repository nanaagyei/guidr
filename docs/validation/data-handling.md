# Pilot data handling checklist (internal)

> **Status:** draft v0 for owner review (issue #52), 2026-11-07. Internal checklist for whoever
> runs the pilot. It is **not legal advice**. §9 lists the points a lawyer should review.
> Applies to the pilot run by hand in spreadsheets (decision D9 in #37), not to the Guidr app.

## 1. Rule zero

**No sheet, folder or record is created for an applicant until their consent from
`consent-form.md` is recorded.** File the consent record in the private pilot folder under the
applicant's opaque reference (`applicant_ref`, for example `A-007`). Names and email addresses
appear only in the private contact sheet (§4), never in this repository or in any file shared
outside the access list.

## 2. Data inventory

| Data | Where it comes from | Where it lives | Personal? |
|---|---|---|---|
| Name, email address | Applicant | Private contact sheet | Yes |
| Consent records (service, outcome) | Applicant | Private consent folder | Yes |
| Qualification answers: citizenship, destination countries, degree type, field, degree completed or final year, first-deadline timing | Qualification screen | Private contact sheet / applicant-ask log | Yes |
| Portfolio rows (`templates/portfolio.csv` columns) | Applicant and advisor | One private sheet per applicant | Yes (linked by `applicant_id`) |
| Weekly review log | Advisor | Private sheet | Yes (linked by `applicant_id`) |
| Program cards (program facts, sources, verification state) | Advisor from primary sources | Shared private sheet | No: describes programs |
| Incident log | Advisor | Private sheet | Yes, where it lists affected applicants |
| Outcomes (only with outcome consent) | Applicant | Private sheet | Yes until anonymised |
| Payment records | Payment provider | Payment provider and bookkeeping | Yes |

## 3. Sensitive fields and why each is needed

| Field | Why the workflow needs it | Minimisation |
|---|---|---|
| Country of citizenship | Eligibility and funding rules (`citizenship_eligibility` in the verification policy) | Country only; never a passport or ID |
| Destination countries | Which deadlines and rules apply | Country list only |
| Degree completed or final year | Pilot qualification | Yes/no only; no transcripts or grades |

**Do not collect:** ethnicity, religion, health, disability, sexual orientation, political
views, immigration status beyond citizenship, grades, test scores, financial details, identity
documents. If an applicant volunteers any of these, do not record them. Delete the message
containing them once you have dealt with it.

## 4. Storage location and access list

- **Storage:** `<OWNER TO CONFIRM: one private, access-controlled location, e.g. a Google Drive
  folder owned by the Guidr account with two-step sign-in>`. No local copies on shared machines.
  No copies in email beyond the original message. Never in the Guidr repository.
- **Access list** (keep this list current; review it at each cohort start):
  - Advisor: the founder.
  - Second checker: `<OWNER TO NAME: opaque reference>`. Access to program cards and to the
    portfolio sheets of the applicants they check.
- Share by named account, never by "anyone with the link". Remove access the day someone leaves.

## 5. Retention schedule

| Data | Kept until |
|---|---|
| Contact sheet, portfolio sheets, weekly review logs, consent records | 90 days after the pilot ends |
| Outcomes (with outcome consent) | Anonymised (name, email and `applicant_ref` link removed) at the 90-day point, then kept |
| Program cards | Kept (no personal data) |
| Incident log | Kept; replace affected applicants with a count at the 90-day point |
| Payment records | As long as tax and accounting law requires `<OWNER TO CONFIRM>` |

Put the 90-day deletion date in the calendar on the day the pilot ends.

## 6. Deletion procedure

Use this for a request at any time and for the 90-day sweep. Reply within **14 days**.

1. Find the applicant's `applicant_ref` in the contact sheet.
2. Delete their portfolio sheet.
3. Delete their rows in the weekly review log and the applicant-ask log.
4. In the incident log, replace their reference with "1 applicant".
5. Outcomes: delete them, or, if outcome consent was given and the request is the 90-day sweep
   rather than a deletion request, anonymise them.
6. Delete their consent record, **except** keep a one-line note
   `<applicant_ref> deleted on <date> at their request` so the request can be shown to have been
   honoured.
7. Delete their row in the contact sheet, and their emails beyond what is needed for that note.
8. If the waitlist form tool (#79) holds their sign-up, delete the row there and in any export.
9. Email the applicant to confirm the deletion is done.

## 7. Copy (access) requests

Within 14 days, send the applicant their contact-sheet row, their portfolio sheet, their weekly
review rows and any outcome record, as a spreadsheet or PDF. Send it only to the email address on
file.

## 8. Breach response

A breach is any access to applicant data by someone not on the access list, or any loss of it
(for example a link shared publicly, or a lost device that was signed in).

1. Contain it at once: revoke the link or access, and sign the device out.
2. Write down what was exposed, for whom, from when to when.
3. Tell the affected applicants promptly, and within **72 hours** at most, saying what happened and
   what they should do.
4. Check whether a regulator must be notified (see §9) and do so within the required time.
5. Record the cause and the change that prevents a repeat.

## 9. Regimes that may apply (flag for a lawyer; not legal advice)

Applicants may live anywhere (D1 in #37), so several regimes may apply depending on where the
applicant is and where Guidr operates. **A lawyer should confirm before the first applicant signs:**

- **EU/EEA GDPR and UK GDPR:** applicants in Europe or the UK; lawful basis (consent and
  contract), international transfers to the storage provider, the 72-hour regulator
  notification, and whether a representative is needed.
- **Ghana Data Protection Act, 2012 (Act 843):** registration with the Data Protection
  Commission, if Guidr operates from or processes data in Ghana.
- **Nigeria Data Protection Act 2023, Kenya Data Protection Act 2019, India DPDP Act 2023**, and
  others: the likely applicant origins.
- **US state laws (for example CCPA/CPRA):** probably below thresholds for a small pilot, but
  confirm.
- **Payments:** card data stays with the payment provider. Never record card numbers.

Keep collection minimal (§3). It is the most effective way to reduce exposure across all of
these.
