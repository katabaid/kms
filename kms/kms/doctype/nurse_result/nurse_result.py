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
				'status': self.status
			})
		for non_selective in self.non_selective_result:
			item_group = frappe.db.get_value('Item', non_selective.item_code, 'item_group')
			mcu_grade_name = frappe.db.get_value('MCU Exam Grade', {
				'hidden_item': non_selective.item_code,
				'hidden_item_group': item_group,
				'parent': doctor_result_name,
				'examination': non_selective.test_name
			}, 'name')
			incdec = ''
			incdec_category = ''
			if (non_selective.min_value != 0 or non_selective.max_value != 0) and non_selective.min_value and non_selective.max_value and non_selective.result_value:
				incdec = 'Increase' if non_selective.result_value > non_selective.max_value else ('Decrease' if non_selective.result_value < non_selective.min_value else None)
				if incdec:
					incdec_category = frappe.db.get_value('MCU Category', {
						'item_group': item_group,
						'item': non_selective.item_code,
						'test_name': non_selective.test_name,
						'selection': incdec
					}, 'description')
			frappe.db.set_value('MCU Exam Grade', mcu_grade_name, {
				'result': non_selective.result_value,
				'incdec': incdec,
				'incdec_category': incdec_category,
				'status': self.status
			})