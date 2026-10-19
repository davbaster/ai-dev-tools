# MCP Server Lab Course — MVP Plan

## Product boundary

Build one free online course for beginners who are new to MCP and APIs. It is a single-course product, not a multi-course platform or public MCP-server hosting service.

Learners build a Python MCP personal-notes server with create, list, read, update, and delete tools. Notes use the preconfigured SQLite database inside each isolated learning container. The course is passed with a final score of **80% or higher**.

## Learner access and dashboard

- Free self-enrollment with username and password.
- Secure HTTP-only session-cookie authentication. Password recovery is out of scope.
- Visitors can preview the entire first chapter but cannot use a lab without an account.
- The learner dashboard shows progress, current score, and a **Resume chapter** action. Only that learner can view their progress and score.
- Detect browser language and provide a language switcher. Lessons, walkthroughs, quizzes, hints, and lab UI have English and Spanish parity.
- Recommend, but do not require, [CS50's Introduction to Programming with Python](https://cs50.harvard.edu/python/) and present a readiness checklist before Chapter 1.

## Course and labs

Learners unlock chapters sequentially. To unlock the next chapter, they must finish every walkthrough and submit every graded item.

1. **Foundations:** MCP client/server roles and FastMCP basics.
2. **Tools:** Build and validate the notes CRUD tools.
3. **stdio:** Run and connect the server through `stdio`.
4. **Streamable HTTP:** Expose and test the server over Streamable HTTP.

Lessons are minimal-reading interactive walkthroughs: first a separate simulation, then live guidance that highlights and validates actions in the actual lab. The lab also includes a concise offline FastMCP/MCP reference.

Each chapter starts with a prepared Python starter project containing TODOs. The responsive browser lab includes a code editor, file tree, terminal, and built-in simulated MCP client; it must support desktop, tablet, and phone, including terminal and code editing on phones. The simulated client provides both a chat-like exploration view and a structured parameter-and-results test panel.

- One active isolated container per learner.
- No internet access in containers; packages, starter code, and reference material are preinstalled.
- The container stops after 15 minutes idle. Reopening restarts from that chapter's starter project; drafts are not restored.
- Before a chapter environment resets, automatically offer a ZIP download of the learner's completed code.

## Assessment

- Per chapter: 3 multiple-choice questions and 2 lab tasks (12 questions and 8 lab tasks total).
- Final score: questions 30%; lab tasks 70%. Each item within its group has equal weight.
- The frontend sends answers, submissions, and check results to the backend for persistence.
- Unlimited practice is available. Visible practice checks are exactly the checks used for the one final graded attempt.
- Show the correct answer and explanation immediately after a final attempt.
- A learner at 80% or higher receives passed status and final score only; there is no certificate or public verification link.
- A learner below 80% can reset all graded attempts and retake the course.
- Explain briefly that LLM use for graded work undermines learning; do not use technical blocking.

## Application architecture

- **Frontend:** React, TypeScript, Vite.
- **Backend:** Python, FastAPI.
- **Database:** PostgreSQL stores accounts, enrollment, progress, answers, grades, feedback, and incident records.
- **Deployment:** one Docker-based server/VM, initially sized for three active learners.
- **Staging:** an isolated Docker Compose project and ports on the same server; it never replaces production.

The frontend and backend communicate only through the backend API. REST covers accounts, enrollment, content, progress, assessment, feedback, downloads, and protected operations settings. WebSockets cover terminal I/O and live lab events.

### API contract

- FastAPI generates `openapi.yml` and `/openapi.json`; commit the generated YAML with every backend API change.
- Generate and commit a TypeScript API client from `openapi.yml`; React uses this client instead of handwritten REST calls.
- Do not use an API URL version prefix in v1.
- Expose FastAPI interactive API documentation at `/docs` as well as `/openapi.json`.

## Feedback on every page

Every page contains **Send feedback / report an issue** with categories: bug, confusing lesson, lab problem, and suggestion. The learner sees submission confirmation only; feedback status tracking and email notices are out of scope.

Automatically collect page URL, selected language, timestamp, browser/device details, browser-console errors, and recent application events. Redact passwords, session tokens, answer text, and all other personal data before diagnostics are stored or sent to automation.

### Feedback triage

- A guarded on-call LLM engineer reviews feedback immediately by default. A protected settings page can switch to hourly or manual-only review; deployment configuration is the fallback.
- Eligible low-risk fixes are limited to documentation, translations, UI copy, and isolated display bugs.
- Broad, uncertain, unsafe, or failed work creates a GitHub issue with redacted evidence and proposed next steps for a human on-call engineer.

## Monitoring and operational incidents

Use Prometheus-compatible metrics and Grafana alerting. Grafana sends webhooks directly to an authenticated incident-triage service.

Initial **critical** alerts cover:

- Application unavailable or health-check failure
- HTTP 5xx errors
- Sustained CPU or memory pressure
- Slow API responses
- PostgreSQL connection failures
- Lab-container start, health, and runtime failures

Warnings are recorded but do not start the LLM engineer. Critical alerts do. For each critical alert, the triage service writes a redacted JSON incident record containing alert details, affected service, metric values, dashboard link, and recent redacted logs. Retain incident JSON and evidence for 30 days.

### Incident-response workflow

1. Grafana posts a critical alert to the triage service.
2. The service validates the webhook, writes redacted JSON, and starts the on-call LLM engineer.
3. The LLM diagnoses the issue with approved repository and staging access and may prepare a small fix.
4. The system builds, tests, and smoke-tests the fix in staging. Any failure stops promotion.
5. A human approves a GitHub pull request before production deployment.
6. If the LLM escalates or staging fails, it creates a GitHub issue with redacted evidence and next steps. This is when the human on-call engineer is notified.

No automatic fix may deploy directly to production. The staging-and-human-approval rule supersedes prior automatic-deployment ideas.

## Exclusions for v1

- Multiple courses, instructor enrollment, paid checkout, certificates, public score verification, and authoring CMS.
- Instructor or administrator views of learner progress or scores.
- Draft restoration after container stop; shared or internet-enabled containers; more than one active container per learner.
- Full accessibility-compliance work, password reset, feedback status tracking, and email notifications.
- Automatic production deployments by the on-call LLM engineer.

## Acceptance criteria

1. A learner can self-enroll, use either language, complete all four chapters, and build the CRUD notes server over `stdio` and Streamable HTTP in an offline isolated lab.
2. All 20 graded items persist correctly; the 30/70 score, 80% pass threshold, sequential unlock, one final attempt, and retake reset behave as specified.
3. React uses the committed generated client, and `openapi.yml`, `/openapi.json`, and `/docs` match FastAPI behavior.
4. Every page accepts redacted feedback and an escalation creates a useful GitHub issue without learner secrets or answers.
5. Every listed critical alert creates a redacted 30-day incident JSON record and starts the LLM workflow; a staged fix cannot reach production without human GitHub PR approval.
