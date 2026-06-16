# Copyright (c) 2026, Milanpars and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

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
		instruction: DF.SmallText | None
		is_overdue: DF.Check
		naming_series: DF.Literal["REF-.YYYY.-"]
		parent_referral: DF.Link | None
		recipient: DF.Link
		reference_doctype: DF.Link
		reference_name: DF.DynamicLink
		seen_on: DF.Datetime | None
		sender: DF.Link
		status: DF.Literal["Draft", "Unseen", "Seen", "Actioned"]
	# end: auto-generated types

	def validate(self):
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

	# ------------------------------------------------------------------ #
	# Validation helpers
	# ------------------------------------------------------------------ #
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

	def mark_actioned(self):
		self.db_set("status", STATUS_ACTIONED, update_modified=False)
		self.db_set("actioned_on", now_datetime(), update_modified=False)
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
		frappe.throw(_("You are not permitted to access {0} {1}.").format(doc_type, doc_name))

	sender = frappe.session.user

	# Resolve the parent referral (the inbox item being acted upon), if any.
	parent_doc = None
	if parent_referral:
		parent_doc = frappe.get_doc("Document Referral", parent_referral)
		# The reference doc must match the parent's reference doc.
		if parent_doc.reference_doctype != doc_type or parent_doc.reference_name != doc_name:
			frappe.throw(_("Parent Referral does not belong to the supplied document."))

	referral = frappe.get_doc(
		{
			"doctype": "Document Referral",
			"reference_doctype": doc_type,
			"reference_name": doc_name,
			"sender": sender,
			"recipient": recipient,
			"action_type": action_type,
			"instruction": instruction,
			"parent_referral": parent_referral,
			"status": STATUS_UNSEEN,
		}
	)
	referral.insert(ignore_permissions=True)

	# Acting on a parent referral (forwarding it onward) closes that node.
	if parent_doc and parent_doc.recipient == sender and parent_doc.status != STATUS_ACTIONED:
		parent_doc.mark_actioned()

	# Bubble the reference document into an "In Progress" state if applicable.
	_touch_reference_status(doc_type, doc_name)

	# Push a bell notification + live cartable refresh to the recipient.
	notify_recipient(referral)

	frappe.db.commit()
	return referral.name


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
		if settings.realtime_update:
			frappe.publish_realtime(
				event="oa_inbox_update",
				message={"referral": referral.name, "subject": subject},
				user=referral.recipient,
				after_commit=True,
			)

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
		frappe.throw(_("You are not permitted to access {0} {1}.").format(doc_type, doc_name))

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
		frappe.throw(_("You can only update your own inbox items."))
	doc.mark_seen()
	return doc.status


@frappe.whitelist()
def mark_referral_actioned(referral: str):
	"""Mark a referral as actioned (handled / completed)."""
	doc = frappe.get_doc("Document Referral", referral)
	if doc.recipient != frappe.session.user and not frappe.has_permission(
		"Document Referral", doc=doc, ptype="write"
	):
		frappe.throw(_("You can only update your own inbox items."))
	doc.mark_actioned()
	_maybe_close_reference(doc.reference_doctype, doc.reference_name)
	return doc.status


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
