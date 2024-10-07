# Copyright (c) 2024, GIS and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import now
from frappe.model.document import Document

class SampleReception(Document):
	def on_submit(self):
		self.collected_by = frappe.session.user
		self.collection_time = now()
