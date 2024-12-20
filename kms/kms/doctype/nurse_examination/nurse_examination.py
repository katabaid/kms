# Copyright (c) 2024, GIS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class NurseExamination(Document):
	def on_submit(self):
		exam_result = frappe.db.exists('Nurse Result', {'exam': self.name}, 'name')
		self.db_set('submitted_date', frappe.utils.now_datetime())
		if exam_result:
			self.db_set('exam_result', exam_result)
	def before_save(self):
		is_try = True
		if self.status == 'Checked In' and self.docstatus == 0:
			if self.non_selective_result:
				results_dict = {item.test_name: item.result_value for item in self.non_selective_result}
				for exam_item in self.examination_item:
					template_doc = frappe.get_doc('Nurse Examination Template', exam_item.template)
					if template_doc.result_in_exam:
						if template_doc.calculated_exam:
							self.calculated_result = []
							for calc in template_doc.calculated_exam:
								formula = calc.formula
								for key, value in results_dict.items():
									formula = formula.replace(f"{{{{{key}}}}}", str(value))
									if not str(value) or str(value) == 'None':
										is_try = False
								if is_try:
									try:
										result_value = eval(formula)
									except Exception as e:
										frappe.throw(f"Error evaluating formula for {calc.test_label}: {str(e)}")
									self.append('calculated_result',{
										'test_label': calc.test_label,
										'result': result_value,
										'item_code': template_doc.item_code
									})
	def on_update(self):
		old = self.get_doc_before_save()
		if self.status == 'Checked In' and self.docstatus == 0 and old.status == 'Started':
			self.db_set('checked_in_time', frappe.utils.now_datetime())
	
	def before_insert(self):
		for exam in self.examination_item:
			item_code = frappe.db.get_value('Nurse Examination Template', exam.template, 'item_code')
			if item_code:
				try:
					is_internal, template = frappe.db.get_value('Questionnaire Template', item_code, ['internal_questionnaire', 'template_name'])
				except TypeError:
					is_internal, template = None, None
				if is_internal:
					status = frappe.db.get_value(
						'Questionnaire', 
						{'patient_appointment': self.appointment, 'template': template},
						'status')
					self.append('questionnaire', {
						'template': template,
						'is_completed': True if status == 'Completed' else False
					})

