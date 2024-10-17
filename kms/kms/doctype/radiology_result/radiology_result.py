# Copyright (c) 2024, GIS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class RadiologyResult(Document):
	def on_submit(self):
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