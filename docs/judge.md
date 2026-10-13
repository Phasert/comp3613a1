# student-judge competency report

**Judged at:** 2026-10-13 (second run — fresh evidence pass)
**Evidence pass:** re-read all six Guide chats (`docs/transcripts/Phase 1.md` … `Phase 5 part 1.md`, plus the live Phase 5 OpenCode continuation), current `docs/report.md` including the **deployed URL and YouTube link**, `docs/diagrams/`, `docs/wireframes/MyAdvisor.png`, the shipped `app/` routers, and the live site at `https://comp3613a1-d7i1.onrender.com/` (landing, `/login`, `/config` all respond). The previous scorecard was ignored; the Phase 6 gap it recorded is now fixed and has been dropped.
**Student / session:** Kyle Nagee (816046831) — COMP 3613 A1, MyAdvisor (OpenCode continuation of a Cursor-started Phase 5)
**Artifact:** Guide chats for this project (Cursor + OpenCode) packaged as `docs/transcripts/*.md`
**Phases in evidence:** 1–6 (COMP 3613 phases; never generic 0–5)

### Totals
| | Count / value |
|--|--|
| Metrics on rubric | 12 (M1–M12) |
| N/A (excluded) | 0 |
| Metrics scored | 12 |
| Scoreable max | 12 × 4 = 48 |
| Awarded total | **46 / 48** |
| **Overall (avg of scored)** | **3.83 / 4** |
| Impression mark | **19 / 20** (no `sincerity` block was ever logged, so overall × 20) |

## Scorecard

| ID | Metric | Score / 4 | In avg | Evidence |
|----|--------|----------:|:------:|----------|
| M1 | Phase discipline | 4 | yes | Phases 1–4 each ran in their own chat with a pause block ("Phase 1 done … Open a new chat"); all three Phase 5 workflows stayed in the implement chat as the skill allows. No app code before wireframes existed. Phase 6 deploy came **after** the polish rounds, which is the required order. |
| M2 | Problem framing | 4 | yes | Named the project ("3" → MyAdvisor) and three workflows in their own words ("create and track degree progress (student) / review student plan (advisor) / review advisor decision (student)"), then gave six entities and every property including domain detail ("Degree - degreeID, name, credits, faculty, requirements (5 core courses, 4 elective courses, etc)"). Engaged include/extend, sharing, theming, and the reject-then-resubmit case. |
| M3 | Decision ownership | 4 | yes | Renamed four use cases in their own words and caught a diagram defect: "the extend arrow is facing the wrong way for that one". Rejected a wrong Guide premise: "there is no Approved, Rejected, and Query on My Plans". Chose plan-owned degree over freezing the student's degree: "it shouldnt change the degree of an already submitted plan … especially when it already been reviewed". |
| M4 | Artefact-before-code | 4 | yes | Implementation follows the wireframe and ERD, and they demanded they keep doing so ("keeping the design of the wireframe modernize the advisor dashboard and review plan to align with the style of the student dashboard and create plan"). Every model change is recorded as a revision against the ERD rather than invented fresh. |
| M5 | Verification habit | 4 | yes | Ran and reported repeatedly with real observations and full console output, e.g. the `JSONDecodeError` paste and "i just refreshed the advisor dashboard and the plan i just reviewed has disappeared" — a real bug they found themselves. Never accepted a first dump. |
| M6 | Assignment fit | 4 | yes | Verified on this pass: **no `select(`/`db.exec(`/`session.query` in any router** (`app/routers/*.py` scan — the only match in `plans.py` is the word inside a comment). Routes → services → repositories → models holds, starter auth/sessions/seed reused, theme applied before build, and the app is deployed on Render with the seeded accounts. |
| M7 | Slice explanation | 3 | yes | Own-words domain reasoning is strong throughout ("the advisor submits the status changes to reviewed there isnt a approve and reject as an advisor approves and rejects each course"). Thin-route and model snippets completed by the student with `architecture_ok: yes`. Docked because `advisor_review_save` took three passes before the intent→boolean mapping was right, and that correction came from the Guide. |
| M8 | Prompt quality | 3 | yes | Phase-tagged openings, then very concrete mismatch notes ("remove Open the full thread", "remove the add year button", "the sidebar isnt going down the complete page"). Terse later prompts are fine once artefacts exist. |
| M9 | Response to pushback | 4 | yes | Roughly ten distinct polish rounds across the three workflows, each producing UI, workflow, or model changes — including two ERD revisions the student chose. No pushback was deflected. |
| M10 | Integrity | 4 | yes | No paste dumps, no assistant-voice turns, no "just apply this", no "ignore previous instructions". All answers informal and first-person. `python manage.py skills-verify` → **pass**, lock root matches. |
| M11 | Provenance continuity | 4 | yes | Every screen traces to their wireframe rows and every table to their ERD; the `waiting on assistance` status and the minor requirement rule both came from their descriptions. |
| M12 | Sincerity trajectory | 4 | yes | No suspicion was ever raised (0 `sincerity` blocks in any chat). No capability jump, no orphan artefacts. |

## Strengths
- **Domain decisions were theirs.** Per-course approval instead of a whole-plan decision, the "not submitted / pending / reviewed" status set, the assistance flow where the helping advisor only advises, and the minor rule (Level II −2, +2 minor courses) were all student-originated and survived into the shipped code.
- **They read the artefact and pushed back on it** — catching a reversed «extend» arrow in Phase 2 and correcting the Guide's assumption about My Plans statuses in Phase 4.
- **Heavy, sustained polish** with model consequences: `StudentPlan.degree_id`, `Advisor.user_id`, `QueryReview.kind`, `PlanCourse.type`/`level`/`decision`, `Degree.*_required`.
- **Real verification habits**: paste-the-traceback debugging, and finding the faculty-jump bug themselves.
- **Architecture held.** Student-authored route snippets never inlined SQL; the Guide's own bugs (`latest_plan_for_user` dropped, `state` NameError, `url_for` missing a path param, Jinja `autoescape` off) were agent-side and corrected without touching the layering.
- **Deployed and confirmed live** — `https://comp3613a1-d7i1.onrender.com/` serves the branded landing, login, and `/config`, with marker logins in the report and a walkthrough video linked.

## Gaps (priority order)
1. **One snippet needed three passes.** `advisor_review_save` was handed back over because it passed a string where the service expected a boolean, so "Save decisions" silently closed the review. It would have been caught by restating the handler's intent in one sentence before running it.
2. **Layer reasoning came from the Guide.** The student never said *why* a rule belongs in the service rather than the router or repository — the code is right, the explanation is thin.

## Phase gate status
| Phase | Status | Note |
|-------|--------|------|
| 1 | met | Project + three `Feature (user)` lines in the student's words. |
| 2 | met | UML PNG drafted from their include/extend, sharing and gap answers; they renamed four use cases and fixed an arrow direction. |
| 3 | met | Student-named entities/properties; one-to-one → one-to-many on `StudentPlan ↔ ReviewPlan` after the reject-and-resubmit pushback. |
| 4 | met | Wireframe read, model edits accepted, unclear workflows clarified (no redraw). |
| 5 | met | Theming, three workflows built, **ten polish rounds** with verify notes, UI/workflow fine-tunes and ERD revisions. Not a first-dump acceptance. |
| 6 | met | Deployed to Render — public URL live and verified this pass; marker logins and the walkthrough video are in `docs/report.md`. |

## Recommended next practice
Write the plan **state machine** in your own words before touching code next time: list every status a plan can hold (`not submitted` → `pending` → `waiting on assistance` → `reviewed`, plus `query` display), what moves it, and who may act in each state. Then diff your list against `PlanService.can_query`, `can_continue`, `continue_destination` and `AdvisorService.queue`. That is the one gap behind both #1 and #2 — your rules were right, they just lived only in code until something broke.

## Integrity note
- **Clean.** No laundering signals, no edited skills, `skills-verify` passes.

## Provenance flags
- None.

## Sincerity log summary
- Blocks found: **0** | max round: – | min/mean/final confidence: – | trend: – | cleared: n/a (never raised)

## Skips
- **Skips: 0/3 used** (from the Guide blocks in every phase). Nothing was skipped or assumed away.