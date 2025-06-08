# Copyright (c) 2024, GIS and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import now
from frappe.model.document import Document

class RadiologyResult(Document):
	def on_submit(self):
		if self.patient_encounter:
			enc = frappe.get_doc('Patient Encounter', self.patient_encounter)
			for custom_row in enc.custom_radiology:
				matching_template = next(
					(item.template for item in self.examination_item if item.template == custom_row.template), None
				)
				if matching_template:
					radiology_request = next(
						(request for request in enc.custom_radiology if request.template == matching_template), None
					)
					if radiology_request:
						radiology_request.radiology_result = self.name
						radiology_request.status = 'Finished'
						radiology_request.status_time = now()
						enc.save(ignore_permissions=True)
		else:
			doctor_result_name = frappe.db.get_value('Doctor Result', {
				'appointment': self.appointment,
				'docstatus': 0
			}, 'name')
			for exam in self.examination_item:
				conclusion_text = [row.conclusion for row in self.conclusion if row.item == exam.item]
				if conclusion_text:
					conclusion_result = ', '.join(conclusion_text)
				item_group = frappe.db.get_value('Item', exam.item, 'item_group')
				mcu_grade_name = frappe.db.get_value('MCU Exam Grade', {
					'hidden_item': exam.item,
					'hidden_item_group': item_group,
					'parent': doctor_result_name,
					'is_item': 0
				}, 'name')
				frappe.db.set_value('MCU Exam Grade', mcu_grade_name, {
					'result': conclusion_result,
					'status': self.get('workflow_state', 'Finished'),
					'document_type': 'Radiology Result',
					'document_name': self.name,
				})
