# Copyright (c) 2026, Milanpars and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, today


class AutomationLetter(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from office_automation.office_automation.doctype.automation_letter_attachment.automation_letter_attachment import (
			AutomationLetterAttachment,
		)
		from office_automation.office_automation.doctype.automation_letter_recipient.automation_letter_recipient import (
			AutomationLetterRecipient,
		)

		amended_from: DF.Link | None
		archive_doctype: DF.Link | None
		archive_name: DF.DynamicLink | None
		attachments: DF.Table[AutomationLetterAttachment]
		body: DF.TextEditor | None
		cc_recipients: DF.Table[AutomationLetterRecipient]
		confidentiality: DF.Literal["Normal", "Confidential", "Secret"]
		date: DF.Date
		is_private: DF.Check
		letter_no: DF.Data | None
		letter_type: DF.Link | None
		naming_series: DF.Literal["AL-.YYYY.-"]
		recipients: DF.Table[AutomationLetterRecipient]
		sender: DF.Link
		status: DF.Literal["Draft", "Registered", "In Progress", "Closed", "Cancelled"]
		subject: DF.Data
		urgency: DF.Literal["Normal", "Urgent", "Immediate"]
	# end: auto-generated types

	def before_insert(self):
		# Apply the org's configured default letter type to new letters when none
		# was chosen. Stored as a setting (not hardcoded) so it works regardless of
		# how each site names/renames its Letter Types.
		if not self.letter_type:
			from office_automation.office_automation.doctype.office_automation_settings.office_automation_settings import (
				get_settings,
			)

			default_type = get_settings().default_letter_type
			if default_type and frappe.db.exists("Letter Type", default_type):
				self.letter_type = default_type

	def validate(self):
		if not self.sender:
			self.sender = frappe.session.user
		if self.status == "Cancelled" and self.docstatus != 2:
			# guard against manual edits; status is system-managed
			self.status = "Draft"
		self._validate_recipients()

	def _validate_recipients(self):
		"""No self-addressing, and a user may not appear twice across To + CC."""
		seen = set()
		for row in [*self.recipients, *self.cc_recipients]:
			if row.recipient == self.sender:
				frappe.throw(_("Row #{0}: A letter cannot be sent to its own sender.").format(row.idx))
			if row.recipient in seen:
				frappe.throw(_("{0} is listed more than once across Recipients/CC.").format(row.recipient))
			seen.add(row.recipient)

	def before_submit(self):
		# When the letter is registered in the دبیرخانه it becomes immutable
		# and ready to be referred (Erja). It also receives its secretariat
		# number (شماره نامه) unless one was entered manually.
		self.status = "Registered"
		if not self.letter_no:
			self.letter_no = make_letter_number(self.date)

	def on_submit(self):
		# Submitting registers the letter AND sends it to every recipient (and CC),
		# creating a root Document Referral (Cartable item) for each.
		self.send_to_recipients()

	def before_cancel(self):
		# Must be set *before* the cancel is written: anything assigned in
		# on_cancel runs after the DB update and would silently be lost.
		self.status = "Cancelled"

	def on_cancel(self):
		self.close_open_referrals()

	def close_open_referrals(self):
		"""A cancelled letter needs no further action: clear it from every
		recipient's Cartable by closing the still-open referrals."""
		from office_automation.office_automation.doctype.document_referral.document_referral import (
			OPEN_STATUSES,
			_publish_inbox_update,
		)

		open_refs = frappe.get_all(
			"Document Referral",
			filters={
				"reference_doctype": self.doctype,
				"reference_name": self.name,
				"status": ["in", OPEN_STATUSES],
			},
			pluck="name",
		)
		for name in open_refs:
			ref = frappe.get_doc("Document Referral", name)
			ref.mark_actioned()
			_publish_inbox_update(ref.recipient, {"referral": name, "cancelled": True})

	def send_to_recipients(self):
		"""Create a root referral for each To recipient and each CC recipient.

		CC rows always land in the recipient's Info / FYI folder and are flagged
		``is_cc`` so they never block the main workflow.
		"""
		from office_automation.office_automation.doctype.document_referral.document_referral import (
			create_referral,
		)

		for row in self.recipients:
			create_referral(
				reference_doctype=self.doctype,
				reference_name=self.name,
				recipient=row.recipient,
				sender=self.sender,
				instruction=row.instruction,
				action_type=row.action_type,
				referral_type=row.referral_type or "Action",
			)

		for row in self.cc_recipients:
			create_referral(
				reference_doctype=self.doctype,
				reference_name=self.name,
				recipient=row.recipient,
				sender=self.sender,
				instruction=row.instruction,
				action_type=row.action_type,
				referral_type="Info",
				is_cc=True,
			)


# --------------------------------------------------------------------------- #
# Secretariat numbering (شماره نامه)
# --------------------------------------------------------------------------- #
def gregorian_to_jalali(gy: int, gm: int, gd: int) -> tuple[int, int, int]:
	"""Convert a Gregorian date to Jalali (Solar Hijri). Pure arithmetic — no
	dependency on the optional persian_calendar app."""
	g_d_m = (0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334)
	gy2 = gy + 1 if gm > 2 else gy
	days = 355666 + 365 * gy + (gy2 + 3) // 4 - (gy2 + 99) // 100 + (gy2 + 399) // 400 + gd + g_d_m[gm - 1]
	jy = -1595 + 33 * (days // 12053)
	days %= 12053
	jy += 4 * (days // 1461)
	days %= 1461
	if days > 365:
		jy += (days - 1) // 365
		days = (days - 1) % 365
	if days < 186:
		jm, jd = 1 + days // 31, 1 + days % 31
	else:
		jm, jd = 7 + (days - 186) // 30, 1 + (days - 186) % 30
	return jy, jm, jd


def make_letter_number(date=None) -> str | None:
	"""Next secretariat number, e.g. ``1405/00012`` (optionally prefixed).

	The counter restarts every Jalali year and is kept in Frappe's ``Series``
	table, so concurrent registrations never collide. Disabled (returns None)
	when *Auto Letter Number* is off in Office Automation Settings.
	"""
	from frappe.model.naming import getseries

	from office_automation.office_automation.doctype.office_automation_settings.office_automation_settings import (
		get_settings,
	)

	settings = get_settings()
	if not settings.get("auto_letter_number"):
		return None
	d = getdate(date or today())
	jy = gregorian_to_jalali(d.year, d.month, d.day)[0]
	prefix = (settings.get("letter_number_prefix") or "").strip()
	key = f"OA-LETTER-NO-{prefix}-{jy}"
	for _attempt in range(5):
		number = f"{prefix}{jy}/{getseries(key, 5)}"
		# Skip numbers already taken manually (letter_no is unique).
		if not frappe.db.exists("Automation Letter", {"letter_no": number}):
			return number
	return None
