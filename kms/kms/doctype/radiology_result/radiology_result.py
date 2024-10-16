# Copyright (c) 2024, GIS and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document

class RadiologyResult(Document):
	def on_submit(self):
		for result in self.result:
			pass