# Copyright (c) 2024, GIS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Questionnaire(Document):
	def after_insert(self):
		if self.patient_appointment:
			pa_doc = frappe.get_doc("Patient Appointment", self.patient_appointment)
			for detail in self.detail:
				detail_dict = {
					k: v for k, v in detail.as_dict().items() 
					if k not in ('name', 'parent', 'parenttype', 'parentfield', 'idx')
				}
				pa_doc.append('custom_questionnaire_detail', detail_dict)
			pa_doc.save(ignore_permissions=True)
			filters = {
				'appointment': self.patient_appointment,
				'docstatus': ['in', ['0', '1']]
			}
			de = frappe.get_all('Doctor Examination', 
				filters = filters, 
				pluck = 'name')
			for de_name in de:
				de_doc = frappe.get_doc('Doctor Examination', de_name)
				if de_doc.questionnaire:
					for row in de_doc.questionnaire:
						if row.template == self.template:
							row.is_completed = True
							de_doc.save(ignore_permissions=True)
							break
			ne = frappe.get_all('Nurse Examination', 
				filters = filters, 
				pluck = 'name')
			for ne_name in ne:
				ne_doc = frappe.get_doc('Nurse Examination', ne_name)
				if ne_doc.questionnaire:
					for row in ne_doc.questionnaire:
						if row.template == self.template:
							row.is_completed = True
							ne_doc.save(ignore_permissions=True)
							break
	
	def before_insert(self):
		self.status = 'Completed' if self.patient_appointment else 'Draft'
		for row in self.detail:
			if row.template and row.question:
				new_question = frappe.get_all('Questionnaire Template Detail', {'parent': row.template, 'name': row.question}, pluck='label')[0]
				row.question = new_question
