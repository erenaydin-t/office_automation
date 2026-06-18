# Changelog

All notable changes to this project are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [0.1.5] - 2026-06-18

### Added
- One-time patch `grant_oa_user_role` that grants the **Office Automation User**
  role to all active System Users, so creating/receiving letters works out of
  the box. (Remove the role from individual users to restrict access.)

### Note
- The v0.1.3 create-permission fix only takes effect after a `bench restart`
  (the web worker must reload the updated permission hook).

## [0.1.4] - 2026-06-18

### Fixed
- `persianize_masters` patch crashed on Frappe v16 with
  `rename_doc() got an unexpected keyword argument 'ignore_permissions'`.
  Removed the unsupported kwargs; the patch runs as Administrator and the
  masters allow rename.

## [0.1.3] - 2026-06-18

### Fixed
- **Create permission bug:** the delegation `has_permission` hook denied *new*
  Automation Letters/Referrals (no name/owner/sender yet), so even users with
  the Office Automation User role got "You need the create permission". Creation
  and amend now defer to role permissions. Added a regression test.

### Docs
- Persian manual: added the "create permission" fix (how to grant the role,
  including a bulk-assign console snippet) and a step-by-step guide to the modern
  New Letter modal.

## [0.1.2] - 2026-06-18

### Fixed
- Corrected the patch module path in `patches.txt`
  (`office_automation.patches…`), which caused a `ModuleNotFoundError` during
  `bench migrate`.

### Changed
- Full Persian localisation: `fa.csv` now translates every DocType name, field
  label, Select option, workspace/menu label, role, and action button. With the
  user/site language set to فارسی, the whole app appears in Persian.

## [0.1.1] - 2026-06-17

### Changed
- Default **Letter Type** and **Action Type** master values are now Persian
  (نامه وارده/صادره/داخلی/بخشنامه and جهت بررسی/اقدام/اطلاع/تأیید، پیگیری شود،
  بایگانی شود). A post-migrate patch renames the previous English masters on
  existing sites; all links update automatically.

## [0.1.0] - 2026-06-17

First feature release on **Frappe v16** (Python 3.14 · Node 24).

### Added
- **Core model** — Automation Letter (submittable), Letter Type & Action Type
  masters, Document Referral (tree-based Erja engine), Delegation Rule.
- **Internal send** — Recipients (گیرندگان) and CC (رونوشت) tables; submitting a
  letter delivers a root referral to each recipient's Cartable.
- **Cartable navigation** — Vue 3 SPA with sidebar folders: Inbox by referral
  type (Order/Follow-up/Action/Notification/Info), Outbox by state
  (In Progress/Approved/Rejected), plus Search, YIC, Drafts, Private/Public,
  Settings — backed by dedicated whitelisted folder APIs.
- **Classification** — Confidentiality and Urgency, Private flag, with UI
  highlighting.
- **Approve / Reject** outcomes that drive the sender's Outbox folders.
- **Modern UI** — design-token theme (soft shadows, whitespace, light palette),
  Lucide-style icons, segmented controls, chip/tag inputs, drag-and-drop
  dropzone, and a New Letter modal with a WYSIWYG body and Vue transitions.
- **Delegation-aware permissions** via `permission_query_conditions` /
  `has_permission` hooks.
- **Notifications & SLA** — bell / ToDo / email / realtime fan-out, overdue
  daily job, and Office Automation Settings singleton.
- **Thread printing** — Jinja print format rendering the letter plus the full
  referral tree (هامش‌نویسی), `get_pdf`-compatible.
- **Desk integration** — Workspace with number cards + shortcuts, apps-screen
  icon, auto-created on install/migrate.
- **DMS readiness** — Dynamic-Link archive fields (e.g. Lyra DMS).
- **Tooling & docs** — fixtures for roles, GitHub Actions CI, ruff + prettier
  pre-commit, Persian translations (fa.csv), and a Persian user manual.

[0.1.5]: https://github.com/erenaydin-t/office_automation/releases/tag/v0.1.5
[0.1.4]: https://github.com/erenaydin-t/office_automation/releases/tag/v0.1.4
[0.1.3]: https://github.com/erenaydin-t/office_automation/releases/tag/v0.1.3
[0.1.2]: https://github.com/erenaydin-t/office_automation/releases/tag/v0.1.2
[0.1.1]: https://github.com/erenaydin-t/office_automation/releases/tag/v0.1.1
[0.1.0]: https://github.com/erenaydin-t/office_automation/releases/tag/v0.1.0
