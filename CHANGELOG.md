# Changelog

All notable changes to this project are documented here.
The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [0.4.2] - 2026-07-01

### Changed
- **Renamed the referral-note label «هامش‌نویسی» → «توضیحات ارجاع»** everywhere it
  is user-facing: the Cartable referral popup, the desk form fields on Document
  Referral and the letter recipient row, the desk-form dialogs, and the thread
  print output. This is a label-only change — the underlying `instruction` field
  is unchanged, so no data migration and no existing notes are affected. (The
  Approve/Reject/Return note field keeps its «یادداشت» label.) Desk-form/print
  labels take effect after `bench migrate`.
- **Custom themed "ارجاع" (Erja) modal.** The new-referral popup no longer uses
  the stock `frappe.ui.Dialog`; it is a themed Vue modal (`OaReferForm.vue`)
  matching the compose window — RTL, app fonts/colors, `OaUserChips` recipient
  picker, segmented referral-type selector, «توضیحات ارجاع» note, and dropzone
  attachment. It can now refer to **several recipients at once** (one referral
  per recipient under the same parent).

## [0.4.1] - 2026-06-30

### Fixed
- **Security: a sender could action the referral they sent.** `approve_referral`,
  `reject_referral`, `return_referral` and `mark_referral_actioned` gated on a
  generic `write` permission, which the delegation `has_permission` hook also
  grants to the sender/owner — so a sender could forge an outcome and dismiss the
  item from the recipient's inbox before they ever saw it. `_get_own_referral`
  now requires the caller to be the **recipient or one of the recipient's active
  delegates** (`recipient in get_effective_users(session_user)`); senders are
  explicitly blocked. Added `test_sender_cannot_action_own_referral`.

## [0.4.0] - 2026-06-30

### Added
- **"Return" (عودت) action for incoming letters.** Alongside تأیید/رد (Approve/
  Reject), a recipient can now return a referral to its sender for revision.
  It closes the recipient's inbox item (status `Actioned`) and records the new
  `Returned` outcome, then notifies the sender — same proven path as approve/
  reject (`return_referral` in `document_referral.py`).
- **"Returned" Outbox folder** in the Cartable SPA so senders can see every
  letter that was returned to them (`get_outbox_items`/`get_folder_counts`
  state `returned`), plus a distinct blue `reply` marker in the referral tree.
- **"Returned Letters" desk list** — a workspace shortcut opening Document
  Referral filtered to `outcome = Returned`.

## [0.3.2] - 2026-06-28

### Changed
- **Editor font dropdown is now an all-free OFL set (10 fonts).** Replaced the
  proprietary entries (IRANSans, B-series, Tahoma) with self-hosted SIL OFL
  fonts so every option renders everywhere without a client install:
  **Vazirmatn, Shabnam, Estedad** (≈ IRANYekan/IRANSans), **Sahel, Samim,
  Tanha** (≈ Nazanin), **Gandom, Parastoo, Nahid, Lalezar** (display ≈ Titr).
  All woff2 are bundled under `public/fonts/` and declared in `oa_fonts.css`.

## [0.3.1] - 2026-06-28

### Added
- **Bundled free Persian fonts (Vazirmatn, Shabnam).** Self-hosted the two
  genuinely-free (SIL OFL) fonts from the editor's list under
  `public/fonts/` with `@font-face` (`oa_fonts.css`, imported into the SPA
  bundle), so they render in the editor and the letter read view on every
  machine — no client install needed.

### Notes
- The other requested fonts are **not** free to redistribute, so they are not
  bundled: **IRANSans** (IRANSansWeb requires a fontiran.com license), the
  **B-series** (B Nazanin/Yekan/Roya/Koodak/Titr/Mitra — © Borna Rayaneh; the
  "free download" sites are piracy mirrors), and **Tahoma** (Microsoft system
  font). They remain in the dropdown referenced by name (render where installed).
  To bundle them legally, provide licensed `woff2`/`ttf` files; or we can add
  free OFL look-alikes (Sahel, Samim, Tanha, Estedad, …).
- PDF font embedding (wkhtmltopdf) needs the fonts installed in the image — a
  separate step from this SPA bundling.

## [0.3.0] - 2026-06-28

### Added
- **New WYSIWYG editor (TipTap).** Replaced the letter composer's Quill control
  with a TipTap-based `OaEditor.vue` (MIT-licensed, native Vue 3, native RTL).
  Toolbar: **Font Family** dropdown (10 Persian fonts — Vazirmatn, Shabnam,
  IRANSans, B Yekan/Nazanin/Roya/Koodak/Titr/Mitra, Tahoma), font size, bold/
  italic/underline/strike, text color, heading, bullet/ordered lists, quote,
  alignment, link, clear-format, undo/redo. New app-level `package.json` pins the
  TipTap deps (installed at image build).

### Notes
- Fonts are **referenced by name, not bundled**: each renders only where the
  user has it installed, and **not in server-generated PDFs**. To make a font
  appear everywhere (incl. PDF), send the `woff2`/`ttf` files and we'll self-host
  + bake them into the image.
- Deploy needs the npm deps installed (`yarn` in the app) + `bench build`, so the
  editor change should land via an **image rebuild** (not a runtime asset patch).

## [0.2.19] - 2026-06-28

### Changed
- **Default letter type is now configurable, not hardcoded.** The previous
  hardcoded «نامه داخلی» default didn't apply on sites that rename their Letter
  Types (e.g. «1-نامه داخلی»), so nothing was pre-selected. Added a **Default
  Letter Type** field to *Office Automation Settings*; `Automation Letter.before_insert`
  applies it to new letters (covers SPA, desk, and API), and the composer
  pre-selects it via the whitelisted `get_default_letter_type`. Fresh installs
  seed it to the seeded Internal type when present; sites with renamed types just
  pick their own value in Settings. Removed the hardcoded field/composer defaults.

## [0.2.18] - 2026-06-28

### Fixed
- **Draft edit could wipe the draft on a load error.** If `get_letter_for_edit`
  failed, the composer stayed open empty and saving rebuilt the child tables
  from the blank form; it now surfaces the error and closes instead.
- **Editing a draft no longer drops per-recipient data.** The composer now
  round-trips each recipient's `action_type`/`instruction` and keeps their
  individual `referral_type` (unless the type selector is changed), instead of
  flattening to one type and clearing the rest.
- **Recall is no longer rolled back by a cleanup hiccup.** `Document Referral.on_trash`
  guards the ToDo/notification cleanup so a failure there can't abort the recall
  transaction (matching its best-effort contract).
- **Editing an old-dated draft no longer silently resets the date.** `OaSegmented`
  only emits on a real change, so re-clicking the active date option is a no-op.
- **Stale default Letter Type can't block letter creation.** `create_letter` /
  `update_letter` drop a `letter_type` that no longer exists rather than failing
  Link validation.

### Changed
- Deduplicated the realtime Cartable-refresh into `_publish_inbox_update()`
  (was repeated in three notify paths), the two SPA recall handlers into a shared
  `runRecall()`, and the create/update letter tail into `_finalize_letter()`.

## [0.2.17] - 2026-06-28

### Changed
- **Jalali auto-enable is now one-time.** The initial migrate enables Jalali and
  records a global flag (`office_automation_jalali_initialized`); subsequent
  migrations are a no-op, so an admin who later disables Jalali (or changes week
  start/end) is no longer overridden on the next `bench migrate`.

## [0.2.16] - 2026-06-28

### Changed
- **persian_calendar is now a required app.** This module targets Persian
  (Jalali) deployments, so `persian_calendar` is declared in `required_apps`
  (installed automatically and migrated before this app).
- **Jalali calendar auto-enables on migrate.** `after_install` / `after_migrate`
  now switch **Jalali Settings** on (Default Calendar = Jalali) when it has not
  been enabled yet, so fresh deployments show Persian dates with no manual step.
  It only flips a *disabled* setting on — an admin's week start/end tweaks are
  left untouched. Best-effort and guarded, so migrate never fails over it.

## [0.2.15] - 2026-06-28

### Changed
- **Persian (Jalali) dates in the Thread print format.** Integrated with the
  [persian_calendar](https://github.com/sfarbod/persian_calendar_ERPNext)
  app. Frappe desk list views / forms / reports are converted to Jalali
  automatically by that app's desk JS once it is enabled, but **print formats
  are not** (it keeps server-side formatting Gregorian on v16). The Automation
  Letter Thread print format now renders the letter date and each referral's
  creation / actioned timestamps via the app's `toshamshi()` Jinja helper with
  Persian digits. A `toj` shim falls back to the stock Gregorian formatter when
  persian_calendar is not installed, so the print format still works standalone.

### Notes
- The Cartable SPA already shows Jalali dates (it formats via
  `Intl.DateTimeFormat("fa-IR")`); stored dates remain Gregorian. To enable
  Jalali everywhere else: install + migrate persian_calendar, then in **Jalali
  Settings** tick *Enable Jalali Calendar* and set *Default Calendar = Jalali*
  (`bench build` + `clear-cache` + `restart`). See the deploy notes in the PR.

## [0.2.14] - 2026-06-28

### Changed
- **Default letter type for new letters.** New letters now default to the
  Internal type «نامه داخلی» (the seeded `Internal` Letter Type). Applied at
  every entry point: the `letter_type` field default on **Automation Letter**
  (desk form / `new_doc`), the SPA composer's pre-selected type, and a
  `create_letter`/`update_letter` fallback so the default still applies when a
  caller omits the type. Editing an existing letter keeps its own type.

## [0.2.13] - 2026-06-28

### Fixed
- **Attachment upload stuck on "loading".** `OaDropzone` pushed a raw file entry
  into the reactive `files` array but then mutated the *raw* reference inside
  `upload()`. In Vue 3 those mutations bypass the reactive proxy, so the row's
  `uploading` flag never re-rendered — the spinner spun forever (even when the
  file had actually uploaded) and the success check never appeared. The upload
  now updates the entry **through** the reactive array (looked up by `uid`).
  Also hardened the handler to check `res.ok` / a missing `file_url` and surface
  the real server error (`_server_messages`) instead of failing silently.

## [0.2.12] - 2026-06-28

### Fixed
- **Draft letters were not editable.** The SPA could create and save drafts but
  offered no way to edit them — clicking a draft opened the read-only letter
  view, the composer always *created* a new letter, and there was no update
  endpoint. Drafts could only be edited from the raw Frappe desk form (and a
  letter recalled back to Draft was therefore stuck). The composer now has an
  edit mode: clicking a draft (or the new **ویرایش** button on a draft letter
  view) opens it pre-filled, and saving updates it in place — including
  re-sending it.
  - New whitelisted endpoints `get_letter_for_edit` and `update_letter`
    (draft-only; rebuilds the recipient/CC/attachment rows). `create_letter` was
    refactored to share the payload logic (`_apply_letter_payload`).
  - `OaDropzone` now seeds from its `modelValue`, so existing attachments show on
    edit and are preserved on save instead of being wiped.

## [0.2.11] - 2026-06-28

### Added
- **Recall sent letters (بازپس‌گیری).** The sender can unsend a letter while
  recipients have not opened it yet. A **بازپس‌گیری** button on the letter view
  (and a per-recipient action in the referral flow) pulls the letter back from
  every recipient whose referral is still *Unseen*; recipients who already
  opened it keep their copy. When *no one* has opened it, the letter fully
  reverts to an editable **Draft** so it can be amended and re-sent.
  - New whitelisted endpoints `recall_letter` and `recall_referral`
    (sender-only). Recalling a referral now cleans up its ToDo + bell
    notifications and live-refreshes the recipient's Cartable
    (`Document Referral.on_trash`).
  - `get_letter_detail` exposes `is_sender`, `can_recall`, `unseen_count`, and a
    per-referral `can_recall` / `seen_on` so the UI can offer recall only when
    valid.

## [0.2.10] - 2026-06-22

### Fixed
- **Dark mode gaps.** The composer modal and its components (chips, segmented
  controls, dropzone) use the `.oa-ui` token set, which had no dark variant, so
  they stayed light in dark mode. Added a dark token block (applied when the
  panel is dark) and replaced a few hardcoded light colors in the New Letter
  form (error box, toggle track) with theme variables.

## [0.2.9] - 2026-06-21

### Changed
- **Erja (forward) dialog**: نوع ارجاع is now a Persian select
  (دستور/پیگیری/اقدام/استحضار/اطلاع, mapped back to the stored values), and you
  can **attach a file** with the referral (new `attachment` field on Document
  Referral).
- **New Letter form**: نوع نامه is now a segmented control (same UX as محرمانگی)
  instead of a dropdown.

## [0.2.8] - 2026-06-21

### Added
- **Responsive panel** (ported from the `ui/` design). Below 860px: off-canvas
  nav drawer with a burger toggle + scrim, the top search & profile text hide,
  the dashboard grids collapse (4→2→1 cols), the inbox folder pane hides,
  toolbars/headers wrap, the letters table scrolls horizontally, and the letter
  view goes single-column. Implemented via `data-r` markers + media queries in
  `panel.css` (scoped to `.oa-panel`).

## [0.2.7] - 2026-06-21

### Fixed
- **Workspace `type` was null** (now mandatory) — set to `Workspace` so the
  workspace re-imports without `MandatoryError`.
- **Inbox redirect moved to the routing layer.** Added `oa_router.js`
  (app_include_js): when the Office Automation workspace is opened it routes to
  `/app/inbox` via `frappe.router` (not swallowed like the old in-content-block
  hack); admins can still open the workspace cards with `?noredirect=1`.
- Idempotent patch `v0_2.remove_inbox_redirect_hack` deletes the old runtime
  artifacts (the "OA Inbox Redirect" Custom HTML Block and any redirect content
  block) from existing sites. Added workspace-routing tests.

## [0.2.6] - 2026-06-21

### Added
- **Automation Letter (نامه اتوماسیون) desk page** now uses the Office Automation
  template look (Vazirmatn, card-style sections, soft shadows, rounded controls,
  blue primary) on both its form and list — scoped to Automation Letter only.

## [0.2.5] - 2026-06-21

### Changed
- `.oa-panel` now uses `display: contents` (removed the root's inline
  `position:fixed`/`display:flex`) so the inbox panel flows within the page
  instead of as a full-screen overlay.

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

[0.2.10]: https://github.com/erenaydin-t/office_automation/releases/tag/v0.2.10
[0.2.9]: https://github.com/erenaydin-t/office_automation/releases/tag/v0.2.9
[0.2.8]: https://github.com/erenaydin-t/office_automation/releases/tag/v0.2.8
[0.2.7]: https://github.com/erenaydin-t/office_automation/releases/tag/v0.2.7
[0.2.6]: https://github.com/erenaydin-t/office_automation/releases/tag/v0.2.6
[0.2.5]: https://github.com/erenaydin-t/office_automation/releases/tag/v0.2.5
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
