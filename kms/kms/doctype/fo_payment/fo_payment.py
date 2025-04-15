# Copyright (c) 2025, GIS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class FOPayment(Document):
	def on_submit(self):
		pass

	def validate(self):
		if not self.items:
			frappe.throw('At least one line of payment must exists.')
		if self.total_payment <= 0:
			frappe.throw('Add payment amount to continue.')
		if sum((item.amount or 0) for item in self.items) <= 0:
			frappe.throw("Total of payment amounts must be greater than 0.")
