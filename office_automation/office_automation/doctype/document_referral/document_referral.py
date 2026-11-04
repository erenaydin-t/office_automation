# Copyright (c) 2026, Milanpars and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

from office_automation.office_automation.permissions.delegation import get_effective_users, is_privileged

STATUS_DRAFT = "Draft"
STATUS_UNSEEN = "Unseen"
STATUS_SEEN = "Seen"
STATUS_ACTIONED = "Actioned"
OPEN_STATUSES = (STATUS_UNSEEN, STATUS_SEEN)

# Persian labels for referral outcomes, used in notifications.
OUTCOME_LABELS = {"Approved": "تأیید شد", "Rejected": "رد شد", "Returned": "عودت شد"}


class DocumentReferral(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		action_type: DF.Link | None
		actioned_on: DF.Datetime | None
		attachment: DF.Attach | None
		instruction: DF.SmallText | None
		is_cc: DF.Check
		is_overdue: DF.Check
		naming_series: DF.Literal["REF-.YYYY.-"]
		outcome: DF.Literal["Pending", "Approved", "Rejected", "Returned"]
		parent_referral: DF.Link | None
		recipient: DF.Link
		reference_doctype: DF.Link
		reference_name: DF.DynamicLink
		referral_type: DF.Literal["Order", "Follow-up", "Action", "Notification", "Info"]
		seen_on: DF.Datetime | None
		sender: DF.Link
		status: DF.Literal["Draft", "Unseen", "Seen", "Actioned"]
	# end: auto-generated types

	def validate(self):
		self._guard_sender_only_edit()
		self._validate_reference_exists()
		self._validate_recipient()
		self._validate_parent_referral()

	def before_insert(self):
		if not self.sender:
			self.sender = frappe.session.user
		if not self.status or self.status == STATUS_DRAFT:
			self.status = STATUS_UNSEEN

	def on_update(self):
		self._sync_tracking_timestamps()

	def on_trash(self):
		"""Tidy up side artifacts when a referral is removed (e.g. recalled).

		Closes any open ToDo, drops the recipient's bell notifications, and pings
		their Cartable so the item disappears live. Best-effort — a failed nudge
		must never block the deletion.
		"""
		for cleanup in (_close_todos, _delete_notifications):
			try:
				cleanup(self.name)
			except Exception:
				frappe.log_error(title="office_automation: referral cleanup on trash failed")
		_notify_recall(self)

	# ------------------------------------------------------------------ #
	# Validation helpers
	# ------------------------------------------------------------------ #
	def _guard_sender_only_edit(self):
		"""Block a recipient from tampering with an *existing* referral.

		The Office Automation User role has blanket ``write`` on Document Referral
		(needed to create referrals when forwarding), and the delegation
		``has_permission`` hook grants row-level write to the recipient, sender and
		owner alike. That means a recipient can open the referral in the desk and
		rewrite the sender's توضیحات ارجاع (``instruction``) or its routing fields.

		Only the **sender** (the author of the referral) or a privileged user may
		modify an existing referral. Creation is exempt — it is governed by role
		permissions and the forward API. The internal state transitions
		(``mark_seen`` / ``mark_actioned`` / approve-reject-return) all use
		``db_set`` and never run this validate path, so they are unaffected; the
		recipient can still record their own note when actioning (that flow appends
		via ``db_set``, it does not overwrite the sender's note).
		"""
		if self.is_new():
			return
		user = frappe.session.user
		if user == self.sender or is_privileged(user):
			return
		frappe.throw(
			_("Only the sender can modify a referral once it has been sent."),
			frappe.PermissionError,
		)

	def _validate_reference_exists(self):
		if not (self.reference_doctype and self.reference_name):
			frappe.throw(_("Reference Document is mandatory."))
		if not frappe.db.exists(self.reference_doctype, self.reference_name):
			frappe.throw(
				_("Referenced document {0} {1} does not exist.").format(
					self.reference_doctype, self.reference_name
				)
			)

	def _validate_recipient(self):
		if self.recipient == self.sender:
			frappe.throw(_("Sender and Recipient cannot be the same user."))
		if not frappe.db.get_value("User", self.recipient, "enabled"):
			frappe.throw(_("Recipient {0} is not an active user.").format(self.recipient))

	def _validate_parent_referral(self):
		if not self.parent_referral:
			return

		parent = frappe.db.get_value(
			"Document Referral",
			self.parent_referral,
			["reference_doctype", "reference_name", "name"],
			as_dict=True,
		)
		if not parent:
			frappe.throw(_("Parent Referral {0} not found.").format(self.parent_referral))

		# The whole referral tree must belong to a single document.
		if parent.reference_doctype != self.reference_doctype or parent.reference_name != self.reference_name:
			frappe.throw(_("Parent Referral belongs to a different document."))

		# Guard against cycles (a node cannot be its own ancestor).
		if self.name and self._is_ancestor(self.name, self.parent_referral):
			frappe.throw(_("Circular referral detected."))

	@staticmethod
	def _is_ancestor(candidate_ancestor: str, start_node: str) -> bool:
		"""Walk up from start_node to root checking for candidate_ancestor."""
		seen = set()
		current = start_node
		while current:
			if current in seen:
				# defensive: existing data already cyclic
				return True
			seen.add(current)
			if current == candidate_ancestor:
				return True
			current = frappe.db.get_value("Document Referral", current, "parent_referral")
		return False

	# ------------------------------------------------------------------ #
	# State transitions
	# ------------------------------------------------------------------ #
	def _sync_tracking_timestamps(self):
		updates = {}
		if self.status == STATUS_SEEN and not self.seen_on:
			updates["seen_on"] = now_datetime()
		if self.status == STATUS_ACTIONED and not self.actioned_on:
			updates["actioned_on"] = now_datetime()
			if not self.seen_on:
				updates["seen_on"] = now_datetime()
		if updates:
			# db_set avoids re-triggering the full save cycle
			for field, value in updates.items():
				self.db_set(field, value, update_modified=False)

	def mark_seen(self):
		if self.status == STATUS_UNSEEN:
			self.db_set("status", STATUS_SEEN, update_modified=False)
			self.db_set("seen_on", now_datetime(), update_modified=False)

	def mark_actioned(self, outcome: str | None = None):
		self.db_set("status", STATUS_ACTIONED, update_modified=False)
		self.db_set("actioned_on", now_datetime(), update_modified=False)
		if outcome:
			self.db_set("outcome", outcome, update_modified=False)
		if self.is_overdue:
			self.db_set("is_overdue", 0, update_modified=False)
		if not self.seen_on:
			self.db_set("seen_on", now_datetime(), update_modified=False)
		# An actioned item is no longer in the recipient's open ToDo list.
		_close_todos(self.name)


# ---------------------------------------------------------------------- #
# Whitelisted API — Referral engine
# ---------------------------------------------------------------------- #
@frappe.whitelist()
def forward_document(
	doc_type: str,
	doc_name: str,
	recipient: str,
	instruction: str | None = None,
	action_type: str | None = None,
	referral_type: str = "Action",
	attachment: str | None = None,
	parent_referral: str | None = None,
):
	"""Forward (Erja) a document to a recipient by creating a Document Referral.

	* Validates that the user may read the referenced document.
	* Creates a new ``Document Referral`` row (status ``Unseen``).
	* When forwarding *from* an inbox item the parent referral is marked
	  ``Actioned`` because the recipient has handled it by passing it on. If no
	  ``parent_referral`` is given, the caller's own open referral on the
	  document (if any) is used automatically, so forwarding from the desk form
	  or the letter view closes the caller's inbox item too.
	"""
	names = _forward_many(
		doc_type,
		doc_name,
		[recipient],
		instruction=instruction,
		action_type=action_type,
		referral_type=referral_type,
		attachment=attachment,
		parent_referral=parent_referral,
	)
	frappe.db.commit()
	return names[0]


@frappe.whitelist()
def forward_to_many(
	doc_type: str,
	doc_name: str,
	recipients: str | list,
	instruction: str | None = None,
	action_type: str | None = None,
	referral_type: str = "Action",
	attachment: str | None = None,
	parent_referral: str | None = None,
) -> list[str]:
	"""Forward a document to several recipients at once, atomically.

	All referrals hang off the same parent and are created in a single
	transaction — either every recipient receives it or none does.
	``recipients`` is a JSON list (or a Python list) of user ids.
	"""
	if isinstance(recipients, str):
		recipients = frappe.parse_json(recipients)
	names = _forward_many(
		doc_type,
		doc_name,
		recipients or [],
		instruction=instruction,
		action_type=action_type,
		referral_type=referral_type,
		attachment=attachment,
		parent_referral=parent_referral,
	)
	frappe.db.commit()
	return names


def _forward_many(
	doc_type: str,
	doc_name: str,
	recipients: list,
	instruction: str | None = None,
	action_type: str | None = None,
	referral_type: str = "Action",
	attachment: str | None = None,
	parent_referral: str | None = None,
) -> list[str]:
	"""Shared engine for forward_document / forward_to_many (no commit)."""
	if not frappe.has_permission(doc_type, doc=doc_name, ptype="read"):
		frappe.throw(
			_("You are not permitted to access {0} {1}.").format(doc_type, doc_name),
			frappe.PermissionError,
		)

	# De-duplicate while preserving order; ignore blanks.
	unique: list[str] = []
	for r in recipients:
		r = (r or "").strip() if isinstance(r, str) else r
		if r and r not in unique:
			unique.append(r)
	if not unique:
		frappe.throw(_("At least one recipient is required."))

	sender = frappe.session.user
	effective = get_effective_users(sender)

	# Validate every recipient before creating anything, so a bad entry can't
	# leave a half-delivered fan-out behind.
	for recipient in unique:
		if recipient == sender:
			frappe.throw(_("Sender and Recipient cannot be the same user."))
		if not frappe.db.get_value("User", recipient, "enabled"):
			frappe.throw(_("Recipient {0} is not an active user.").format(recipient))

	# Resolve the parent referral (the inbox item being acted upon), if any.
	parent_doc = None
	if parent_referral:
		parent_doc = frappe.get_doc("Document Referral", parent_referral)
		# The reference doc must match the parent's reference doc.
		if parent_doc.reference_doctype != doc_type or parent_doc.reference_name != doc_name:
			frappe.throw(_("Parent Referral does not belong to the supplied document."))
		# You may only branch the tree from a node addressed to (or sent by) you.
		if (
			parent_doc.recipient not in effective
			and parent_doc.sender not in effective
			and not is_privileged(sender)
		):
			frappe.throw(
				_("You can only forward from a referral addressed to you."),
				frappe.PermissionError,
			)
	else:
		parent_name = find_open_referral(doc_type, doc_name, sender)
		if parent_name:
			parent_doc = frappe.get_doc("Document Referral", parent_name)

	names = []
	for recipient in unique:
		referral = create_referral(
			reference_doctype=doc_type,
			reference_name=doc_name,
			recipient=recipient,
			sender=sender,
			instruction=instruction,
			action_type=action_type,
			referral_type=referral_type,
			attachment=attachment,
			parent_referral=parent_doc.name if parent_doc else None,
		)
		names.append(referral.name)

	# Acting on a parent referral (forwarding it onward) closes that node —
	# also when the caller is the recipient's active delegate.
	if parent_doc and parent_doc.recipient in effective and parent_doc.status != STATUS_ACTIONED:
		parent_doc.mark_actioned()

	return names


def find_open_referral(doc_type: str, doc_name: str, user: str | None = None) -> str | None:
	"""The caller's open (Unseen/Seen) referral on a document, if any.

	Considers referrals addressed to the user and to anyone they currently
	substitute for; the user's own item wins over a delegated one, newest first.
	"""
	user = user or frappe.session.user
	effective = get_effective_users(user)
	rows = frappe.get_all(
		"Document Referral",
		filters={
			"reference_doctype": doc_type,
			"reference_name": doc_name,
			"recipient": ["in", effective],
			"status": ["in", (STATUS_UNSEEN, STATUS_SEEN)],
		},
		fields=["name", "recipient"],
		order_by="creation desc",
	)
	if not rows:
		return None
	own = [r for r in rows if r.recipient == user]
	return (own or rows)[0].name


def create_referral(
	reference_doctype: str,
	reference_name: str,
	recipient: str,
	sender: str | None = None,
	instruction: str | None = None,
	action_type: str | None = None,
	referral_type: str = "Action",
	attachment: str | None = None,
	is_cc: bool = False,
	parent_referral: str | None = None,
	notify: bool = True,
):
	"""Create a single Document Referral (the shared building block).

	Used by ``forward_document`` (Erja) and by Automation Letter's internal
	"send to recipients / CC" on submit. Inserts the row, nudges the reference
	document's status, and fans out notifications.
	"""
	referral = frappe.get_doc(
		{
			"doctype": "Document Referral",
			"reference_doctype": reference_doctype,
			"reference_name": reference_name,
			"sender": sender or frappe.session.user,
			"recipient": recipient,
			"action_type": action_type,
			"referral_type": referral_type or "Action",
			"is_cc": 1 if is_cc else 0,
			"instruction": instruction,
			"attachment": attachment,
			"parent_referral": parent_referral,
			"status": STATUS_UNSEEN,
			"outcome": "Pending",
		}
	)
	referral.insert(ignore_permissions=True)

	# A file uploaded for the referral is private and unattached, so only its
	# uploader could download it. Attach it to the referenced document, which
	# every party of the referral tree can read.
	if attachment:
		link_file_to_document(
			attachment, reference_doctype, reference_name, also_from=("Document Referral", referral.name)
		)

	# Bubble the reference document into an "In Progress" state if applicable.
	_touch_reference_status(reference_doctype, reference_name)

	# Push a bell notification + live cartable refresh to the recipient.
	if notify:
		notify_recipient(referral)

	return referral


def link_file_to_document(
	file_url: str | None, doctype: str, docname: str, also_from: tuple[str, str] | None = None
):
	"""Attach a freshly uploaded (still unattached) File to a document.

	Files uploaded from the Cartable are private and unattached until the
	letter/referral is saved; while unattached only the uploader can open them.
	Linking them to the document lets everyone who can read that document
	download the file. Only the uploader's own unattached files are claimed, so
	a caller cannot hijack someone else's upload by guessing its URL.
	"""
	if not file_url:
		return
	owner = {} if is_privileged(frappe.session.user) else {"owner": frappe.session.user}
	file_name = frappe.db.get_value(
		"File", {"file_url": file_url, "attached_to_name": ["in", ["", None]], **owner}, "name"
	)
	if not file_name and also_from:
		# Frappe auto-attaches an Attach-field file to the record that holds it
		# (here: a single referral), which would hide it from the other
		# recipients of a multi-recipient forward. Re-home it onto the document.
		file_name = frappe.db.get_value(
			"File",
			{
				"file_url": file_url,
				"attached_to_doctype": also_from[0],
				"attached_to_name": also_from[1],
				**owner,
			},
			"name",
		)
	if file_name:
		frappe.db.set_value(
			"File",
			file_name,
			{"attached_to_doctype": doctype, "attached_to_name": docname},
			update_modified=False,
		)


def _reference_title(reference_doctype: str, reference_name: str) -> str:
	meta = frappe.get_meta(reference_doctype)
	title_field = (meta.get_title_field() if meta else None) or "name"
	return frappe.get_value(reference_doctype, reference_name, title_field) or reference_name


def notify_recipient(referral):
	"""Fan out notifications to a referral's recipient.

	Honors ``Office Automation Settings`` (bell log always; ToDo, email and
	realtime are toggleable). Every channel is best-effort — a notification
	failure must never roll back a valid referral, so exceptions are logged and
	swallowed.
	"""
	try:
		from office_automation.office_automation.doctype.office_automation_settings.office_automation_settings import (
			get_settings,
		)

		settings = get_settings()
		reference_title = _reference_title(referral.reference_doctype, referral.reference_name)
		subject = _("New referral from {0}: {1}").format(
			frappe.utils.get_fullname(referral.sender), reference_title
		)

		# 1) Bell notification (always).
		frappe.get_doc(
			{
				"doctype": "Notification Log",
				"subject": subject,
				"for_user": referral.recipient,
				"type": "Alert",
				"document_type": "Document Referral",
				"document_name": referral.name,
				"from_user": referral.sender,
				"email_content": frappe.utils.escape_html(referral.instruction or ""),
			}
		).insert(ignore_permissions=True)

		# 2) ToDo assignment (optional) — surfaces in the recipient's "To Do".
		if settings.create_todo:
			_assign_todo(referral, subject)

		# 3) Realtime cartable refresh (optional).
		_publish_inbox_update(referral.recipient, {"referral": referral.name, "subject": subject})

		# 4) Email (optional; requires an outgoing email account).
		if settings.send_email_notification:
			frappe.sendmail(
				recipients=[referral.recipient],
				subject=subject,
				message=frappe.utils.escape_html(referral.instruction or subject),
				reference_doctype="Document Referral",
				reference_name=referral.name,
				now=False,
			)
	except Exception:
		frappe.log_error(title="office_automation: referral notification failed")


def _assign_todo(referral, description: str):
	"""Create a ToDo assignment for the recipient (idempotent per referral)."""
	from frappe.desk.form.assign_to import add as assign_add

	exists = frappe.db.exists(
		"ToDo",
		{
			"reference_type": "Document Referral",
			"reference_name": referral.name,
			"allocated_to": referral.recipient,
			"status": "Open",
		},
	)
	if exists:
		return
	assign_add(
		{
			"assign_to": [referral.recipient],
			"doctype": "Document Referral",
			"name": referral.name,
			"description": description,
			"assigned_by": referral.sender,
			"notify": 0,
		}
	)


def _close_todos(referral_name: str):
	"""Cancel any open ToDos tied to a referral once it is handled."""
	todos = frappe.get_all(
		"ToDo",
		filters={
			"reference_type": "Document Referral",
			"reference_name": referral_name,
			"status": "Open",
		},
		pluck="name",
	)
	for name in todos:
		frappe.db.set_value("ToDo", name, "status", "Closed", update_modified=False)


def _touch_reference_status(doc_type: str, doc_name: str):
	"""Best-effort: move an Automation Letter to 'In Progress' once referred.

	A ``Closed`` letter that receives a new referral is re-opened, since there
	is again open work on it.
	"""
	if doc_type != "Automation Letter":
		return
	current = frappe.db.get_value(doc_type, doc_name, "status")
	if current in ("Registered", "Closed"):
		frappe.db.set_value(doc_type, doc_name, "status", "In Progress", update_modified=False)


@frappe.whitelist()
def get_referral_tree(doc_type: str, doc_name: str) -> list[dict]:
	"""Return the complete hierarchical referral tree for a document.

	Output is a list of root nodes; each node carries a ``children`` list.
	A single indexed query fetches every referral for the document, and the
	tree is assembled in memory (O(n)) — no recursive SQL.
	"""
	if not frappe.has_permission(doc_type, doc=doc_name, ptype="read"):
		frappe.throw(
			_("You are not permitted to access {0} {1}.").format(doc_type, doc_name),
			frappe.PermissionError,
		)

	rows = frappe.get_all(
		"Document Referral",
		filters={"reference_doctype": doc_type, "reference_name": doc_name},
		fields=[
			"name",
			"parent_referral",
			"sender",
			"recipient",
			"action_type",
			"instruction",
			"status",
			"outcome",
			"is_cc",
			"seen_on",
			"actioned_on",
			"creation",
		],
		order_by="creation asc",
	)

	nodes: dict[str, dict] = {}
	roots: list[dict] = []

	users = list({r.sender for r in rows} | {r.recipient for r in rows})
	full_names = (
		{
			u.name: u.full_name
			for u in frappe.get_all(
				"User", filters={"name": ["in", users]}, fields=["name", "full_name"], ignore_permissions=True
			)
		}
		if users
		else {}
	)

	for row in rows:
		row["children"] = []
		row["sender_name"] = full_names.get(row.sender) or row.sender
		row["recipient_name"] = full_names.get(row.recipient) or row.recipient
		nodes[row["name"]] = row

	for row in rows:
		parent = row.get("parent_referral")
		if parent and parent in nodes:
			nodes[parent]["children"].append(row)
		else:
			roots.append(row)

	return roots


@frappe.whitelist()
def mark_referral_seen(referral: str):
	"""Mark a referral as seen — used by the Cartable when an item is opened.

	Only the recipient (or their active delegate) may do this. In particular the
	*sender* must not: marking their own sent item as seen would both falsify
	the read receipt and block them from recalling it.
	"""
	doc = frappe.get_doc("Document Referral", referral)
	if doc.recipient not in get_effective_users(frappe.session.user):
		frappe.throw(_("You can only update your own inbox items."), frappe.PermissionError)
	doc.mark_seen()
	return doc.status


@frappe.whitelist()
def mark_referral_actioned(referral: str, outcome: str | None = None, note: str | None = None):
	"""Mark a referral as actioned — «اتمام کار» (handled / completed / filed).

	The natural close for informational items (CC / اطلاع / استحضار) that need
	no approve/reject decision. ``outcome`` is optional and restricted to the
	known outcomes; an optional ``note`` is appended like the other actions.
	"""
	if outcome and outcome not in ("Approved", "Rejected", "Returned"):
		frappe.throw(_("Invalid outcome {0}.").format(outcome))
	doc = _get_own_referral(referral)
	if doc.status == STATUS_ACTIONED:
		return doc.status
	if note:
		doc.db_set("instruction", _append_note(doc.instruction, note), update_modified=False)
	doc.mark_actioned(outcome=outcome)
	_maybe_close_reference(doc.reference_doctype, doc.reference_name)
	frappe.db.commit()
	return doc.status


@frappe.whitelist()
def approve_referral(referral: str, note: str | None = None):
	"""Recipient approves the referral (Outbox -> Approved for the sender)."""
	doc = _get_own_referral(referral, require_open=True)
	if note:
		doc.db_set("instruction", _append_note(doc.instruction, note), update_modified=False)
	doc.mark_actioned(outcome="Approved")
	_maybe_close_reference(doc.reference_doctype, doc.reference_name)
	_notify_outcome(doc, "Approved")
	frappe.db.commit()
	return doc.outcome


@frappe.whitelist()
def reject_referral(referral: str, note: str | None = None):
	"""Recipient rejects / sends back the referral (Outbox -> Rejected)."""
	doc = _get_own_referral(referral, require_open=True)
	if note:
		doc.db_set("instruction", _append_note(doc.instruction, note), update_modified=False)
	doc.mark_actioned(outcome="Rejected")
	_maybe_close_reference(doc.reference_doctype, doc.reference_name)
	_notify_outcome(doc, "Rejected")
	frappe.db.commit()
	return doc.outcome


@frappe.whitelist()
def return_referral(referral: str, note: str | None = None):
	"""Recipient returns the referral to its sender (عودت).

	Like approve/reject this closes the recipient's own inbox item (status
	``Actioned``) but records the distinct outcome ``Returned`` so the sender
	sees it in their "Returned" Outbox folder. Use it when a letter is sent back
	for revision/clarification rather than approved or rejected outright. An
	optional note is appended to the instruction and the sender is notified.
	"""
	doc = _get_own_referral(referral, require_open=True)
	if note:
		doc.db_set("instruction", _append_note(doc.instruction, note), update_modified=False)
	doc.mark_actioned(outcome="Returned")
	_maybe_close_reference(doc.reference_doctype, doc.reference_name)
	_notify_outcome(doc, "Returned")
	frappe.db.commit()
	return doc.outcome


# ---------------------------------------------------------------------- #
# Recall (بازپس‌گیری) — sender unsends a letter still unread by recipients
# ---------------------------------------------------------------------- #
@frappe.whitelist()
def recall_letter(reference_name: str, reference_doctype: str = "Automation Letter") -> dict:
	"""Recall a sent letter by pulling back every still-``Unseen`` referral.

	Only the original sender may recall. Referrals already opened (``Seen`` /
	``Actioned``) are left untouched. When *no* recipient has opened the letter
	(all referrals were unseen and are now removed), the letter reverts to an
	editable ``Draft`` so the sender can amend and re-send it.

	Returns ``{recalled, kept, reverted_to_draft}``.
	"""
	letter = frappe.get_doc(reference_doctype, reference_name)
	_assert_is_sender(letter.get("sender"))

	# Only the letter's own deliveries (sent by its sender) are pulled back —
	# referrals other users forwarded further down the tree are theirs to recall.
	referrals = frappe.get_all(
		"Document Referral",
		filters={
			"reference_doctype": reference_doctype,
			"reference_name": reference_name,
			"sender": letter.get("sender"),
		},
		fields=["name", "status"],
	)
	unread = [r["name"] for r in referrals if r["status"] == STATUS_UNSEEN]
	kept = len(referrals) - len(unread)

	if not unread:
		frappe.throw(_("This letter cannot be recalled — every recipient has already opened it."))

	for name in unread:
		_recall_single(name)

	reverted = _maybe_revert_to_draft(reference_doctype, reference_name)
	frappe.db.commit()
	return {"recalled": len(unread), "kept": kept, "reverted_to_draft": reverted}


@frappe.whitelist()
def recall_referral(referral: str) -> dict:
	"""Recall a single recipient's still-``Unseen`` referral.

	Only the original sender may recall, and only while the recipient has not
	opened it. If this removes the last referral on the letter, the letter
	reverts to an editable ``Draft``.
	"""
	doc = frappe.get_doc("Document Referral", referral)
	_assert_is_sender(doc.sender)
	if doc.status != STATUS_UNSEEN:
		frappe.throw(_("This item has already been opened and can no longer be recalled."))

	reference_doctype, reference_name = doc.reference_doctype, doc.reference_name
	parent = doc.parent_referral
	_recall_single(referral)
	_maybe_reopen_parent(parent)
	reverted = _maybe_revert_to_draft(reference_doctype, reference_name)
	frappe.db.commit()
	return {"reverted_to_draft": reverted}


def _maybe_reopen_parent(parent_name: str | None):
	"""Undo the implicit close of a forwarded inbox item when its forward is recalled.

	Forwarding marks the forwarder's own referral ``Actioned``. If they recall the
	only child they created from it (and it carried no explicit outcome), the
	item goes back to their inbox as ``Seen`` so the work is not lost.
	"""
	if not parent_name:
		return
	parent = frappe.db.get_value(
		"Document Referral", parent_name, ["name", "status", "outcome", "recipient"], as_dict=True
	)
	if not parent or parent.status != STATUS_ACTIONED or parent.outcome not in (None, "", "Pending"):
		return
	if parent.recipient not in get_effective_users(frappe.session.user):
		return
	if frappe.db.exists("Document Referral", {"parent_referral": parent_name}):
		return
	frappe.db.set_value(
		"Document Referral",
		parent_name,
		{"status": STATUS_SEEN, "actioned_on": None},
		update_modified=False,
	)
	_publish_inbox_update(parent.recipient, {"referral": parent_name, "reopened": True})


def _assert_is_sender(sender: str | None):
	if sender != frappe.session.user:
		frappe.throw(_("Only the original sender can recall this letter."), frappe.PermissionError)


def _recall_single(referral_name: str):
	"""Delete one referral; its ``on_trash`` clears ToDos, notifications and
	refreshes the recipient's Cartable."""
	frappe.delete_doc("Document Referral", referral_name, ignore_permissions=True, force=True)


def _maybe_revert_to_draft(reference_doctype: str, reference_name: str) -> bool:
	"""Bring a fully-recalled Automation Letter back to an editable Draft.

	Triggered when no referral remains on a submitted letter — i.e. nothing was
	ever opened, so the send is fully undone. A partial recall (some referrals
	opened and kept) instead just recomputes the letter's closure state.
	"""
	if reference_doctype != "Automation Letter":
		return False

	remaining = frappe.db.count(
		"Document Referral",
		{"reference_doctype": reference_doctype, "reference_name": reference_name},
	)
	if remaining:
		# Partial recall: opened referrals stay, keep the letter active.
		_maybe_close_reference(reference_doctype, reference_name)
		return False

	docstatus = frappe.db.get_value(reference_doctype, reference_name, "docstatus")
	if docstatus != 1:
		return False

	# Force the submitted letter back to Draft (docstatus 0). Submittable docs
	# have no native un-submit, and the sender's role lacks cancel/amend, so a
	# direct db update is the intended escape hatch for a clean unsend.
	frappe.db.set_value(
		reference_doctype,
		reference_name,
		{"docstatus": 0, "status": "Draft"},
		update_modified=True,
	)
	frappe.clear_document_cache(reference_doctype, reference_name)
	return True


def _delete_notifications(referral_name: str):
	"""Remove the recipient's bell notifications tied to a (recalled) referral."""
	logs = frappe.get_all(
		"Notification Log",
		filters={"document_type": "Document Referral", "document_name": referral_name},
		pluck="name",
	)
	for name in logs:
		frappe.delete_doc("Notification Log", name, ignore_permissions=True, force=True)


def _publish_inbox_update(user: str, message: dict):
	"""Fire the realtime Cartable-refresh event for a user when realtime is on.

	Shared by every flow that changes a user's inbox/outbox (new referral,
	outcome, recall) so the event name + gating live in one place.
	"""
	from office_automation.office_automation.doctype.office_automation_settings.office_automation_settings import (
		get_settings,
	)

	if get_settings().realtime_update:
		frappe.publish_realtime(
			event="oa_inbox_update",
			message=message,
			user=user,
			after_commit=True,
		)


def _notify_recall(referral):
	"""Best-effort realtime nudge so the recipient's Cartable drops the item."""
	try:
		_publish_inbox_update(referral.recipient, {"referral": referral.name, "recalled": True})
	except Exception:
		frappe.log_error(title="office_automation: recall notification failed")


def _get_own_referral(referral: str, require_open: bool = False):
	"""Load a referral the current user is entitled to ACT ON (approve / reject /
	return / mark-actioned).

	Acting on a referral is the *recipient's* decision, so only the recipient —
	or a user actively delegated to substitute for that recipient — may do it.
	A generic ``write`` permission is deliberately NOT sufficient: the delegation
	``has_permission`` hook grants write to the sender and owner too (so they can
	read/track the item), but the sender must never be able to approve, reject or
	return a referral they sent — that would let them forge an outcome and dismiss
	the item from the recipient's inbox before the recipient ever sees it.

	``get_effective_users(session_user)`` is the session user plus every delegator
	they currently substitute for, so ``recipient in effective`` is true exactly
	when the caller is the recipient or one of the recipient's active delegates.
	"""
	doc = frappe.get_doc("Document Referral", referral)
	if doc.recipient not in get_effective_users(frappe.session.user):
		frappe.throw(
			_("Only the recipient (or their delegate) can action this referral."),
			frappe.PermissionError,
		)
	if require_open and doc.status == STATUS_ACTIONED:
		# e.g. a stale tab or a double click: never overwrite a recorded outcome.
		frappe.throw(_("This referral has already been actioned."))
	return doc


def _append_note(existing: str | None, note: str) -> str:
	# db_set bypasses Frappe's XSS sanitizer, so strip markup here — the note is
	# plain text and is rendered in print formats and the desk.
	note = frappe.utils.strip_html_tags(note or "").strip()
	if not note:
		return existing or ""
	stamp = f"[{frappe.utils.get_fullname(frappe.session.user)}] {note}"
	return f"{existing}\n{stamp}" if existing else stamp


def _notify_outcome(doc, outcome: str):
	"""Tell the original sender that their referral was approved/rejected."""
	try:
		reference_title = _reference_title(doc.reference_doctype, doc.reference_name)
		subject = _("Referral {0} by {1}: {2}").format(
			_(OUTCOME_LABELS.get(outcome, outcome)),
			frappe.utils.get_fullname(doc.recipient),
			reference_title,
		)
		frappe.get_doc(
			{
				"doctype": "Notification Log",
				"subject": subject,
				"for_user": doc.sender,
				"type": "Alert",
				"document_type": "Document Referral",
				"document_name": doc.name,
				"from_user": doc.recipient,
			}
		).insert(ignore_permissions=True)
		_publish_inbox_update(doc.sender, {"referral": doc.name, "subject": subject, "outcome": outcome})
	except Exception:
		frappe.log_error(title="office_automation: outcome notification failed")


def _maybe_close_reference(doc_type: str, doc_name: str):
	"""Close an Automation Letter once every referral on it is Actioned.

	Only applies when at least one referral exists, so a freshly registered
	letter is never auto-closed.
	"""
	if doc_type != "Automation Letter":
		return

	open_count = frappe.db.count(
		"Document Referral",
		{
			"reference_doctype": doc_type,
			"reference_name": doc_name,
			"status": ["in", (STATUS_DRAFT, STATUS_UNSEEN, STATUS_SEEN)],
		},
	)
	total = frappe.db.count("Document Referral", {"reference_doctype": doc_type, "reference_name": doc_name})
	if total and not open_count:
		current = frappe.db.get_value(doc_type, doc_name, "status")
		if current == "In Progress":
			frappe.db.set_value(doc_type, doc_name, "status", "Closed", update_modified=False)


def on_reference_trash(doc, method=None):
	"""Cascade: when a referenced document is deleted, remove its referrals."""
	referrals = frappe.get_all(
		"Document Referral",
		filters={"reference_doctype": doc.doctype, "reference_name": doc.name},
		pluck="name",
	)
	for name in referrals:
		frappe.delete_doc("Document Referral", name, ignore_permissions=True, force=True)
