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
	* When forwarding *from* an inbox item (``parent_referral`` set), the parent
	  referral is marked ``Actioned`` because the recipient has handled it by
	  passing it on.
	"""
	if not frappe.has_permission(doc_type, doc=doc_name, ptype="read"):
		frappe.throw(
			_("You are not permitted to access {0} {1}.").format(doc_type, doc_name),
			frappe.PermissionError,
		)

	sender = frappe.session.user

	# Resolve the parent referral (the inbox item being acted upon), if any.
	parent_doc = None
	if parent_referral:
		parent_doc = frappe.get_doc("Document Referral", parent_referral)
		# The reference doc must match the parent's reference doc.
		if parent_doc.reference_doctype != doc_type or parent_doc.reference_name != doc_name:
			frappe.throw(_("Parent Referral does not belong to the supplied document."))

	referral = create_referral(
		reference_doctype=doc_type,
		reference_name=doc_name,
		recipient=recipient,
		sender=sender,
		instruction=instruction,
		action_type=action_type,
		referral_type=referral_type,
		attachment=attachment,
		parent_referral=parent_referral,
	)

	# Acting on a parent referral (forwarding it onward) closes that node.
	if parent_doc and parent_doc.recipient == sender and parent_doc.status != STATUS_ACTIONED:
		parent_doc.mark_actioned()

	frappe.db.commit()
	return referral.name


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

	# Bubble the reference document into an "In Progress" state if applicable.
	_touch_reference_status(reference_doctype, reference_name)

	# Push a bell notification + live cartable refresh to the recipient.
	if notify:
		notify_recipient(referral)

	return referral


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
	"""Best-effort: move an Automation Letter to 'In Progress' once referred."""
	if doc_type != "Automation Letter":
		return
	current = frappe.db.get_value(doc_type, doc_name, "status")
	if current == "Registered":
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
			"seen_on",
			"actioned_on",
			"creation",
		],
		order_by="creation asc",
	)

	nodes: dict[str, dict] = {}
	roots: list[dict] = []

	for row in rows:
		row["children"] = []
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
	"""Mark a referral as seen — used by the Cartable when an item is opened."""
	doc = frappe.get_doc("Document Referral", referral)
	if doc.recipient != frappe.session.user and not frappe.has_permission(
		"Document Referral", doc=doc, ptype="write"
	):
		frappe.throw(_("You can only update your own inbox items."), frappe.PermissionError)
	doc.mark_seen()
	return doc.status


@frappe.whitelist()
def mark_referral_actioned(referral: str, outcome: str | None = None):
	"""Mark a referral as actioned (handled / completed), optionally with an outcome."""
	doc = _get_own_referral(referral)
	doc.mark_actioned(outcome=outcome)
	_maybe_close_reference(doc.reference_doctype, doc.reference_name)
	return doc.status


@frappe.whitelist()
def approve_referral(referral: str, note: str | None = None):
	"""Recipient approves the referral (Outbox -> Approved for the sender)."""
	doc = _get_own_referral(referral)
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
	doc = _get_own_referral(referral)
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
	doc = _get_own_referral(referral)
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

	referrals = frappe.get_all(
		"Document Referral",
		filters={"reference_doctype": reference_doctype, "reference_name": reference_name},
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
	_recall_single(referral)
	reverted = _maybe_revert_to_draft(reference_doctype, reference_name)
	frappe.db.commit()
	return {"reverted_to_draft": reverted}


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


def _get_own_referral(referral: str):
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
	return doc


def _append_note(existing: str | None, note: str) -> str:
	stamp = f"[{frappe.utils.get_fullname(frappe.session.user)}] {note}"
	return f"{existing}\n{stamp}" if existing else stamp


def _notify_outcome(doc, outcome: str):
	"""Tell the original sender that their referral was approved/rejected."""
	try:
		subject = _("Referral {0}: {1} {2}").format(outcome, doc.reference_doctype, doc.reference_name)
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
