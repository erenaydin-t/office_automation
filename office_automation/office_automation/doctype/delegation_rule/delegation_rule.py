# Copyright (c) 2026, Milanpars and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class DelegationRule(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		delegatee: DF.Link
		delegator: DF.Link
		from_date: DF.Date
		is_active: DF.Check
		naming_series: DF.Literal["DELEG-.YYYY.-"]
		to_date: DF.Date
	# end: auto-generated types

	def validate(self):
		if self.delegator == self.delegatee:
			frappe.throw(_("Delegator and Delegatee cannot be the same user."))
		if getdate(self.from_date) > getdate(self.to_date):
			frappe.throw(_("From Date cannot be after To Date."))
		self._check_overlap()

	def on_change(self):
		# Permission decisions are cached per-request; clear so changes take
		# effect immediately for the affected delegatee.
		frappe.cache().delete_value(_delegators_cache_key(self.delegatee))

	def _check_overlap(self):
		overlap = frappe.db.sql(
			"""
			select name from `tabDelegation Rule`
			where name != %(name)s
			  and delegator = %(delegator)s
			  and delegatee = %(delegatee)s
			  and is_active = 1
			  and from_date <= %(to_date)s
			  and to_date >= %(from_date)s
			limit 1
			""",
			{
				"name": self.name or "new",
				"delegator": self.delegator,
				"delegatee": self.delegatee,
				"from_date": self.from_date,
				"to_date": self.to_date,
			},
		)
		if overlap and self.is_active:
			frappe.throw(_("An overlapping active delegation already exists ({0}).").format(overlap[0][0]))


def _delegators_cache_key(user: str) -> str:
	return f"oa_active_delegators::{user}"
