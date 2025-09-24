# Copyright (c) 2024, GIS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from kms.api.healthcare import finish_exam

class NurseExamination(Document):
	def on_submit(self):
		finish_exam(self.service_unit, self.status, self.doctype, self.name)
		self._update_exam_result()
		self.db_set('submitted_date', frappe.utils.now_datetime())

	def on_update(self):
		old = self.get_doc_before_save()
		if self.status == 'Checked In' and self.docstatus == 0 and old.status == 'Started':
			self.db_set('checked_in_time', frappe.utils.now_datetime())
	
	def before_save(self):
		if self.status == 'Checked In' and self.docstatus == 0:
			self._calculate_results()

	def before_insert(self):
		self._fetch_questionnaire_data()
		self.exam_note = frappe.db.get_value('Patient Appointment', self.appointment, 'notes')

	def _update_exam_result(self):
		exam_result = frappe.db.exists('Nurse Result', {'exam': self.name}, 'name')
		if exam_result:
			self.db_set('exam_result', exam_result)

	def _calculate_results(self):
		if not self.non_selective_result:
			return
		results_dict = {item.test_name: item.result_value for item in self.non_selective_result}
		self.calculated_result = []
		for exam_item in self.examination_item:
			template_doc = frappe.get_doc('Nurse Examination Template', exam_item.template)
			if template_doc.result_in_exam and template_doc.calculated_exam:
				self._process_calculated_exam(template_doc, results_dict)

	def _process_calculated_exam(self, template_doc, results_dict):
		for calc in template_doc.calculated_exam:
			formula = calc.formula
			is_try = True
			for key, value in results_dict.items():
				formula = formula.replace(f"{{{{{key}}}}}", str(value))
				if not value or str(value) in ['None', '0']:
					is_try = False
			if is_try:
				self._evaluate_formula(calc, formula, template_doc.item_code)

	def _evaluate_formula(self, calc, formula, item_code):
		try:
			result_value = eval(formula)
			self.append('calculated_result', {
				'test_label': calc.test_label,
				'result': result_value,
				'item_code': item_code
			})
		except Exception as e:
			frappe.throw(f"Error evaluating formula for {calc.test_label}: {str(e)}")

	def _fetch_questionnaire_data(self):
		cardiologist = frappe.db.get_single_value('MCU Settings', 'cardiologist')
		for exam in self.examination_item:
			self._process_exam_item(exam, cardiologist)

	def _process_exam_item(self, exam, cardiologist):
		is_internal = frappe.db.get_value('Questionnaire Template', exam.template, 'internal_questionnaire')
		template = frappe.db.get_value('Questionnaire Template', exam.template, 'template_name')
		if exam.item == cardiologist:
			is_internal = True
			template = 'Treadmill'
		if is_internal:
			self._append_questionnaire(template)

	def _append_questionnaire(self, template):
		questionnaire_data = self._get_questionnaire_data(template)
		if questionnaire_data:
			self.append('questionnaire', {
				'template': template,
				'status': questionnaire_data.get('status'),
				'is_completed': True if questionnaire_data.get('status') == 'Completed' else False,
				'questionnaire': questionnaire_data.get('name')
			})
		else:
			self.append('questionnaire', {
				'template': template,
				'status': None,
				'is_completed': False
			})

	def _get_questionnaire_data(self, template):
		return frappe.db.get_value(
			'Questionnaire',
			{'patient_appointment': self.appointment, 'template': template},
			['status', 'name'],
			as_dict=True
		)

