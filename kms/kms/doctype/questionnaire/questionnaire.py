# Copyright (c) 2024, GIS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Questionnaire(Document):
	def after_insert(self):
		if self.patient_appointment:
			pa_doc = frappe.get_doc("Patient Appointment", self.patient_appointment)
			for detail in self.detail:
				pa_doc.append('custom_questionnaire_detail', detail.as_dict())
			pa_doc.save(ignore_permissions=True)
	
	def before_insert(self):
		self.status = 'Draft'
