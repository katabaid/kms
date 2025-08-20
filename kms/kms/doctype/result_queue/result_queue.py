# Copyright (c) 2025, GIS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ResultQueue(Document):
	def before_insert(self):
		self.patient = frappe.get_value(self.doc_type, self.doc_name, 'patient')
