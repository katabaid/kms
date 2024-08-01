# Copyright (c) 2024, GIS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _

class DispatcherSettings(Document):
	def validate(self):
		if frappe.db.exists(self.doctype,{
			'branch': self.branch,
			'enable_date': self.enable_date,
			'name': ('!=', self.name)
		}):
			frappe.throw(_("The combination of Branch and Enable Date must be unique."))