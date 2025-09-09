# Copyright (c) 2024, GIS and contributors
# For license information, please see license.txt

import frappe, io
from frappe.model.document import Document
from frappe.utils.pdf import get_pdf
from frappe.utils.file_manager import save_file
from PyPDF2 import PdfMerger

class DoctorResult(Document):
	child_tables = ['nurse_grade', 'doctor_grade', 'radiology_grade', 'lab_test_grade']
	grade_order = ['A', 'B', 'BF', 'C', 'D', 'E', 'F']

	def before_save(self):
		remarks = {
			row.description.strip()
			for child_name in self.child_tables
			for row in (self.get(child_name) or [])
			if row.grade and row.grade.split('-')[-1] != 'A' and row.description
    }
		dental_comments = _get_dental_comments(self.appointment) or []
		self.copied_remark = '\n'.join(sorted(remarks) + dental_comments)

	def before_submit(self):
		validation_result = self.validate_before_submit()
		if not validation_result['is_valid']:
			error_message = 'All results must be submitted, and all gradable must be graded.\n\nInvalid entries found:\n'
			for error in validation_result['errors']:
				error_message += f"Table: {error['table']}, Row: {error['row_idx']}, Item: {error['item_name']}\n"
			frappe.throw(error_message)
		if not self.validate_before_submit():
			frappe.throw('All results must be submitted, and all gradable must be graded.')
		# self.process_auto_grading()
		self.process_physical_exam()
		self.process_other_exam()

	def validate_before_submit(self):
		def is_valid(row):
			return not (
				(row.get('gradable') == 1 and not row.get('grade')) or
				(row.get('hidden_item_group') and row.get('hidden_item') and 
					row.get('is_item') == 0 and not row.get('result')
				)
			)
		def get_validation_reason(row):
			"""Helper function to determine why a row failed validation"""
			if row.get('gradable') == 1 and not row.get('grade'):
				return 'Missing grade for gradable item'
			elif (row.get('hidden_item_group') and row.get('hidden_item') and 
					row.get('is_item') == 0 and not row.get('result')):
				return 'Missing result for required item'
			else:
				return 'Unknown validation error'
		
		validation_errors = []
		for table in self.child_tables:
			if self.get(table):
				for row in self.get(table):
					if not is_valid(row):
						validation_errors.append({
							'table': table,
							'row_idx': row.idx,
							'item_name': row.get('item_name', 'Unknown Item'),
							'reason': get_validation_reason(row)
						})
		return {
			'is_valid': len(validation_errors) == 0,
			'errors': validation_errors
		}
		
# Server Script: before_submit for DoctorResult
	#def validate_before_submit(self):
	#	def is_valid(row):
	#		return not (
	#			(row.get('gradable') == 1 and not row.get('grade')) or
	#			(row.get(
	#				'hidden_item_group') and row.get('hidden_item') and 
	#				row.get('is_item') == 0 and not row.get('result')
	#			)
	#		)
	#	return all(
	#		all(is_valid(row) for row in self.get(table)) for table in self.child_tables if self.get(table)
	#	)

	def on_submit(self):
		self.process_group_exam()
		self.save()
		self.create_pdf_report()

	def on_update_before_submit(self):
		self.process_group_exam()
		self.create_pdf_report()

	def create_pdf_report(self):
		print_format = 'MCU Format'
		html = frappe.get_print(self.doctype, self.name, print_format)
		main_pdf = get_pdf(html)
		docs = frappe.db.get_all('MCU Exam Grade', {'parent':self.name}, ['document_type', 'document_name'])
		unique_docs = list({doc['document_name']: doc for doc in docs if doc.document_name}.values())
		merger = PdfMerger()
		merger.append(io.BytesIO(main_pdf))
		for doc in unique_docs:
			related_files = frappe.get_all('File', filters={
				"attached_to_doctype": doc['document_type'],
				"attached_to_name": doc['document_name'],
				"file_url": ["like", f"%{doc['document_name']}%.pdf"]
			}, pluck='name')
			for f in related_files:
				file_doc = frappe.get_doc('File', f)
				file_content = file_doc.get_content()
				merger.append(io.BytesIO(file_content))
		output = io.BytesIO()
		merger.write(output)
		merger.close()
		filename = f'{self.name}.pdf'
		existing_file = frappe.db.exists('File', {
			'file_name': ["like", f"{self.name}%.pdf"],
			'attached_to_doctype': self.doctype,
			'attached_to_name': self.name
		})
		if existing_file:
			frappe.delete_doc('File', existing_file)
		save_file(
			filename,
			output.getvalue(),
			self.doctype,
			self.name,
		)
		self.reload()

	def process_auto_grading(self):
		self._process_item_grade()
		self._process_group_grade()

	def process_physical_exam(self):
		self.physical_examination = []
		self._process_questionnaire()
		self._process_nurse_grade()
		self._process_doctor_grade()

	def process_other_exam(self):
		self.other_examination = []
		current_results = []
		counter = 0
		for table in self.child_tables:
			#previous_item = ''
			previous_group = urine_rbc = urine_wbc = ''
			for row in getattr(self, table, []):
				item_template = ''
				if row.parentfield == 'nurse_grade':
					item_template = frappe.get_value(
						'Nurse Examination Template', {'item_code':row.hidden_item}, 'name')
				if row.hidden_item:
					if (((item_template and item_template not in vital_sign_templates()) or not item_template)
						and (row.hidden_item != physical_examination())
					):
						add_result = False
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
									examination = '<p>HbA1c</p><p align="right">Pre - Diabetic</p><p align="right">Diabetic</p>'
									std_value = '<p>&lt; 5.7</p><p align="right">5.7 - 6.5</p><p align="right">&#8805; 6.5</p>'
								elif examination == 'Typoid IgM (Tubex)':
									examination = '<p>Typoid IgM (Tubex)</p>'
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
						row_result = row.result
						if row.hidden_item == 'MIRU-00001':
							if row.examination == 'urine RBC atas':
								urine_rbc = row.result
								add_result = False
							elif row.examination == 'urine RBC bawah':
								row_result = urine_rbc + ' - ' + row.result
								examination = 'Urine RBC'
								counter += 1
								add_result = True
							elif row.examination == 'urine WBC atas':
								urine_wbc = row.result
								add_result = False
							elif row.examination == 'urine WBC bawah':
								row_result = urine_wbc + ' - ' + row.result
								examination = 'Urine WBC'
								counter += 1
								add_result = True
							else:
								counter += 1
								add_result = True
						else:
							counter += 1
							add_result = True
						if isinstance(row.result, (int, float)):
							row_result = format_indonesian_safe(row.result)
						row_result = format_indonesian_safe(row_result)
						if row_result and arrow:
							final_result = f'<p style="color: red;"> {row_result} {arrow}</p>'
						else:
							final_result = row_result
						if add_result:
							current_results.append({
								'examination': examination,
								'result': final_result,
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

	def _process_questionnaire(self):
		def _process_disease_history(row_dict, indices, last_index=None):
			disease_list = []
			all_tidak_ada = True
			last_index_empty = True
			for idx in indices:
				if idx in row_dict and row_dict[idx].answer != 'Tidak Ada':
					all_tidak_ada = False
					break
			if last_index is not None and last_index in row_dict and row_dict[last_index].answer:
				last_index_empty = False
			if all_tidak_ada and last_index_empty:
				return 'Tidak Ada'
			else:
				for idx in indices:
					if idx in row_dict and row_dict[idx].answer == 'Ada':
						next_idx = idx + 1
						if next_idx in row_dict and row_dict[next_idx].answer:
							disease_list.append(row_dict[next_idx].answer)
				if last_index is not None and last_index in row_dict and row_dict[last_index].answer:
					disease_list.append(row_dict[last_index].answer)
				if disease_list:
					return ', '.join(disease_list)
				else:
					return 'Tidak Ada'
				
		q = next(iter(frappe.db.get_all('Questionnaire', pluck='name',
			filters={'patient_appointment': self.appointment, 'template': 'MCU'})), None)
		doc = frappe.get_doc('Questionnaire', q) if q else None
		if doc:
			row_dict = {row.idx: row for row in doc.detail}
			self.append('physical_examination',{
				'item_name': 'Chief Complaint',
				'result': row_dict[2].answer if row_dict[2].answer else row_dict[1].answer
			})
			row_dict = {row.idx: row for row in doc.detail}
			self.append('physical_examination',{
				'item_name': 'Life Style',
				'result': _process_disease_history(
					row_dict, [45, 47, 49])
			})
			self.append('physical_examination',{
				'item_name': 'Past Medical History',
				'result': _process_disease_history(
					row_dict, [3, 5, 7, 9, 11, 13, 15, 17, 19], 21)
			})
			self.append('physical_examination',{
				'item_name': 'Family Medical History',
				'result': _process_disease_history(
					row_dict, [22, 24, 26, 28, 30, 32, 34, 36], 38)
			})

	def _process_nurse_grade(self):
		counter = 0
		bp = ''
		append = True
		for nurse_grade in self.nurse_grade:
			item_template = frappe.get_value(
				'Nurse Examination Template', {'item_code':nurse_grade.hidden_item}, 'name')
			if item_template in vital_sign_templates() and nurse_grade.result:
				if nurse_grade.examination == 'Systolic':
					bp += f'{nurse_grade.result}'
					append = False
				elif nurse_grade.examination == 'Diastolic':
					counter += 1
					bp += f'/{nurse_grade.result}'
					final_result = bp + ' ' + nurse_grade.uom
					item_input = 'Blood Pressure'
					append = True
				else:
					counter += 1
					item_input = nurse_grade.examination
					final_result = nurse_grade.result + ' ' + nurse_grade.uom
					append = True
				if append:
					self.append('physical_examination', {
						'item_name': 'Vital Sign' if counter == 1 else None,
						'item_input': item_input,
						'result': final_result,
					})

	def _process_doctor_grade(self):
		counter = 0
		item_name = None
		for doctor_grade in self.doctor_grade:
			if doctor_grade.hidden_item == physical_examination() and doctor_grade.status:
				counter += 1
				if counter == 1:
					item_name = 'Physical Examination'
					girth = frappe.db.get_value('Doctor Examination', doctor_grade.document_name, 'abdominal_girth')
				else:
					item_name = None
				self.append('physical_examination', {
					'item_name': item_name,
					'item_input': doctor_grade.examination,
					'result': doctor_grade.result,
				})
		if counter:
			self.append('physical_examination', {
				'item_input': 'Abdominal Girth',
				'result': girth,
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
		AND td.appointment = %s AND td.docstatus = 0) ORDER BY idx""", (appointment), as_list=True)

def format_indonesian_safe(number_str):
	if number_str is None:
		return number_str
	try:
		number_str = str(number_str).strip()
		num_float = float(number_str)
		if num_float.is_integer():
			number = int(num_float)
		else:
			number = num_float
	except (ValueError, TypeError):
		return number_str
	if isinstance(number, int):
		return f"{number:,}".replace(',', '.')
	else:
		parts = f"{number:,.3f}".split('.')
		integer_with_commas = parts[0]
		decimal_part = parts[1].rstrip('0')
		integer_formatted = integer_with_commas.replace(',', '.')
		if decimal_part:
			return f"{integer_formatted},{decimal_part}"
		else:
			return integer_formatted