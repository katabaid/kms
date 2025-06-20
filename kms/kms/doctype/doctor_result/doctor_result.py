# Copyright (c) 2024, GIS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class DoctorResult(Document):
	child_tables = ["nurse_grade", "doctor_grade", "radiology_grade", "lab_test_grade"]
	grade_order = ['A', 'B', 'BF', 'C', 'D', 'E', 'F']

	def before_save(self):
		remarks = {
			row.description.strip()
			for child_name in self.child_tables
			for row in (self.get(child_name) or [])
			if row.grade and row.grade.split('-')[-1] != "A" and row.description
    }
		dental_comments = _get_dental_comments(self.appointment) or []
		self.copied_remark = "\n".join(sorted(remarks) + dental_comments)

	def before_submit(self):
		#if not self.validate_before_submit():
		#	frappe.throw('All results must be submitted, and all gradable must be graded.')
		self.process_auto_grading()
		self.process_physical_exam()
		self.process_other_exam()		
	
# Server Script: before_submit for DoctorResult
	def validate_before_submit(self):
		def is_valid(row):
			return not (
				(row.get("gradable") == 1 and not row.get("grade")) or
				(row.get(
					"hidden_item_group") and row.get("hidden_item") and 
					row.get("is_item") == 0 and not row.get("result")
				)
			)
		return all(
			all(is_valid(row) for row in self.get(table)) for table in self.child_tables if self.get(table)
		)

	def on_submit(self):
		self.process_group_exam()

	def process_auto_grading(self):
		self._process_item_grade()
		self._process_group_grade()

	def process_physical_exam(self):
		self._process_nurse_grade()
		self._process_doctor_grade()

	def process_other_exam(self):
		self.other_examination = []
		current_results = []
		counter = 0
		for table in self.child_tables:
			previous_item = ''
			previous_group = ''
			for row in getattr(self, table, []):
				#try:
					item_template = ''
					if row.parentfield == 'nurse_grade':
						item_template = frappe.get_value(
							'Nurse Examination Template', {'item_code':row.hidden_item}, 'name')
					if row.hidden_item:
						print(counter, row.hidden_item)
						if (((item_template and item_template not in vital_sign_templates()) or not item_template)
							and (row.hidden_item != physical_examination())
						):
							counter += 1
							#if previous_item and previous_item != row.hidden_item:
							#	item_all_inputs = [
							#		p.incdec_category for p in getattr(self, table, []) 
							#		if p.hidden_item == previous_item and p.incdec_category]
							#	comments = ", ".join(item_all_inputs) if item_all_inputs else "Dalam batas normal."
							#	current_results.append({
							#		'examination': f'Comment: {comments}',
							#		'bundle_position': bundle_position if bundle_position else 9999,
							#		'idx': counter,
							#		'header': 'Item',
							#		'item_group': row.hidden_item_group,
							#		'item': row.hidden_item
							#	})
							#	previous_item = row.hidden_item
							#	counter += 1
							#if not previous_item:
							#	previous_item = row.hidden_item
							bundle_position = frappe.get_value(
								'Item', row.hidden_item, 'custom_bundle_position')
							arrow = '\u2193' if row.incdec == 'Decrease' else '\u2191' if row.incdec == 'Increase' else ''
							std_value = row.std_value
							if not row.hidden_item and row.hidden_item_group:
								examination = row.hidden_item_group
								header = 'Group'
							elif row.hidden_item and row.hidden_item_group and row.is_item:
								examination = row.examination
								if row.result:
									header = None
									if examination == 'HbA1c':
										examination += '<br/>Pre - Diabetic<br/>Diabetic'
										std_value = '&lt; 5.7<br/>5.7 - 6.5<br/>&#8805; 6.5'
									elif examination == 'Typoid IgM (Tubex)':
										examination += '<br/>Negative (does not indicate current typhoid fever infection)'
										examination += '<br/>Inconclusive (repeat the test if still inconclusive, repeat sampling at a later date)'
										examination += '<br/>Positive (The higher score the stronger is the indication of current typhoid fever infection)'
										std_value = '&#8804; 2<br/><br/>&gt;2 - &lt;4<br/>4 - 10'
									elif examination == 'Sputum Direct BTA':
										examination += '<ul><li>Negative (Tidak ditemukan BTA / 100 Lapang Pandang)</li>'
										examination += '<li>Scanty (1 - 9 BTA /100 Lapang Pandang)</li>'
										examination += '<li>(1+) (10 - 99 BTA / 100 Lapang Pandang)</li>'
										examination += '<li>(2+) (1 - 10 BTA / Lapang Pandang)</li>'
										examination += '<li>(3+) (>10 BTA / Lapang Pandang)</li></ul>'
									elif examination == 'Stool Culture' or examination == 'Rectal Swab (Swab Culture)':
										examination += '<ul><li>Salmonella</li>'
										examination += '<li>Shigella</li>'
										examination += '<li>Vibrio</li>'
										examination += '<li>Escherichia coli O157H7</li></ul>'
								else:
									header = 'Item'
							else:
								examination = row.examination
								header = None
							if isinstance(row.result, (int, float)):
								row_result = int(row.result) if row.result.is_integer() else row.result
							else:
								row_result = row.result
							current_results.append({
								'examination': examination,
								'result': (row_result or '') + ' ' + arrow,
								'bundle_position': bundle_position if bundle_position else 9999,
								'idx': counter,
								'uom': row.uom,
								'std_value': std_value,
								'header': header,
								'item_group': row.hidden_item_group,
								'item': row.hidden_item
							})
					else:
						counter += 1
						print(counter)
						#if counter > 1:
						#	item_all_inputs = [
						#		p.incdec_category for p in getattr(self, table, []) 
						#		if p.hidden_item == previous_item and p.incdec_category]
						#	comments = ", ".join(item_all_inputs) if item_all_inputs else "Dalam batas normal."
						#	current_results.append({
						#		'examination': f'Comment: {comments}',
						#		'bundle_position': bundle_position if bundle_position else 9999,
						#		'idx': counter,
						#		'header': 'Item',
						#		'item_group': row.hidden_item_group,
						#		'item': row.hidden_item
						#	})
						#	previous_item = row.hidden_item
						#	counter += 1
						if previous_group and previous_group != row.hidden_item_group:
							item_all_inputs = [
								p.incdec_category for p in getattr(self, table, []) 
								if p.hidden_item_group == previous_group and p.incdec_category]
							comments = ", ".join(item_all_inputs) if item_all_inputs else "Dalam batas normal."
							current_results.append({
								'examination': f'Comment: {comments}',
								'bundle_position': bundle_position if bundle_position else 9999,
								'idx': counter,
								'header': 'Group'
							})
							previous_group = row.hidden_item_group
							counter += 1
						if not previous_group:
							previous_group = row.hidden_item_group
						bundle_position = frappe.get_value(
							'Item Group', row.hidden_item_group, 'custom_bundle_position')
						current_results.append({
							'examination': row.hidden_item_group,
							'bundle_position': bundle_position if bundle_position else 9999,
							'idx': counter,
							'header': 'Group'
						})
				#except Exception as e:
				#	frappe.log_error(f"Error processing {table} row: {e}")
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
					row_index += 1
					self.append('other_examination', {
						'content': frappe.db.get_value('Item', result.get('item'), 'item_name'),
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
		current_results = []
		counter = 0
		for table in self.child_tables:
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
		self.save()

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
		for table in self.child_tables:
			for row in getattr(self, table, []):
				if row.is_item == 1 and row.gradable == 1:
					item_group = row.hidden_item_group
					item_code = row.hidden_item
					item_name = row.examination
					item_grade = row.grade
					# determine children
					children = [
						e for e in getattr(self, table, [])
						if e.get('hidden_item_group') == item_group
						and e.get('hidden_item') == item_code
						and e.get('is_item') == 0
						and e.get('gradable') == 1
					]
					if not children and not item_grade:
						frappe.throw(f'{item_name} must grade manually.')
					# check missing grades
					missing_grades = [e for e in children if not e.get('grade')]
					if missing_grades:
						frappe.throw(f"Grade missing for examination(s) {[e.examination for e in missing_grades]} under item {row.get('examination')} in {table}")
					# check invalid grades
					invalid_entries = []
					actual_grades = []
					for e in children:
						mcu_grade_name = e.grade
						if not frappe.db.exists('MCU Grade', mcu_grade_name):
							invalid_entries.append("MCU Grade '{mcu_grade_name}' not found for {e.examination}")
							continue
						mcu_grade = frappe.get_doc("MCU Grade", mcu_grade_name)
						actual_grade = mcu_grade.get("grade_on_report") or mcu_grade.get("grade")
						if not actual_grade:
							invalid_entries.append(f"MCU Grade '{mcu_grade_name}' has no grade configured for {e.examination}")
						elif actual_grade not in self.grade_order:
							invalid_entries.append(f"Invalid grade '{actual_grade}' from MCU Grade '{mcu_grade_name}' for {e.examination}")
						else:
							actual_grades.append(actual_grade)
						if invalid_entries:
							frappe.throw("<br>".join(invalid_entries))
					# determine worst grade
					if actual_grades:
						worst_grade = max(actual_grades, key=lambda g: self.grade_order.index(g))
						row.grade = item_group+'.'+item_code+'.-'+worst_grade

	def _process_group_grade(self):
		for table in self.child_tables:
			for row in getattr(self, table, []):
				if not row.hidden_item and row.gradable:
					# determine children
					children = [
						e for e in getattr(self, table, [])
						if e.get('hidden_item_group') == row.hidden_item_group
						and e.get('is_item') == 1
						and e.get('gradable') == 1
					]
					# check missing grades
					missing_grades = [e for e in children if not e.get('grade')]
					if not children and not row.grade:
						frappe.throw(f'{row.hidden_item_group} must grade manually.')
					if missing_grades:
						frappe.throw(f"Grade missing for item(s) {[e.examination for e in missing_grades]} in {table}")
					# check invalid grades
					invalid_entries = []
					actual_grades = []
					for e in children:
						mcu_grade_name = e.grade
						if not frappe.db.exists('MCU Grade', mcu_grade_name):
							invalid_entries.append(f"MCU Grade '{mcu_grade_name}' not found for {e.examination}")
							continue
						mcu_grade = frappe.get_doc("MCU Grade", mcu_grade_name)
						actual_grade = mcu_grade.get("grade_on_report") or mcu_grade.get("grade")
						if not actual_grade:
							invalid_entries.append(f"MCU Grade '{mcu_grade_name}' has no grade configured for {e.examination}")
						elif actual_grade not in self.grade_order:
							invalid_entries.append(f"Invalid grade '{actual_grade}' from MCU Grade '{mcu_grade_name}' for {e.examination}")
						else:
							actual_grades.append(actual_grade)
					if invalid_entries:
						frappe.throw("<br>".join(invalid_entries))
					# determine worst grade
					if actual_grades:
						worst_grade = max(actual_grades, key=lambda g: self.grade_order.index(g))
						row.grade = row.hidden_item_group+'..-'+worst_grade

def vital_sign_templates(): 
	return frappe.get_all(
		'MCU Vital Sign', filters = {'parentfield': 'vital_sign_on_report'}, pluck = "template")

def physical_examination():
	return frappe.db.get_single_value('MCU Settings', 'physical_examination', cache=True)

def _get_dental_comments(appointment):
	return frappe.db.sql("""SELECT suggestion FROM `tabDental Grading` WHERE parent =
		(SELECT parent FROM `tabDoctor Examination Request` tder, `tabDoctor Examination` td 
		WHERE item = (SELECT value FROM tabSingles ts WHERE doctype = 'MCU Settings'
		AND field = 'dental_examination') AND parent = td.name
		AND td.appointment = %s AND td.docstatus = 0) ORDER BY idx
		""", (appointment), as_list=True)
