# Copyright (c) 2025, GIS and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class MCUQueuePooling(Document):
	def before_insert(self):
		self.title = f'{self.patient_appointment}-{self.date}-{self.service_unit}'
