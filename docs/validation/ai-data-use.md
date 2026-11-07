# AI and third-party data use: pilot rules

> **Status:** draft v0 for owner review (issue #52), 2026-11-07.

## The rule for the pilot

1. **No applicant's personal data is sent to a model provider without that applicant's separate,
   written consent for that specific task.** Service consent (`consent-form.md`) does not cover
   it.
2. **Research on program facts is done on the program, not on the person.** Prompts and searches
   name the program, department, institution and intake. They never include an applicant's name,
   email, citizenship, grades, research interests, plans or any other profile field.
3. Model output is never a primary source. It can point to a source. A fact only becomes
   `verified` when a person reads the primary source (`guidr-backend/docs/VERIFICATION_POLICY.md`).
4. Pilot applicants' data is **not entered into the Guidr app** during the pilot. The pilot runs
   in spreadsheets (D9 in #37). The app's research features send profile fields to model
   providers (see below), so using the app for a pilot applicant would break rule 1.

## Services that could see data

| Service | Used for | What it would see | Pilot status |
|---|---|---|---|
| Perplexity (Sonar API) | App research gateway (recommendations, school/funding dossiers, professor synthesis) | **Profile fields** in the app's prompts (below) plus program queries | Program-only queries allowed; no applicant data |
| OpenAI-compatible deep-research provider (`OPEN_DEEP_RESEARCH_*`) | Fallback research provider in the app | Same as Perplexity | Same as Perplexity |
| Groq / OpenAI | LLM extraction of program pages and profile parsing in the app | Program web pages; uploaded documents if document parsing is enabled (it is gated off, #69) | Program pages only |
| OpenAlex, Semantic Scholar | Professor and publication data | Professor and institution names | No applicant data involved |
| General-purpose AI assistants (any chat assistant used by the advisor) | Drafting, summarising | Whatever is pasted in | **Do not paste applicant data.** Program facts only |
| Spreadsheet / drive provider `<OWNER TO CONFIRM>` | Pilot storage | All pilot records | Allowed (the storage location in `data-handling.md`) |
| Waitlist form tool (Tally, #79) | Early-access sign-ups | Sign-up answers | Allowed, as stated on the waitlist page |
| Email provider | Contacting applicants | Messages | Allowed |
| Payment provider `<OWNER TO CONFIRM>` | Collecting the pilot fee | Payment details | Allowed. Card data never touches Guidr |

### What the app's prompts send today (for later, when the app is used with real applicants)

`guidr-backend/src/pipeline/orchestrator/dossier_nodes.py` loads the user's profile and fills the
templates in `guidr-backend/src/pipeline/prompts/templates/` with: intended degree level, field of
study, research areas, secondary fields, career goals, **GPA**, preferred countries and cities,
funding priority, program-style preferences and **country of citizenship**. Before the app is used
with any real applicant, either strip these fields from prompts, or obtain the consent in rule 1
and say so in the privacy page.

## If an applicant consents to a specific AI task

Record what was sent, to which service, on what date, and the applicant's written consent for
that task, in their private folder. Send the minimum fields the task needs.
