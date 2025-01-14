# Copyright (c) 2024, GIS and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import now
from frappe.model.document import Document

class RadiologyResult(Document):
	def on_submit(self):
		if self.dispatcher:
			doctor_result_name = frappe.db.get_value('Doctor Result', {
				'appointment': self.appointment,
				'docstatus': 0
			}, 'name')
			for result in self.result:
				item_group = frappe.db.get_value('Item', result.item_code, 'item_group')
				mcu_grade_name = frappe.db.get_value('MCU Exam Grade', {
					'hidden_item': result.item_code,
					'hidden_item_group': item_group,
					'parent': doctor_result_name,
					'examination': result.result_line
				}, 'name')
				frappe.db.set_value('MCU Exam Grade', mcu_grade_name, {
					'result': result.result_check,
					'uom': result.result_text,
					'status': self.workflow_state
				})
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
