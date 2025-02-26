# Copyright (c) 2024, GIS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class DoctorResult(Document):
	def before_submit(self):
		if not self.validate_before_submit():
			frappe.throw('All results must be submitted, and all gradable must be graded.')
		self.process_auto_grading()
		self.process_physical_exam()
		self.process_other_exam()		
	
# Server Script: before_submit for DoctorResult
	def validate_before_submit(self):
		def validate_row(row):
			# Check if gradable = 1 and grade is empty
			if row.get("gradable") == 1 and not row.get("grade"):
				return False
			# Check if hidden_item_group and hidden_item are set, is_item = 0, and result is empty
			if (
				row.get("hidden_item_group")
				and row.get("hidden_item")
				and row.get("is_item") == 0
				and not row.get("result")
			):
				return False
			return True

		def validate_child_table(child_table):
			return all(validate_row(row) for row in child_table)

		# List of child tables to validate
		child_tables = ["nurse_grade", "doctor_grade", "radiology_grade", "lab_test_grade"]

		# Validate all child tables and return the result
		return all(
			validate_child_table(self.get(table)) for table in child_tables if self.get(table)
		)

	def on_update_after_submit(self):
		self.process_group_exam()

	def process_auto_grading(self):
		self._process_item_grade()
		self._process_group_grade()

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
					if row.parentfield == 'nurse_grade':
						item_template = frappe.get_value(
							'Nurse Examination Template', {'item_code':row.hidden_item}, 'name')
					if row.hidden_item:
						if ((item_template and item_template not in vital_sign_templates())
							and (row.hidden_item != physical_examination())
							and row.hidden_item != 'DENS-00082'
						):
							counter += 1
							bundle_position = frappe.get_value(
								'Item', row.hidden_item, 'custom_bundle_position')
							current_results.append({
								'examination': (
									row.hidden_item_group if not row.hidden_item and row.hidden_item_group else 
									row.hidden_item if row.hidden_item and row.hidden_item_group and row.is_item else 
									row.examination),
								'result': row.result,
								'bundle_position': bundle_position if bundle_position else 9999,
								'idx': counter,
								'uom': row.uom,
								'std_value': format_floats_and_combine(row.min_value, row.max_value),
								'header': (
									'Group' if not row.hidden_item and row.hidden_item_group else 
									'Item' if row.hidden_item and row.hidden_item_group and row.is_item else 
									None),
								'item_group': row.hidden_item_group,
								'item': row.hidden_item
							})
					else:
						counter += 1
						bundle_position = frappe.get_value(
							'Item Group', row.hidden_item_group, 'custom_bundle_position')
						current_results.append({
							'examination': row.hidden_item_group,
							'bundle_position': bundle_position if bundle_position else 9999,
							'idx': counter,
							'header': 'Group'
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

		row_index = 0

		for result in sorted_results:
			row_index += 1
			if row_index>1 and (row_index-1)%15 == 0:
				if result.get('header') is None:
					self.append('other_examination', {
						'content': result.get('item'),
						'header': 'Item'
					})
			self.append('other_examination', {
				'content': result.get('examination'),
				'result': result.get('result'),
				'uom': result.get('uom'),
				'std_value': result.get('std_value'),
				'header': result.get('header'),
				'previous_result': previous_data.get(result['examination'], '') if result.get('result') else None,
				'last_result': last_data.get(result['examination'], '') if result.get('result') else None,
			})

	def process_group_exam(self):
		self.group_exam = []
		grade_tables = ['nurse_grade', 'doctor_grade', 'radiology_grade', 'lab_test_grade']
		current_results = []
		counter = 0
		for table in grade_tables:
			for row in getattr(self, table, []):
				try:
					if not row.hidden_item:
						counter += 1
						bundle_position = frappe.get_value('Item Group', row.hidden_item_group, 'custom_bundle_position')
						grade = frappe.get_value('MCU Grade', row.grade, 'grade')
						grade_on_report = frappe.get_value('MCU Grade', row.grade, 'grade_on_report')
						current_results.append({
							'contents': row.hidden_item_group,
							'result': grade if not grade_on_report else grade_on_report,
							'bundle_position': bundle_position if bundle_position else 9999,
							'idx': counter,
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
				previous_data = {d.contents: d.result for d in prev_doc.group_exam}
			if len(previous_results) >= 2:
				last_doc = frappe.get_doc('Doctor Result', previous_results[1].name)
				last_data = {d.contents: d.result for d in last_doc.group_exam}

		for result in sorted_results:
			self.append('group_exam', {
				'contents': result['contents'],
				'result': result['result'],
				'previous_result': previous_data.get(result['contents'], '') if result['result'] else None,
				'last_result': last_data.get(result['contents'], '') if result['result'] else None,
			})

	def _process_nurse_grade(self):
		counter = 0
		for nurse_grade in self.nurse_grade:
			item_template = frappe.get_value(
				'Nurse Examination Template', {'item_code':nurse_grade.hidden_item}, 'name')
			if item_template in vital_sign_templates() and nurse_grade.result:
				counter += 1
				self.append('physical_examination', {
					'item_name': 'Vital Sign' if counter == 1 else None,
					'item_input': nurse_grade.examination,
					'result': nurse_grade.result + ' ' + nurse_grade.uom,
				})

	def _process_doctor_grade(self):
		counter = 0
		for doctor_grade in self.doctor_grade:
			if doctor_grade.hidden_item == physical_examination() and doctor_grade.status:
				counter += 1
				self.append('physical_examination', {
					'item_name': 'Physical Examination' if counter == 1 else None,
					'item_input': doctor_grade.examination,
					'result': doctor_grade.result,
				})

	def _process_item_grade(self):
		grade_tables = ['nurse_grade', 'doctor_grade', 'radiology_grade', 'lab_test_grade']
		for table in grade_tables:
			for row in getattr(self, table, []):
				pass

	def _process_group_grade(self):
		grade_tables = ['nurse_grade', 'doctor_grade', 'radiology_grade', 'lab_test_grade']
		for table in grade_tables:
			for row in getattr(self, table, []):
				pass

def format_floats_and_combine(a, b):
	def safe_float(value):
			try:
					return float(value)
			except (TypeError, ValueError):
					return None

	a = safe_float(a)
	b = safe_float(b)
	if not a and not b:
		return None
	formatted_a = f"{int(a)}" if a and a.is_integer() else f"{a}" if a else "0"
	formatted_b = f"{int(b)}" if b and b.is_integer() else f"{b}" if b else "0"
	return f"{formatted_a} - {formatted_b}"

def vital_sign_templates(): 
	return frappe.get_all('MCU Vital Sign', filters = {'parentfield': 'vital_sign_on_report'}, pluck = "template")

def physical_examination():
	return frappe.db.get_single_value('MCU Settings', 'physical_examination')

def physical_examination_name():
	return frappe.db.get_single_value('MCU Settings', 'physical_examination_name')