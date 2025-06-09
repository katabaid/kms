# Copyright (c) 2024, GIS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class NurseResult(Document):
	def before_submit (self):
		self.status = 'Finished'
		for non_selective_result in self.non_selective_result:
			if not non_selective_result.result_value:
				frappe.throw (f"""Result Value {non_selective_result.test_name} is mandatory before submitting the document.""")
		for examination_item in self.examination_item:
			if examination_item.status == 'Started':
				examination_item.status = 'Finished'

	def on_submit(self):
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
				'is_item': 1
			}, 'name')
			frappe.db.set_value('MCU Exam Grade', mcu_grade_name, {
				'result': conclusion_result,
				'status': self.get('workflow_state', 'Finished'),
				'document_type': 'Nurse Result',
				'document_name': self.name,
			})
