# Copyright (c) 2024, GIS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class NurseExamination(Document):
	def on_submit(self):
		exam_result = frappe.db.exists('Nurse Examination Result', {'exam': self.name}, 'name')
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
										'result': result_value
									})
