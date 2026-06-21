# Changelog

All notable changes to this project are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [0.2.4] - 2026-06-21

### Added
- **Delegation Rule desk page** now uses the Office Automation template look
  (Vazirmatn, card-style sections, soft shadows, rounded controls, blue primary).
  Applied only to Delegation Rule's form and list via self-contained client
  scripts — no other ERPNext page is affected, and it follows light/dark + RTL.

## [0.2.3] - 2026-06-21

### Reverted
- **Rolled the UI back to the v0.2.2 design** (the full polished panel that
  matches the approved template). The v0.3.x "integration" rewrites (in-page
  panel, plain forms, theme refactors) are reverted — they introduced errors and
  diverged from the template.

### Changed
- The Office Automation app icon opens **/app/inbox** directly.

## [0.2.2] - 2026-06-20

### Fixed
- **Root cause of the recurring "You need the create permission" error.** The
  `has_permission` hook returned `None` for the create / privileged / new-doc
  cases. Frappe treats a non-`True` controller-hook result as a denial once the
  role grant has passed (only `Administrator` short-circuits), so even users with
  the Office Automation User/Manager **or System Manager** role were blocked from
  creating letters and referrals. The hook now returns `True` to allow and
  `False` to deny — never `None`. This also lets privileged role users open
  letters again.

## [0.2.1] - 2026-06-20

### Fixed
- CI test `test_oa_user_can_create_letter` failed because the fixture user was a
  Website User (desk DocType permissions don't apply). `ensure_oa_user` now
  creates a **System User** and clears its cache so role permissions take effect.

### CI
- Cache uv / yarn / pip / npm downloads and enable pip cache to speed up runs.

## [0.2.0] - 2026-06-20

### Added
- **Office Automation Panel** — a full RTL Persian SPA matching the approved
  design: top app bar, right nav drawer, and four screens (Dashboard with
  greeting + stat cards + quick access + pending list, Cartable with folder
  rail, Letters list, and a Letter view with the referral-flow timeline,
  attachments and approve/reject/forward actions) plus the compose modal.
  Includes light/dark theme toggle, Vazirmatn font and Material Symbols icons.
- New endpoints `get_dashboard_stats` and `get_letter_detail`.
- The `/app/inbox` page now mounts this panel (`OaPanel.vue` + `panel.css`).

## [0.1.6] - 2026-06-20

### Security
- **Cartable folder endpoints leaked other users' data.** `get_letters_by_visibility`
  used `frappe.get_all` (no permission filter), exposing every private/confidential
  letter to any user; it now uses `frappe.get_list` so permission rules apply.
  `get_outbox_items`, `get_drafts`, and `get_folder_counts` accepted an arbitrary
  `user` argument with no authorization check — they now route through the guarded
  `_recipients_for` resolver (matching `get_inbox_items`), rejecting requests for
  another user's data. Added a regression test.

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

[0.2.4]: https://github.com/erenaydin-t/office_automation/releases/tag/v0.2.4
[0.2.3]: https://github.com/erenaydin-t/office_automation/releases/tag/v0.2.3
[0.2.2]: https://github.com/erenaydin-t/office_automation/releases/tag/v0.2.2
[0.2.1]: https://github.com/erenaydin-t/office_automation/releases/tag/v0.2.1
[0.2.0]: https://github.com/erenaydin-t/office_automation/releases/tag/v0.2.0
[0.1.6]: https://github.com/erenaydin-t/office_automation/releases/tag/v0.1.6
[0.1.5]: https://github.com/erenaydin-t/office_automation/releases/tag/v0.1.5
[0.1.4]: https://github.com/erenaydin-t/office_automation/releases/tag/v0.1.4
[0.1.3]: https://github.com/erenaydin-t/office_automation/releases/tag/v0.1.3
[0.1.2]: https://github.com/erenaydin-t/office_automation/releases/tag/v0.1.2
[0.1.1]: https://github.com/erenaydin-t/office_automation/releases/tag/v0.1.1
[0.1.0]: https://github.com/erenaydin-t/office_automation/releases/tag/v0.1.0
