# Copyright (c) 2024, GIS and contributors
# For license information, please see license.txt

import frappe, io
from frappe.model.document import Document
from frappe.utils import cint
from frappe.utils.pdf import get_pdf
from frappe.utils.file_manager import save_file
from PyPDF2 import PdfMerger

class DoctorResult(Document):
	child_tables = ['nurse_grade', 'doctor_grade', 'radiology_grade', 'lab_test_grade']
	grade_order = ['A', 'B', 'BF', 'C', 'D', 'E', 'F']
	max_print_lines = 20

	def before_save(self):
		remarks = {
			row.description.strip()
			for child_name in self.child_tables
			for row in (self.get(child_name) or [])
			if row.grade and row.grade.split('-')[-1] != 'A' and row.description}
		dental_comments = _get_dental_comments(self.appointment) or []
		self.copied_remark = '\n'.join(sorted(remarks) + dental_comments)

	def before_submit(self):
		validation_result = self.validate_before_submit()
		if not validation_result['is_valid']:
			error_message = 'All results must be submitted, and all gradable must be graded.\n\nInvalid entries found:\n'
			for error in validation_result['errors']:
				error_message += f"Table: {error['table']}, Row: {error['row_idx']}, Item: {error['item_name']}\n"
			frappe.throw(error_message)
		self.process_physical_exam()
		self.process_other_exam()
		self.process_group_exam()
		self._create_doctor_result_pdf_report()

	def validate_before_submit(self):
		def is_valid(row):
			return not (
				(row.get('gradable') == 1 and not row.get('grade')) or
				(row.get('hidden_item_group') and row.get('hidden_item') and 
					row.get('is_item') == 0 and not row.get('result')
				)
			)
		def get_validation_reason(row):
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
							'reason': get_validation_reason(row)})
		return {
			'is_valid': len(validation_errors) == 0,
			'errors': validation_errors
		}

	def on_update_after_submit(self):
		if hasattr(self, '_in_on_update_after_submit'):
			return
		try:
			self._in_on_update_after_submit = True
			self.process_group_exam()
			self.process_other_exam()
			self.save()
			self._create_doctor_result_pdf_report()
		finally:
			self._in_on_update_after_submit = False
			
	def _create_doctor_result_pdf_report(self):
		prefixes = [
			('logo', 'doctor_result_print_format'),('nologo', 'doctor_result_print_format_no_logo')]
		for prefix, field_name in prefixes:
			pdf_contents = []
			print_format = frappe.db.get_single_value('MCU Settings', field_name)
			if not print_format:
				frappe.throw('Print Format not found. Please set up using MCU Settings.')
			pdf_contents.append(_generate_primary_pdf(self.doctype, self.name, print_format))
			unique_docs = _get_related_exam_docs(self)
			for doc in unique_docs:
				related_pdfs = _get_created_pdf_attachments(doc['document_type'], doc['document_name'], prefix)
				if related_pdfs:
					pdf_contents = _create_pdf_list(pdf_contents, related_pdfs)
				else:
					created_filename = _create_result_pdf_report(doc['document_type'], doc['document_name'], prefix)
					file_doc = frappe.get_doc('File', created_filename)
					pdf_contents.append(file_doc.get_content())
			output = _merge_pdfs(pdf_contents)
			filename = f'{self.name}{prefix}.pdf'
			existing_file = frappe.db.exists('File', {
				'file_name': ["like", f"{self.name}{prefix}%.pdf"],
				'attached_to_doctype': self.doctype,
				'attached_to_name': self.name})
			if existing_file:
				frappe.delete_doc('File', existing_file)
			save_file(filename, output, self.doctype, self.name, is_private=1)
		#print_format = frappe.db.get_single_value('MCU Settings', 'doctor_result_print_format')
		#if not print_format:
		#	frappe.throw('Please set the Doctor Result Print Format in MCU Settings.')
		#pdf_contents.append(_generate_primary_pdf(self.doctype, self.name, print_format))
		#unique_docs = _get_related_exam_docs(self)
		#for doc in unique_docs:
		#	related_pdfs = _get_created_pdf_attachments(doc['document_type'], doc['document_name'])
		#	if related_pdfs:
		#		pdf_contents = _create_pdf_list(pdf_contents, related_pdfs)
		#	else:
		#		created_filename = _create_result_pdf_report(doc['document_type'], doc['document_name'])
		#		file_doc = frappe.get_doc('File', created_filename)
		#		pdf_contents.append(file_doc.get_content())
		#output = _merge_pdfs(pdf_contents)
		#filename = f'{self.name}.pdf'
		#existing_file = frappe.db.exists('File', {
		#	'file_name': ["like", f"{self.name}%.pdf"],
		#	'attached_to_doctype': self.doctype,
		#	'attached_to_name': self.name})
		#if existing_file:
		#	frappe.delete_doc('File', existing_file)
		#save_file(filename, output, self.doctype, self.name, is_private=1)
		frappe.msgprint('MCU Result prints are ready and attached.')
		self.reload()

	def process_physical_exam(self):
		self.physical_examination = []
		self._process_questionnaire()
		self._process_nurse_grade()
		self._process_doctor_grade()

	def process_other_exam(self):
		self.other_examination = []
		current_results = self._collect_other_exam_results()
		prev_data, last_data = self._get_previous_results_map('other_examination', key='content', value='result')
		limit_per_page = cint(frappe.get_single_value('MCU Settings', 'max_lines_per_page'))
		if not limit_per_page:
			frappe.throw('Please set Max Lines per Page in MCU Settings. Please contact Administrator.')
		idx = 0
		for result in current_results:
			idx += 1
			additional_rows = get_additional_lines(idx, limit_per_page, 3)
			if additional_rows and result.get('header') == 'Group':
				for _ in range(additional_rows):
					idx += 1
					self.append('other_examination', {'header': result.get('header'),})
			self.append('other_examination', {
				'content': result.get('examination'),
				'result': result.get('result'),
				'uom': result.get('uom'),
				'std_value': result.get('std_value'),
				'header': result.get('header'),
				'previous_result': prev_data.get(result['examination'], '') if result.get('result') else None,
				'last_result': last_data.get(result['examination'], '') if result.get('result') else None,})

	def process_group_exam(self):
		self.group_exam = []
		current_results = self._collect_group_exam_results()
		prev_data, last_data = self._get_previous_results_map('group_exam', key='contents', value='result')
		for result in current_results:
			self.append('group_exam', {
				'contents': result['contents'],
				'result': result['result'],
				'previous_result': prev_data.get(result['contents'], '') if result['result'] else None,
				'last_result': last_data.get(result['contents'], '') if result['result'] else None,
			})

	def _collect_group_exam_results(self):
		results = []
		counter = 0
		for table in self.child_tables:
			for row in getattr(self, table, []):
				if not row.hidden_item:
					counter += 1
					pos = frappe.get_cached_value('Item Group', row.hidden_item_group, 'custom_bundle_position')
					if row.grade:
						if values := frappe.get_cached_value('MCU Grade', row.grade, ['grade', 'grade_on_report']):
							grade, grade_or = values
						else:
							grade, grade_or = None, None
					results.append({
							'contents': row.hidden_item_group,
							'result': grade if not grade_or else grade_or,
							'bundle_position': pos if pos else 9999,
							'idx': counter,})
		return sorted(results, key=lambda x: (x['bundle_position'], x['idx']))
	
	def _collect_other_exam_results(self):
		results, counter = [], 0
		for table in self.child_tables:
			for row in getattr(self, table, []):
				normalized = self._normalize_other_exam_row(row, table)
				if normalized:
					counter += 1
					normalized['idx'] = counter
					results.append(normalized)
		return sorted(results, key=lambda x: (x['bundle_position'], x['idx']))

	def _get_previous_results_map(self, child_table_name, key, value):
		prev_results = frappe.get_all('Doctor Result',
			filters={
				'patient': self.patient,
				'docstatus': 1,
				'created_date': ('<', self.created_date),
				'name': ('!=', self.name)},
			order_by = 'created_date desc', limit = 2)
		prev_data, last_data = {}, {}
		if prev_results:
			if len(prev_results) >= 1:
				prev_doc = frappe.get_doc("Doctor Result", prev_results[0].name)
				prev_data = {getattr(d, key): getattr(d, value) for d in getattr(prev_doc, child_table_name, [])}
			if len(prev_results) >= 2:
				last_doc = frappe.get_doc("Doctor Result", prev_results[1].name)
				last_data = {getattr(d, key): getattr(d, value) for d in getattr(last_doc, child_table_name, [])}
		return prev_data, last_data

	def _normalize_other_exam_row(self, row, table):
		if not row.hidden_item and row.hidden_item_group:
			return self._normalize_group_row(row, table)
		if row.hidden_item:
			if self._is_excluded_nurse_exam(row):
				return None
			exam, std_value, header = self._apply_special_case(row)
			urine_case = self._handle_urine_cases(row)
			if urine_case:
				return urine_case
			return self._build_exam_result(row, exam, std_value, header)
		return None

	def _normalize_group_row(self, row, table):
		pos = frappe.get_cached_value('Item Group', row.hidden_item_group, 'custom_bundle_position') or 9999
		comments = [
			p.incdec_category for p in getattr(self, table, [])
			if p.hidden_item_group == row.hidden_item_group and p.incdec_category
		]
		return {
			'examination': row.hidden_item_group,
			'result': None,
			'bundle_position': pos,
			'header': 'Group',
			'comments': ', '.join(comments) if comments else 'Dalam batas normal.'
		}

	def _is_excluded_nurse_exam(self, row):
		if row.parentfield not in ('nurse_grade', 'doctor_grade'):
			return False
		item_template = frappe.get_cached_value(
			'Nurse Examination Template', {'item_code': row.hidden_item}, 'name'
		)
		return (
			(item_template and item_template in vital_sign_templates()) 
			or row.hidden_item == physical_examination()
		)

	def _apply_special_case(self, row):
		exam, std_value, header = row.examination, row.std_value, None
		if exam == "HbA1c":
			exam = "<p>HbA1c</p><p align='right'>Pre - Diabetic</p><p align='right'>Diabetic</p>"
			std_value = "<p>&lt; 5.7</p><p align='right'>5.7 - 6.5</p><p align='right'>&#8805; 6.5</p>"
		elif exam == "Typoid IgM (Tubex)":
			exam = "<p>Typoid IgM (Tubex)</p>"
			exam += "<br/>Negative (does not indicate current typhoid fever infection)"
			exam += "<br/>Inconclusive (repeat test later)"
			exam += "<br/>Positive (higher score indicates stronger infection)"
			std_value = "&#8804; 2<br/><br/>&gt;2 - &lt;4<br/>4 - 10"
		elif exam == "Sputum Direct BTA":
			exam += (
				"<ul><li>Negative (Tidak ditemukan BTA / 100 Lapang Pandang)</li>"
				"<li>Scanty (1 - 9 BTA /100 Lapang Pandang)</li>"
				"<li>(1+) (10 - 99 BTA / 100 Lapang Pandang)</li>"
				"<li>(2+) (1 - 10 BTA / Lapang Pandang)</li>"
				"<li>(3+) (>10 BTA / Lapang Pandang)</li></ul>"
			)
		elif exam in ("Stool Culture", "Rectal Swab (Swab Culture)"):
			exam += (
				"<ul><li>Salmonella</li><li>Shigella</li>"
				"<li>Vibrio</li><li>Escherichia coli O157H7</li></ul>"
			)
		# mark as "Item" if it has hidden item + group + is_item flag
		if row.hidden_item and row.hidden_item_group and row.is_item and not row.result:
			header = "Item"
		return exam, std_value, header

	def _handle_urine_cases(self, row):
		if not hasattr(self, "_urine_state"):
			self._urine_state = {"rbc": "", "wbc": ""}
		if row.hidden_item != "MIRU-00001":
			return None
		if row.examination == "urine RBC atas":
			self._urine_state["rbc"] = row.result
			return None
		elif row.examination == "urine RBC bawah":
			return self._build_exam_result(
				row,
				examination="Urine RBC",
				result=self._urine_state["rbc"] + " - " + row.result,
			)
		elif row.examination == "urine WBC atas":
			self._urine_state["wbc"] = row.result
			return None
		elif row.examination == "urine WBC bawah":
			return self._build_exam_result(
				row,
				examination="Urine WBC",
				result=self._urine_state["wbc"] + " - " + row.result,
			)
		return None

	def _build_exam_result(self, row, examination=None, std_value=None, header=None, result=None):
		pos = frappe.get_cached_value('Item Group', row.hidden_item_group, 'custom_bundle_position') or 9999
		row_result = result or row.result
		row_result = format_indonesian_safe(row_result)
		arrow = '\u2193' if row.incdec == 'Decrease' else '\u2191' if row.incdec == 'Increase' else ''
		if row_result and arrow:
			row_result = f"<p style='color: red;'>{row_result} {arrow}</p>"
		return {
			'examination': examination or row.examination,
			'result': row_result,
			'bundle_position': pos,
			'uom': row.uom,
			'std_value': std_value or row.std_value,
			'header': header,
			'item_group': row.hidden_item_group,
			'item': row.hidden_item,
		}

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

def vital_sign_templates(): 
	return frappe.get_all(
		'MCU Vital Sign', filters = {'parentfield': 'vital_sign_on_report'}, pluck = 'template')

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

def _create_result_pdf_report(doctype, docname, prefix = None):
	def generate_pdf_for_prefix(prefix):
		print_format = _get_print_format(doctype, docname, prefix)
		pdf_contents = [_generate_primary_pdf(doctype, docname, print_format)]
		related_pdfs = _get_uploaded_pdf_attachments(doctype, docname)
		merged_pdf = _merge_pdfs(_create_pdf_list(pdf_contents, related_pdfs))
		filename = f'{docname}{prefix}.pdf'
		file = save_file(filename, merged_pdf, doctype, docname, is_private=1)
		return file.name

	prefixes = ['logo', 'nologo']
	file_names = []
	if not prefix:
		for p in prefixes:
			file_names.append(generate_pdf_for_prefix(p))
	elif prefix in prefixes:
		file_names.append(generate_pdf_for_prefix(prefix))
	else:
		frappe.throw('Unknown Print Format prefix. Please contact Administrator.')
	return file_names[0] if prefix else None

def _get_print_format(doctype, docname, prefix):
	hsu = frappe.db.get_value(doctype, docname, 'service_unit')
	if not hsu:
		frappe.throw(
			f"Healthcare Service Unit is not set for {doctype} {docname}. Cannot create PDF report.")
	if prefix == 'logo':
		print_format = frappe.db.get_value('Healthcare Service Unit', hsu, 'custom_default_print_format')
	else:
		print_format = frappe.db.get_value('Healthcare Service Unit', hsu, 'custom_default_print_format_without_logo')
	if not print_format:
		frappe.throw(
			f"Please set the Default Print Format for Healthcare Service Unit {hsu}. Cannot create PDF report.")
	return print_format

def _generate_primary_pdf(doctype, docname, print_format):
	html = frappe.get_print(doctype, docname, print_format)
	pdf_content = get_pdf(html)
	if not pdf_content:
		frappe.throw(f"Failed to generate primary PDF for {doctype} {docname}.")
	return pdf_content

def _get_uploaded_pdf_attachments(doctype, docname):
	return frappe.get_all('File', 
		filters={
			"attached_to_doctype": doctype, "attached_to_name": docname, 
			"file_type": 'PDF', 'file_name': ('not like', f'{docname}%')},
		pluck='name') or []

def _get_created_pdf_attachments(doctype, docname, prefix):
	return frappe.get_all('File', 
		filters={
			"attached_to_doctype": doctype, "attached_to_name": docname, 
			"file_type": 'PDF', 'file_name': ('not like', f'{docname}{prefix}%')},
		pluck='name') or []

def _create_pdf_list(pdf_list, related_files):
	for file_name in related_files:
		try:
			file_doc = frappe.get_doc('File', file_name)
			pdf_list.append(file_doc.get_content())
		except Exception:
			frappe.log_error(frappe.get_traceback(), f"Failed to read content of attached file: {file_name}")
	return pdf_list

def _merge_pdfs(pdf_contents):
	if not pdf_contents:
		return b''
	merger = PdfMerger()
	for content in pdf_contents:
		merger.append(io.BytesIO(content))
	with io.BytesIO() as output:
		merger.write(output)
		merger.close()
		return output.getvalue()
	
def recreate_doctor_result_pdf_report(id):
	doc = frappe.get_doc('Doctor Result', id)
	doc._create_doctor_result_pdf_report()

def _get_related_exam_docs(doc):
	child_mappings = [
		{'nurse_grade', 'Nurse Result'},
		{'radiology_grade', 'Radiology Result'},
	]
	docs = []
	for table_name, expected_type in child_mappings:
		for row in getattr(doc, table_name, []):
			if row.document_type == expected_type and row.document_name:
				docs.append({
					'document_type': row.document_type,
					'document_name': row.document_name,
				})
	return list({d['document_name']: d for d in docs}.values())

def get_additional_lines(row_number: int, base_number: int, limit: int = 3) -> int:
	if base_number < limit:
		frappe.throw(f'Base number must be bigger than limit ({limit}).')
	offset = row_number % base_number
	if offset == 0:
		return 1
	elif offset > base_number - limit:
		return base_number - offset + 1
	return 0