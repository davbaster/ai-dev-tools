# Shared Household Chores

## Homework Scope

Build a clickable, responsive web prototype for tracking household chores and making each person's contribution visible and fair.

The primary success criterion is a simple, intuitive experience for adults and children.

## Target Users

- Adults and children in the same household
- Household members use a shared invite code to join
- Users identify themselves with a simple name; real authentication is out of scope for the prototype

## Core Product Behavior

1. A household member creates a one-time or recurring chore.
2. Chores include a name, description, point value, due date, and recurrence.
3. Recurrence options are daily, weekly, or monthly.
4. Unclaimed chores appear as available.
5. A household member claims an available chore.
6. The claimant marks the chore complete.
7. Another household member verifies the completion.
8. Points are awarded only after verification.
9. The verifier may reopen a completed chore.
10. Overdue chores remain assigned to the person who claimed them.

## Fairness Model

- Each chore has custom points based on its expected effort.
- The dashboard shows today's chores, overdue chores, and household point totals.
- Everyone can see all chore history and points.
- The primary fairness view is the current week.
- Weekly rankings reset every week.
- Completed history includes the date, completing user, verifying user, and points awarded.
- The product uses points and rankings only; no badges, rewards, or exchanges.

## MVP Screens

### 1. Home Dashboard

Show a balanced overview of:

- Today's available, claimed, completed, and overdue chores
- Current weekly points by household member
- Weekly ranking
- In-app reminders for chores that are due soon or overdue

### 2. Chore List

Support scanning and filtering chores by status, including:

- Available
- Claimed
- Completed and awaiting verification
- Verified
- Overdue

Users can claim available chores and open a chore's details.

### 3. Chore Details

Show the chore's name, description, points, due date, recurrence, claimant, and status. The prototype must demonstrate:

- Claiming an available chore
- Marking a claimed chore complete
- Verifying a completed chore
- Awarding points after verification
- Reopening a verified chore as the verifier

Creating and editing chores may be represented by a focused control or simplified interaction within the prototype; separate management screens are not required for the MVP.

## Permissions

All household members have the same permissions in the MVP:

- Create chores
- Edit chores
- Claim available chores
- Mark claimed chores complete
- Verify another person's completed chores
- View all household history and points

## Data and Prototype Assumptions

- The intended product uses a backend database so household data persists between sessions.
- The homework deliverable is a clickable frontend prototype, so the backend can be mocked or represented with local prototype state.
- Load a sample household on the first visit so the main workflow is immediately demonstrable.
- Use in-app notifications only for the prototype.

## Visual Direction

Use a neutral, practical interface that prioritizes clarity, scanning, and obvious status changes over playful or competitive decoration.

## Out of Scope

- Email, browser, or push notifications
- Real authentication and password recovery
- Mobile-native or desktop-native apps
- Notes, photos, or other completion attachments
- Badges, household rewards, or point redemption
- Custom date-range analytics
- Separate role permissions
- Automatic assignment rotation
- Returning overdue chores to the available pool
- Separate fairness screens beyond the current-week view
- A full production backend implementation

## MVP Acceptance Criteria

The prototype is complete when a reviewer can:

- Open the app and see a populated sample household
- Identify available, claimed, completed, verified, and overdue chores
- Claim an available chore
- Mark the claimed chore complete
- Verify the completion as another household member
- See points appear only after verification
- See the updated weekly ranking
- Reopen a verified chore as its verifier
- Understand the current week's household contribution without instructions
- Use the main experience at responsive desktop and mobile widths
