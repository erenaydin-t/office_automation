# Office Automation

An Iranian-style **office automation (اتوماسیون اداری)** application for the
[Frappe Framework](https://frappeframework.com) / ERPNext.

It implements the patterns that local Iranian organizations expect from a
"دبیرخانه / اتوماسیون اداری" system, while staying decoupled and standards
compliant so it can be dropped onto any Frappe v16 bench.

## Features

| Concept (FA) | Concept (EN) | Implementation |
|--------------|--------------|----------------|
| نامه / مکاتبات | Correspondence letter | **Automation Letter** (Submittable DocType) |
| ارجاع | Referral | **Document Referral** (tree-based ledger, not Frappe Workflow) |
| کارتابل | Unified inbox | **Inbox** Frappe Page + Vue 3 SPA |
| جانشینی / تفویض اختیار | Delegation | **Delegation Rule** + permission hooks |
| هامش‌نویسی | Margin notes / endorsements | Thread Print Format (Jinja + `get_pdf`) |

## Notifications, SLA & administration

- **Multi-channel notifications** — every referral fires a bell `Notification Log`,
  and (toggleable) a `ToDo` assignment, an email, and a realtime
  `oa_inbox_update` event that live-refreshes the Cartable.
- **Overdue SLA** — a daily scheduled job flags open referrals older than
  *Overdue After (Days)* and can send a reminder. Surfaced via the `is_overdue`
  field and the **Overdue Referrals** number card.
- **Office Automation Settings** — a singleton controlling ToDo / email /
  realtime / overdue behavior.
- **Workspace** — module landing page with three number cards (Unseen / Pending
  / Overdue) plus shortcuts and link cards.
- **Fixtures** — the two custom roles are exported as fixtures; standard records
  (DocTypes, Page, Print Format, Workspace, Number Cards) travel as module files.
- **CI & pre-commit** — GitHub Actions runs `ruff` lint/format + Frappe v16
  tests; `.pre-commit-config.yaml` wires `ruff` and `prettier`.

## Architecture highlights

- **Tree-based referral engine** — `Document Referral` rows reference each other
  via `parent_referral`, forming an Erja tree per document instead of a linear
  Frappe Workflow. See `forward_document()` and `get_referral_tree()`.
- **Delegation-aware permissions** — `permission_query_conditions` and
  `has_permission` hooks let an active *Delegatee* transparently inherit the
  *Delegator's* access to `Automation Letter` and `Document Referral`.
- **Decoupled DMS readiness** — attachments and archive links use Dynamic Links,
  so an external repository (e.g. **Lyra DMS**) can be attached without coupling
  the schema.

## Installation

```bash
# on an existing bench (Frappe v16+)
bench get-app office_automation /path/to/office_automation
bench --site your-site.local install-app office_automation
bench --site your-site.local migrate
bench build --app office_automation
```

## Development

```bash
bench --site your-site.local clear-cache
bench --site your-site.local console
```

## License

MIT
