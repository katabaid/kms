# Copyright (c) 2024, GIS and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document

class DoctorExaminationTemplate(Document):
	def before_save(self):
		if len(self.items) + len(self.normal_items) == 1:
			self.is_single_result = 1
		else:
			self.is_single_result = 0
