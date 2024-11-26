# Copyright (c) 2024, GIS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class DoctorResult(Document):
	def before_submit(self):
		self.process_physical_exam()
		self.process_other_exam()
		self.process_group_exam()

	def process_physical_exam(self):
		self._process_nurse_grade()
		self._process_doctor_grade()

	def process_other_exam(self):
		self.other_examination = []
		grade_tables = ['nurse_grade', 'doctor_grade', 'radiology_grade', 'lab_test_grade']
		current_results = []
		counter = 0
		for table in grade_tables:
			for row in getattr(self, table, []):
				try:
					counter += 1
					bundle_position = frappe.get_value('Item', row.hidden_item, 'custom_bundle_position')
					current_results.append({
						'examination': row.examination,
						'result': row.result,
						'bundle_position': bundle_position if bundle_position else 9999,
						'idx': counter,
						'uom': row.uom,
						'std_value': format_floats_and_combine(row.min_value, row.max_value)
					})
				except Exception as e:
					frappe.log_error(f"Error processing {table} row: {e}")
		sorted_results = sorted(
			current_results,
			key = lambda x: (x['bundle_position'], x['idx'])
		)
		previous_results = frappe.get_all(
			'Doctor Result',
			filters = {
				'patient': self.patient,
				'docstatus': 1,
				'created_date': ("<", self.created_date),
				'name': ('!=', self.name)
			},
			fields=["name"],
			order_by = 'created_date desc',
			limit = 2
		)

		previous_data = {}
		last_data = {}
		
		if previous_results:
			if len(previous_results) >= 1:
				prev_doc = frappe.get_doc('Doctor Result', previous_results[0].name)
				previous_data = {d.content: d.result for d in prev_doc.other_examination}
			if len(previous_results) >= 2:
				last_doc = frappe.get_doc('Doctor Result', previous_results[1].name)
				last_data = {d.content: d.result for d in last_doc.other_examination}

		for result in sorted_results:
			self.append('other_examination', {
				'content': result['examination'],
				'result': result['result'],
				'uom': result['uom'],
				'previous_result': previous_data.get(result['examination'], ''),
				'last_result': last_data.get(result['examination'], ''),
			})
		#self.save()

	def process_group_exam(self):
		self.group_exam = []

	def _process_nurse_grade(self):
		templates = frappe.get_all('MCU Vital Sign', filters = {'parentfield': 'vital_sign_on_report'}, pluck = "template")
		counter = 0
		for nurse_grade in self.nurse_grade:
			item_template = frappe.get_value('Nurse Examination Template', {'item_code':nurse_grade.hidden_item}, 'name')
			if item_template in templates and nurse_grade.result:
				counter += 1
				self.append('physical_examination', {
					'item_name': 'Vital Sign' if counter == 1 else None,
					'item_input': nurse_grade.examination,
					'result': nurse_grade.result + ' ' + nurse_grade.uom,
				})
		#self.save()

	def _process_doctor_grade(self):
		physical_examination = frappe.db.get_single_value('MCU Settings', 'physical_examination')
		physical_examination_name = frappe.db.get_single_value('MCU Settings', 'physical_examination_name')
		counter = 0
		for doctor_grade in self.doctor_grade:
			if doctor_grade.hidden_item == physical_examination and doctor_grade.status:
				counter += 1
				self.append('physical_examination', {
					'item_name': physical_examination_name if counter == 1 else None,
					'item_input': doctor_grade.examination,
					'result': doctor_grade.uom,
				})
		#self.save()

def format_floats_and_combine(a, b):
	if not a and not b:
		return None
	formatted_a = f"{int(a)}" if a and a.is_integer() else f"{a}" if a else "0"
	formatted_b = f"{int(b)}" if b and b.is_integer() else f"{b}" if b else "0"
	return f"{formatted_a} - {formatted_b}"