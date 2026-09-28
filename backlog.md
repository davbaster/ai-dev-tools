# Household Chores Backlog

A small, ordered backlog for implementing the shared household chores scope in Django. The existing project uses the `chores` app, SQLite, and Django templates.

## 1. Model households and members

**Priority:** Must have

Create models for `Household` and `Member` with:

- Household name and unique invite code
- Member display name
- Household membership
- No password or real authentication in the MVP

**Done when:** A household can contain named members and a new member can join using a valid invite code.

## 2. Model chores and recurring settings

**Priority:** Must have

Create a `Chore` model with:

- Name and description
- Point value
- Due date
- Recurrence: one-time, daily, weekly, or monthly
- Status or status derived from assignment/completion timestamps
- Claimant
- Created and updated timestamps

Add validation so points are positive and recurrence values are valid.

**Done when:** Migrations apply successfully and the Django admin can create and edit representative chores.

## 3. Model completion and verification history

**Priority:** Must have

Create a completion record that stores:

- Chore and completing member
- Completion timestamp
- Verifying member and verification timestamp
- Awarded points
- Reopened state or a clear completion status

Enforce that a member cannot verify their own completion.

**Done when:** The data model preserves who completed, who verified, when it happened, and how many points were awarded.

## 4. Add sample household and seed data

**Priority:** Must have

Provide a repeatable seed command or fixture that creates a sample household with named members and chores covering:

- Available
- Claimed
- Awaiting verification
- Verified
- Overdue

Load this data automatically on the first prototype visit, without duplicating it on later visits.

**Done when:** A fresh local setup opens with a populated household that demonstrates every important status.

## 5. Build the dashboard and chore list views

**Priority:** Must have

Add URL routes, views, templates, and shared styling for:

- Dashboard with today's chores, overdue chores, weekly points, rankings, and reminders
- Chore list with status filters
- Chore detail page

Keep the layout responsive and neutral/practical, with status and next actions easy to scan.

**Done when:** A user can navigate from the dashboard to the list and then to any chore detail.

## 6. Implement the claim, complete, verify, and reopen workflow

**Priority:** Must have

Add POST actions with CSRF protection for:

- Claiming an available chore
- Marking a claimed chore complete
- Verifying another member's completion and awarding points
- Reopening a verified chore as the verifier

Keep overdue chores assigned to their claimant.

**Done when:** The complete workflow works through the UI and points appear only after verification.

## 7. Add weekly fairness calculations and in-app reminders

**Priority:** Should have

Implement query helpers or service functions for:

- Current-week points per member
- Weekly ranking with deterministic tie handling
- Due-soon and overdue reminders
- Full completion history with dates, users, and points

**Done when:** The dashboard shows the current week's totals and ranking, and reminder states are visible without email or browser notifications.

## 8. Add focused tests and responsive acceptance checks

**Priority:** Must have

Add Django tests for:

- Invite-code joining and member creation
- Chore validation and recurrence values
- Claim, completion, verification, and reopen transitions
- No points before verification
- No self-verification
- Overdue chores remaining assigned
- Weekly point totals and ranking reset behavior

Manually verify the three MVP screens at desktop and mobile widths.

**Done when:** `uv run python manage.py test` passes and every MVP acceptance criterion in `_docs/plan.md` can be demonstrated.

## Deliberately Deferred

- Real authentication and password recovery
- Email, browser, or push notifications
- Notes, photos, badges, rewards, and point redemption
- Automatic assignment rotation
- Custom date-range analytics
- Separate roles and permissions
- Production deployment and a full backend hardening pass
