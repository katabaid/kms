# Copyright (c) 2024, GIS and contributors
# For license information, please see license.txt

import frappe, re
from frappe.model.document import Document
from frappe.utils import today, flt
from frappe import _
from statistics import mean

class Dispatcher(Document):
	def after_insert(self):
		if self.name:
			self.queue_no = self.name.split('-')[-1].lstrip('0')
			self.db_update()

	def validate(self):
		self.progress = self.calculate_progress()
		if self.status == "In Queue":
			self.update_status_if_all_rooms_finished()
		if self.status == "Finished" and self.status_changed_to_finished():
			self.update_patient_appointment()
			#self.create_doctor_result()
	
	def before_insert(self):
		if frappe.db.exists(self.doctype,{
			'patient_appointment': self.patient_appointment,
			'date': self.date,
		}):
			frappe.throw(_("Patient already in Dispatcher's queue."))

	def update_status_if_all_rooms_finished(self):
		finished_statuses = {'Refused', 'Finished', 'Rescheduled', 'Partial Finished'}
		if all(room.status in finished_statuses for room in self.assignment_table):
			self.status = 'Waiting to Finish'

	def status_changed_to_finished(self):
		doc_before_save = self.get_doc_before_save()
		return doc_before_save and doc_before_save.status != "Finished"

	def update_patient_appointment(self):
		if self.patient_appointment:
			status = frappe.db.get_value('Patient Appointment', self.patient_appointment, 'status')
			if status not in {"Closed", "Checked Out", "Ready to Check Out"}:
				frappe.db.set_value('Patient Appointment', self.patient_appointment, 'status', 'Ready to Check Out')
		else:
			frappe.msgprint(_("No linked Patient Appointment found."))
	
	def create_doctor_result(self):
		doc = frappe.new_doc('Doctor Result')
		doc.appointment = self.patient_appointment
		doc.patient = self.patient
		doc.age = frappe.db.get_value('Patient Appointment', self.patient_appointment, 'patient_age')
		doc.gender = self.gender
		doc.dispatcher = self.name
		doc.created_date = today()
		package_line = frappe.db.sql(f"""SELECT DISTINCT examination_item, item_name, item_group,
			(select custom_gradable from `tabItem Group` tig 
				where tig.name = item_group) group_gradable, 
			(select custom_bundle_position from `tabItem Group` tig 
				where tig.name = item_group) group_position,
			(select custom_gradable from `tabItem` ti 
				where ti.name = examination_item) item_gradable, 
			(select custom_bundle_position from `tabItem` ti 
				where ti.name = examination_item) item_position,
			(select 1 from `tabNurse Examination Template` tnet 
				where tnet.item_code = examination_item) nurse,
			(select 1 from `tabDoctor Examination Template` tnet 
				where tnet.item_code = examination_item) doctor,
			(select 1 from `tabRadiology Result Template` tnet 
				where tnet.item_code = examination_item) radiology,
			(select 1 from `tabLab Test Template` tnet 
				where tnet.lab_test_code = examination_item) lab_test
			from `tabMCU Appointment`
			where parent = '{self.patient_appointment}'""", as_dict = True)
		group_result = get_examination_items(package_line)
		process_examination_items(doc, group_result, self.package)
		doc.insert()

	def calculate_progress(self):
		child_items = frappe.get_all(
			'MCU Appointment', filters={'parent': self.name}, fields=['status'])
		if not child_items:
			return 0
		else:
			return round(mean([100 if item.status == 'Finished' else 0 for item in child_items]))

def convert_to_float(value):
	return float(str(value).replace(",", "."))

def is_within_range(value, min_value, max_value):
	return min_value < value < max_value

def get_examination_items(sql):
	def group_and_sort(data, key):
		filtered_data = [row for row in data if row.get(key) is not None]
		grouped_data = {}
		for row in filtered_data:
			group = row['item_group']
			if group not in grouped_data:
				grouped_data[group] = {
					'item_group': group,
					'group_gradable': row['group_gradable'],
					'group_position': row['group_position'],
					'items': []
				}
			grouped_data[group]['items'].append({
				'examination_item': row['examination_item'],
				'item_name': row['item_name'],
				'item_gradable': row['item_gradable'],
				'item_position': row['item_position'],
			})
		for group in grouped_data.values():
			group['items'] = sorted(group['items'], key=lambda x: x['item_position'])
		sorted_data = sorted(grouped_data.values(), key=lambda x: x['group_position'])
		return sorted_data
	nurse_array = group_and_sort(sql, 'nurse')
	radiology_array = group_and_sort(sql, 'radiology')
	lab_array = group_and_sort(sql, 'lab_test')
	return {
		'nurse': nurse_array,
		'radiology': radiology_array,
		'lab_test': lab_array,
	}

def process_examination_items(doc, data, package):
	def calculate_blood_pressure(appointment):
		exams = frappe.get_all(
			'Nurse Examination',
			filters = {'appointment': appointment, 'docstatus':  1},
			pluck = 'name'
		)
		for exam in exams:
			systolic = frappe.db.get_value(
				'Nurse Examination Result', 
				{'parent': exam, 'test_name': 'Systolic'}, 
				'result_value'
			)
			diastolic = frappe.db.get_value(
				'Nurse Examination Result', 
				{'parent': exam, 'test_name': 'Diastolic'}, 
				'result_value'
			)
			if systolic and diastolic:
				systolic = int(systolic)
				diastolic = int(diastolic)
				break
		if systolic and diastolic:
			if systolic < 120 and diastolic <80:
				return 'Normal'
			if (systolic >= 120 and systolic <140) or (diastolic >=80 and diastolic <90):
				return 'Prehypertension'
			if (systolic >= 140 and systolic <160) or (diastolic >=90 and diastolic <100):
				return 'Stage 1 Hypertension'
			if systolic >= 160 or diastolic >=100:
				return 'Stage 2 Hypertension'
		return None

	def get_radiology_result(appointment, item_code, item_name):
		column = frappe.db.get_value('Radiology Result Template', item_name, 'diagnose_column')
		if column:
			exams = frappe.db.get_all(
				'Radiology Result', 
				filters = {'appointment': appointment, 'docstatus': 1}, 
				pluck = 'name'
			)
			for exam in exams:
				for line in exam.result:
					if line.item_code == item_code and line.result_line == column:
						return line.result_text
		else:
			return None

	def append_items(category, group, item, doc, additional_data=None):
		data = {
			'examination': item['item_name'],
			'gradable': item.get('item_gradable', 0),
			'hidden_item_group': group['item_group'],
			'hidden_item': item['examination_item'],
			**(additional_data or {})
		}
		doc.append(f"{category}_grade", data)

	blood_pressure = frappe.db.get_single_value('MCU Settings', 'vital_sign_with_systolicdiastolic')
	blood_pressure_item_code = (
		frappe.db.get_value('Nurse Examination Template', blood_pressure, 'item_code') 
		if blood_pressure else None)
	for category, groups in data.items():
		for group in groups:
			doc.append(f"{category}_grade", {
				'examination': group['item_group'],
				'gradable': group['group_gradable'],
				'hidden_item_group': group['item_group'],
			})
			for item in group['items']:
				print(item)
				radiology_result = None
				incdec = None
				if blood_pressure_item_code == item['examination_item']:
					incdec = calculate_blood_pressure(doc.appointment)
				if category == 'radiology':
					radiology_result = get_radiology_result(
						doc.appointment, item['examination_item'], item['item_name'])
				append_items(
					category, group, item, doc,
					additional_data={'result': radiology_result, 'incdec': incdec, 'is_item': 1}
				)
				if category == 'nurse':
					diagnose_column = frappe.db.get_value(
						'Nurse Examination Template', item['examination_item'], 'diagnose_column')
					if diagnose_column:
						append_items(
							category, group, item, doc,
							additional_data={'is_item': 1}
						)
					else:
						process_nurse_category(doc, group, item)
				elif category == 'lab_test':
					process_lab_test_category(doc, group, item)
	process_doctor_category(doc, package)

def calculate_grade(result_text, min_value, max_value, group, item_code, test_name):
	if not (result_text and min_value and max_value):
		return None, None
	result_value = flt(result_text)
	if flt(min_value) <= result_value <= flt(max_value):
		grade = 'A'
		grade_description = frappe.db.get_value(
			'MCU Grade',
			{'item_group': group, 'item_code': item_code, 'test_name': test_name, 'grade': grade},
			'description'
		)
		if grade_description:
			return grade, grade_description
	return None, None

def process_nurse_category(doc, group, item):
	nurse_grades = build_nurse_grade(
		group['item_group'], item['examination_item'], item['item_name'], doc.appointment)
	for nurse_grade in nurse_grades:
		grade, grade_description = calculate_grade(
			nurse_grade.result_text, nurse_grade.min_value, nurse_grade.max_value,
			group['item_group'], item['examination_item'], nurse_grade.result_line
		)
		incdec = nurse_grade.incdec.split('|||') if nurse_grade.incdec else ['', '']
		if nurse_grade.result_line == 'BMI':
			bmi_rec = frappe.db.get_all(
				'BMI Classification', fields=['name', 'min_value', 'max_value', 'grade'])
			exam_result_float = convert_to_float(nurse_grade.result_text)
			for bmi in bmi_rec:
				min_value_float = convert_to_float(bmi['min_value'])
				max_value_float = convert_to_float(bmi['max_value'])
				if is_within_range(exam_result_float, min_value_float, max_value_float):
					grade = bmi['grade']
					grade_description = frappe.db.get_value(
						'MCU Grade',
						f"{group['item_group']}.{item['examination_item']}.BMI{bmi['name']}",
						'description'
					)
					category = frappe.db.get_value(
						'MCU Category', 
						f"{group['item_group']}.{item['examination_item']}.BMI.{bmi['name']}",
						'description'
					)
					incdec = [bmi['name'], category]
					break
		doc.append('nurse_grade', {
			'examination': nurse_grade.result_line,
			'gradable': nurse_grade.gradable,
			'result': nurse_grade.result_text,
			'min_value': nurse_grade.min_value,
			'max_value': nurse_grade.max_value,
			'grade': grade,
			'description': grade_description,
			'uom': nurse_grade.uom,
			'status': nurse_grade.status,
			'document': nurse_grade.doc,
			'incdec': incdec[0],
			'incdec_category': incdec[1] if len(incdec) > 1 else '',
			'hidden_item_group': group['item_group'],
			'hidden_item': item['examination_item']
		})

def process_doctor_category(doc, package):
	def split_position(pos):
		pos = str(pos)
		return [int(part) if part.isdigit() else part for part in pos.split('-')]
	def flatten_grades(grades):
		flat = []
		for grade in grades:
			if isinstance(grade, list):
				flat.extend(flatten_grades(grade))  # Recursively flatten
			else:
				flat.append(grade)
		return flat
	doctor_grades = build_doctor_grade(doc.appointment, package)
	flat_grades = flatten_grades(doctor_grades)
	filtered_grades = [grade for grade in flat_grades if grade is not None]
	sorted_temp = sorted(filtered_grades, key=lambda x: split_position(x.get('position', '')))
	for ready in sorted_temp:
		doc.append('doctor_grade', {
			'examination': ready.get('examination'),
			'gradable': ready.get('gradable'),
			'result': ready.get('result'),
			'min_value': ready.get('min_value'),
			'max_value': ready.get('max_value'),
			'grade': ready.get('grade'),
			'uom': ready.get('uom'),
			'status': ready.get('status'),
			'document': ready.get('document'),
			'incdec': ready.get('incdec'),
			'incdec_category': ready.get('incdec_category'),
			'hidden_item_group': ready.get('hidden_item_group'),
			'hidden_item': ready.get('hidden_item'),
			'is_item': ready.get('is_item'),
		})

def process_lab_test_category(doc, group, item):
	lab_test_grades = build_lab_test_grade(
		group['item_group'], item['examination_item'], item['item_name'], doc.appointment)
	for lab_test_grade in lab_test_grades:
		grade, grade_description = calculate_grade(
			lab_test_grade.result_text, lab_test_grade.min_value, lab_test_grade.max_value,
			group['item_group'], item['examination_item'], lab_test_grade.result_line
		)
		incdec = lab_test_grade.incdec.split('|||') if lab_test_grade.incdec else ['', '']
		doc.append( 'lab_test_grade', {
			'examination': lab_test_grade.result_line,
			'gradable': lab_test_grade.gradable,
			'result': lab_test_grade.result_text,
			'min_value': lab_test_grade.min_value,
			'max_value': lab_test_grade.max_value,
			'grade': grade,
			'description': grade_description,
			'uom': lab_test_grade.uom,
			'status': lab_test_grade.status,
			'document': lab_test_grade.doc,
			'incdec': incdec[0],
			'incdec_category': incdec[1] if len(incdec) > 1 else '',
			'hidden_item_group': group['item_group'],
			'hidden_item': item['examination_item']
		})

def build_lab_test_grade(item_group, item_code, item_name, appointment):
	sql = f"""
		SELECT tntr.idx, lab_test_event AS result_line, custom_min_value AS min_value, 
		custom_max_value AS max_value, result_value AS result_text, lab_test_uom AS uom, 
		tlt.name AS doc, tlt.status AS status,
		CASE WHEN custom_min_value IS NOT NULL 
			AND custom_max_value IS NOT NULL 
			AND (custom_min_value <> 0 OR custom_max_value <> 0) 
			AND result_value IS NOT NULL THEN
			CASE WHEN result_value > custom_max_value THEN 
				CONCAT_WS(
					'|||', 
					'Increase', 
					(SELECT tmc.description FROM `tabMCU Category` tmc 
						WHERE tmc.item_group = '{item_group}' 
						AND tmc.item = '{item_code}' 
						AND tmc.test_name = lab_test_event 
						AND tmc.selection = 'Increase'
					)
				) 
			WHEN result_value < custom_min_value THEN 
				CONCAT_WS(
					'|||', 
					'Decrease', 
					(SELECT tmc.description FROM `tabMCU Category` tmc 
						WHERE tmc.item_group = '{item_group}' 
						AND tmc.item = '{item_code}' 
						AND tmc.test_name = lab_test_event 
						AND tmc.selection = 'Decrease'
					)
				) 
			ELSE NULL END 
		ELSE NULL END AS incdec,
		IFNULL(
			(SELECT 1 FROM `tabMCU Grade` tmg 
				WHERE tmg.item_group = '{item_group}' 
				AND tmg.item_code = '{item_code}' 
				AND test_name = lab_test_event 
				LIMIT 1), 
			0) AS gradable
		FROM `tabNormal Test Result` tntr, `tabLab Test` tlt 
		WHERE tntr.parent = tlt.name AND tlt.custom_appointment = '{appointment}' 
		AND tlt.docstatus IN (0, 1) AND tntr.lab_test_name = '{item_name}'
		UNION
		SELECT tstt.idx, event, NULL, NULL, result, NULL, tlt.name, tlt.status, NULL, 0
		FROM `tabSelective Test Template` tstt, `tabLab Test` tlt 
		WHERE tstt.parent = tlt.name AND tlt.custom_appointment = '{appointment}' 
		AND tlt.docstatus IN (0, 1) AND event = '{item_name}' ORDER BY idx"""
	return frappe.db.sql(sql, as_dict = True)

def build_nurse_grade(item_group, item_code, item_name, appointment):
	sql = f"""
		SELECT tner.idx AS idx, test_name AS result_line, FORMAT(min_value, 2) AS min_value, 
		FORMAT(max_value, 2) AS max_value, FORMAT(result_value, 2) AS result_text, 
		test_uom AS uom, tne.name AS doc, tnerq.status AS status, 
		CASE 
			WHEN min_value IS NOT NULL 
			AND max_value IS NOT NULL 
			AND (min_value <> 0 OR max_value <> 0) 
			AND result_value IS NOT NULL THEN
			CASE WHEN result_value > max_value THEN 
				CONCAT_WS(
					'|||', 
					'Increase', 
					(SELECT tmc.description FROM `tabMCU Category` tmc 
						WHERE tmc.item_group = '{item_group}' 
						AND tmc.item = '{item_code}' 
						AND tmc.test_name = test_name 
						AND tmc.selection = 'Increase'
					)
				) 
			WHEN result_value < min_value THEN 
				CONCAT_WS(
					'|||', 
					'Decrease', 
					(SELECT tmc.description FROM `tabMCU Category` tmc 
						WHERE tmc.item_group = '{item_group}' 
						AND tmc.item = '{item_code}' 
						AND tmc.test_name = test_name 
						AND tmc.selection = 'Decrease'
					)
				) 
			ELSE NULL END 
		ELSE NULL END AS incdec,
		IFNULL(
			(SELECT 1 FROM `tabMCU Grade` tmg 
				WHERE tmg.item_group = '{item_group}' 
				AND tmg.item_code = '{item_code}' 
				AND tmg.test_name = tner.test_name 
				LIMIT 1
			), 
			0
		) AS gradable
		FROM `tabNurse Examination Result` tner, `tabNurse Examination` tne, 
			`tabNurse Examination Request` tnerq
		WHERE tne.name = tner.parent AND tne.appointment = '{appointment}' AND tne.docstatus = 1 
		AND tner.item_code = '{item_code}' AND tnerq.parent = tne.name 
		AND EXISTS (SELECT 1 FROM `tabNurse Examination Template` tnet 
			WHERE tnet.item_code = tner.item_code AND tnerq.template = tnet.item_name)
		UNION
		SELECT tnesr.idx+100, result_line, NULL, NULL, result_text, result_check, tne.name, 
			tnerq.status, NULL, 0
		FROM `tabNurse Examination Selective Result` tnesr, `tabNurse Examination` tne, 
			`tabNurse Examination Request` tnerq
		WHERE tne.name = tnesr.parent AND tne.appointment = '{appointment}' AND tne.docstatus = 1 
		AND tnesr.item_code = '{item_code}' AND tnerq.parent = tne.name 
		AND EXISTS (SELECT 1 FROM `tabNurse Examination Template` tnet 
			WHERE tnet.item_code = tnesr.item_code AND tnerq.template = tnet.item_name)
		UNION
		SELECT tce.idx+200, test_label, NULL, NULL, FORMAT(result, 2), NULL, tne.name, 
			tnerq.status, NULL, 0
		FROM `tabCalculated Exam` tce, `tabNurse Examination` tne, `tabNurse Examination Request` tnerq
		WHERE tne.name = tce.parent AND tne.appointment = '{appointment}' AND tne.docstatus = 1 
		AND tce.item_code = '{item_code}' AND tnerq.parent = tne.name 
		AND EXISTS (SELECT 1 FROM `tabNurse Examination Template` tnet 
			WHERE tnet.item_code = tce.item_code AND tnerq.template = tnet.item_name)
		UNION
		SELECT tner.idx+300 AS idx, test_name AS result_line, FORMAT(min_value, 2) AS min_value, 
			FORMAT(max_value, 2) AS max_value, FORMAT(result_value, 2) AS result_text, 
			test_uom AS uom, tnr.name AS doc, tnerq.status AS status, 
		CASE 
			WHEN min_value IS NOT NULL 
			AND max_value IS NOT NULL 
			AND (min_value <> 0 OR max_value <> 0) 
			AND result_value IS NOT NULL THEN
			CASE WHEN result_value > max_value THEN 
				CONCAT_WS(
					'|||', 
					'Increase', 
					(SELECT tmc.description FROM `tabMCU Category` tmc 
						WHERE tmc.item_group = '{item_group}' 
						AND tmc.item = '{item_code}' 
						AND tmc.test_name = test_name 
						AND tmc.selection = 'Increase'
					)
				) 
			WHEN result_value < min_value THEN 
				CONCAT_WS(
					'|||', 
					'Decrease', 
					(SELECT tmc.description FROM `tabMCU Category` tmc 
						WHERE tmc.item_group = '{item_group}' 
						AND tmc.item = '{item_code}' 
						AND tmc.test_name = test_name 
						AND tmc.selection = 'Decrease'
					)
				) 
			ELSE NULL END 
		ELSE NULL END AS incdec,
		IFNULL(
			(SELECT 1 FROM `tabMCU Grade` tmg 
				WHERE tmg.item_group = '{item_group}' 
				AND tmg.item_code = '{item_code}' 
				AND tmg.test_name = tner.test_name 
				LIMIT 1), 
			0) AS gradable
		FROM `tabNurse Examination Result` tner, `tabNurse Result` tnr, 
			`tabNurse Examination Request` tnerq
		WHERE tnr.name = tner.parent AND tnr.appointment = '{appointment}' 
		AND tnr.docstatus IN (0,1) AND tner.item_code = '{item_code}' AND tnerq.parent = tnr.name
		AND EXISTS (SELECT 1 FROM `tabNurse Examination Template` tnet 
			WHERE tnet.item_code = tner.item_code AND tnerq.template = tnet.item_name 
			AND tnet.result_in_exam = 0)
		UNION
		SELECT tnesr.idx+400, result_line, NULL, NULL, result_text, result_check, tnr.name, 
			tnerq.status, NULL, 0
		FROM `tabNurse Examination Selective Result` tnesr, `tabNurse Result` tnr, 
			`tabNurse Examination Request` tnerq
		WHERE tnr.name = tnesr.parent AND tnr.appointment = '{appointment}' 
		AND tnr.docstatus IN (0,1)
		AND tnesr.item_code = '{item_code}' AND tnerq.parent = tnr.name 
		AND EXISTS (SELECT 1 FROM `tabNurse Examination Template` tnet 
			WHERE tnet.item_code = tnesr.item_code AND tnerq.template = tnet.item_name 
			AND tnet.result_in_exam = 0)
		ORDER BY 1"""
	return frappe.db.sql(sql, as_dict = True)

def build_doctor_grade(appointment, package):
	def build_single_exams():
		fields = [
			('physical_examination_name', 'physical_examination'),
			('visual_field_test_name', 'visual_field_test'),
			('romberg_test_name', 'romberg_test'),
			('tinnel_test_name', 'tinnel_test'),
			('phallen_test_name', 'phallen_test'),
			('rectal_test_name', 'rectal_test'),
			('dental_examination_name', 'dental_examination'),
		]
		return [{
			'item_code': frappe.db.get_single_value('MCU Settings', item_name),
			'item_name': frappe.db.get_single_value('MCU Settings', field_name),
			'code': item_name} for field_name, item_name in fields]

	def prepare_item_and_group(item, previous_exam_item_group, previous_exam_item):
		temp_doc = []
		group_gradable, group_pos = frappe.db.get_value(
			'Item Group', item.item_group, ['custom_gradable', 'custom_bundle_position'])
		item_gradable, item_pos = frappe.db.get_value(
			'Item', item.examination_item, ['custom_gradable', 'custom_bundle_position'])

		if previous_exam_item_group != item.item_group:
			previous_exam_item_group = item.item_group
			temp_doc.append({
				'examination': item.item_group,
				'gradable': group_gradable,
				'hidden_item_group': item.item_group,
				'position': group_pos,
			})
		if previous_exam_item != item.examination_item:
			previous_exam_item = item.examination_item
			temp_doc.append({
				'examination': item.item_name,
				'gradable': item_gradable,
				'hidden_item_group': item.item_group,
				'hidden_item': item.examination_item,
				'position': item_pos,
				'is_item': 1,
			})
		return temp_doc, item_pos

	def process_result_tables(doctor_exam, item_group, item_code, status, pos):
		counter = 0
		temp_doc = []
		for selective in doctor_exam.result:
			if selective.item_code == item_code:
				counter += 1
				temp_doc.append({
					'examination': selective.result_line,
					'gradable': 0,
					'result': ': '.join(filter(None, [
						selective.result_check or '', 
						selective.result_text or ''])),
					'status': status,
					'document': doctor_exam.name,
					'hidden_item_group': item_group,
					'hidden_item': item_code,
					'position': str(pos) + f'-{str(counter).zfill(2)}',})

		for non_selective in doctor_exam.non_selective_result:
			if non_selective.item_code == item_code:
				gradable = frappe.db.exists(
					'MCU Grade', 
					{
						'item_group': item_group, 
						'item_code': item_code, 
						'test_name': non_selective.test_name
					})
				grade = ''
				grade_description = ''
				incdec = ''
				incdec_category = ''
				is_within_range = (non_selective.result_value >= non_selective.min_value 
					and non_selective.result_value <= non_selective.max_value)
				if non_selective.result_value and non_selective.min_value and non_selective.max_value:
					if gradable and is_within_range:
						grade = 'A'
						grade_description = frappe.db.get_value(
							'MCU Grade', 
							{
								'item_group': item_group, 
								'item_code': item_code, 
								'test_name': non_selective.test_name, 
								'grade': 'A'
							},
							'description',
							as_dict = 1)
					if non_selective.result_value<non_selective.min_value:
						incdec = 'Decrease'
					if non_selective.result_value>non_selective.max_value:
						incdec = 'Increase'
					if incdec:
						incdec_category = frappe.db.get_value(
							'MCU Category',
							{
								'item_group': item_group, 
								'item_code': item_code, 
								'test_name': non_selective.test_name, 
								'selection': incdec
							},
							'description'
						)
				counter += 1
				temp_doc.append({
					'examination': non_selective.test_name,
					'gradable': 1 if gradable else 0,
					'result': non_selective.result_value,
					'min_value': non_selective.min_value,
					'max_value': non_selective.max_value,
					'grade': grade if grade else None,
					'description': grade_description if grade_description else None,
					'uom': non_selective.uom,
					'status': status,
					'document': doctor_exam.name,
					'incdec': incdec if incdec else None,
					'incdec_category': incdec_category if incdec_category else None,
					'hidden_item_group': item_group,
					'hidden_item': item_code,
					'position': str(pos) + f'-{str(counter).zfill(2)}',})

	def process_doc_tabs(doctor_tab, doctor_exam, item_group, item_code, status, pos):
		temp = []
		if doctor_tab == 'physical_examination':
			temp = process_physical_examination(doctor_exam, item_group, item_code, status, pos)
		elif doctor_tab == 'visual_field_test':
			temp = process_visual_field_test(doctor_exam, item_group, item_code, status, pos)
		elif doctor_tab == 'romberg_test':
			temp = process_romberg_test(doctor_exam, item_group, item_code, status, pos)
		elif doctor_tab == 'tinnel_test':
			temp = process_tinnel_test(doctor_exam, item_group, item_code, status, pos)
		elif doctor_tab == 'phallen_test':
			temp = process_phallen_test(doctor_exam, item_group, item_code, status, pos)
		elif doctor_tab == 'rectal_test':
			temp = process_rectal_test(doctor_exam, item_group, item_code, status, pos)
		elif doctor_tab == 'dental_examination':
			pass
		return temp

	single_exams = build_single_exams()
	doctor_exam_names = frappe.get_all(
		'Doctor Examination', {'docstatus': 1, 'appointment': appointment})
	item_group_list = []
	doc_tabs_list = []
	result_tables_list = []
	for doctor_exam_name in doctor_exam_names:
		prev_group = prev_item = ''
		doctor_exam = frappe.get_doc('Doctor Examination', doctor_exam_name.name)
		for exam_item in doctor_exam.examination_item:
			item = [item for item in package if item.item_name == exam_item.template]
			disp_item = item[0]
			temp_item_group, item_pos = prepare_item_and_group(disp_item, prev_group, prev_item)
			item_group_list.append(temp_item_group)
			doctor_tabs = [item for item in single_exams if item['item_code'] == disp_item.examination_item]
			if doctor_tabs:
				doctor_tab = doctor_tabs[0]
				temp_doc_tabs = process_doc_tabs(
					doctor_tab['code'], 
					doctor_exam, 
					disp_item.item_group, 
					disp_item.examination_item, 
					disp_item.status, 
					item_pos)
				doc_tabs_list.append(temp_doc_tabs)
			else:
				temp_result_tables = process_result_tables(
					doctor_exam, disp_item.item_group, disp_item.examination_item, disp_item.status, item_pos)
				result_tables_list.append(temp_result_tables)
			prev_group = disp_item.item_group
			prev_item = disp_item.examination_item
	return item_group_list + result_tables_list + doc_tabs_list

def process_physical_examination(doctor_exam, item_group, item_code, status, pos):
	temp = []
	temp.append(process_eyes(doctor_exam, item_group, item_code, status, pos))
	temp.append(process_ears(doctor_exam, item_group, item_code, status, pos))
	temp.append(process_nose(doctor_exam, item_group, item_code, status, pos))
	temp.append(process_throat(doctor_exam, item_group, item_code, status, pos))
	temp.append(process_neck(doctor_exam, item_group, item_code, status, pos))
	temp.append(process_cardiac(doctor_exam, item_group, item_code, status, pos))
	temp.append(process_breast(doctor_exam, item_group, item_code, status, pos))
	temp.append(process_resp(doctor_exam, item_group, item_code, status, pos))
	temp.append(process_abdomen(doctor_exam, item_group, item_code, status, pos))
	temp.append(process_spine(doctor_exam, item_group, item_code, status, pos))
	temp.append(process_genit(doctor_exam, item_group, item_code, status, pos))
	temp.append(process_neuro(doctor_exam, item_group, item_code, status, pos))
	temp.append(process_skin(doctor_exam, item_group, item_code, status, pos))
	return temp

def process_visual_field_test(doctor_exam, item_group, item_code, status, pos):
	result_line = 'Visual Field Test'
	if not doctor_exam.visual_check:
		result = doctor_exam.visual_details
	else:
		result = 'Same As Examiner'
	return {
		'examination': result_line,
		'gradable': 0,
		'result': result,
		'status': status,
		'document': doctor_exam.name,
		'hidden_item_group': item_group,
		'hidden_item': item_code,
		'position': str(pos) + '-1',}

def process_romberg_test(doctor_exam, item_group, item_code, status, pos):
	result_line = 'Romberg Test'
	if not doctor_exam.romberg_check:
		result = '\n'.join(filter(None, 
			[doctor_exam.romberg_abnormal or '', doctor_exam.romberg_others or '']))
	else:
		result = 'No Abnormality'
	return {
		'examination': result_line,
		'gradable': 0,
		'result': result,
		'status': status,
		'document': doctor_exam.name,
		'hidden_item_group': item_group,
		'hidden_item': item_code,
		'position': str(pos) + '-1',}

def process_tinnel_test(doctor_exam, item_group, item_code, status, pos):
	result_line = 'Tinnel Test'
	if not doctor_exam.tinnel_check:
		result = doctor_exam.tinnel_details
	else:
		result = 'No Abnormality'
	return {
		'examination': result_line,
		'gradable': 0,
		'result': result,
		'status': status,
		'document': doctor_exam.name,
		'hidden_item_group': item_group,
		'hidden_item': item_code,
		'position': str(pos) + '-1',}

def process_phallen_test(doctor_exam, item_group, item_code, status, pos):
	result_line = 'Phallen Test'
	if not doctor_exam.phallen_check:
		result = doctor_exam.phallen_details
	else:
		result = 'No Abnormality'
	return {
		'examination': result_line,
		'gradable': 0,
		'result': result,
		'status': status,
		'document': doctor_exam.name,
		'hidden_item_group': item_group,
		'hidden_item': item_code,
		'position': str(pos) + '-1',}

def process_rectal_test(doctor_exam, item_group, item_code, status, pos):
	result_line = 'Rectal Test'
	if not doctor_exam.rectal_check:
		if (
			not doctor_exam.rectal_hemorrhoid 
			and not doctor_exam.enlarged_prostate 
			and not doctor_exam.re_others):
			result = 'No Abnormality'
		else:
			result_list = []
			if doctor_exam.rectal_hemorrhoid:
				result_list.append(doctor_exam.rectal_hemorrhoid)
			if doctor_exam.enlarged_prostate:
				result_list.append('Enlarged Prostate')
			if doctor_exam.re_others:
				result_list.append(f'Other ({doctor_exam.rectal_others})')
			result = ','.join(result_list)
	else:
		result = 'No Abnormality'
	return {
		'examination': result_line,
		'gradable': 0,
		'result': result,
		'status': status,
		'document': doctor_exam.name,
		'hidden_item_group': item_group,
		'hidden_item': item_code,
		'position': str(pos) + '-1',}

def process_eyes(doctor_exam, item_group, item_code, status, pos):
	result_line = 'Eyes'
	if not doctor_exam.eyes_check:
		if (not doctor_exam.left_anemic 
			and not doctor_exam.left_icteric 
			and not doctor_exam.el_others):
			result = 'Left: No Abnormality'
		else:
			result_list = []
			if doctor_exam.left_anemic:
				result_list.append('Anemic')
			if doctor_exam.left_icteric:
				result_list.append('Icteric')
			if doctor_exam.el_others:
				result_list.append(f'Other ({doctor_exam.eyes_left_others})')
			result = 'Left: ' + ','.join(result_list)
		if (not doctor_exam.right_anemic 
			and not doctor_exam.right_icteric 
			and not doctor_exam.er_others):
			result += '\nRight: No Abnormality'
		else:
			result_list = []
			if doctor_exam.right_anemic:
				result_list.append('Anemic')
			if doctor_exam.right_icteric:
				result_list.append('Icteric')
			if doctor_exam.er_others:
				result_list.append(f'Other ({doctor_exam.eyes_right_others})')
			result += '\nRight: ' + ','.join(result_list)
	else:
		result = 'Left: No Abnormality \n Right: No Abnormality'
	return {
		'examination': result_line,
		'gradable': 0,
		'result': result,
		'status': status,
		'document': doctor_exam.name,
		'hidden_item_group': item_group,
		'hidden_item': item_code,
		'position': str(pos) + '-1',}

def process_ears(doctor_exam, item_group, item_code, status, pos):
	result_line = 'Ear'
	if not doctor_exam.ear_check:
		if (not doctor_exam.left_cerumen 
			and not doctor_exam.left_cerumen_prop 
			and not doctor_exam.left_tympanic 
			and not doctor_exam.earl_others):
			result = 'Left: No Abnormality'
		else:
			result_list = []
			if doctor_exam.left_cerumen:
				result_list.append('Cerumen')
			if doctor_exam.left_cerumen_prop:
				result_list.append('Cerumen Prop')
			if doctor_exam.left_tympanic:
				result_list.append('Tympanic membrance intact')
			if doctor_exam.earl_others:
				result_list.append(f'Other ({doctor_exam.ear_left_others})')
			result = 'Left: ' + ','.join(result_list)
		if (not doctor_exam.right_cerumen 
			and not doctor_exam.right_cerumen_prop 
			and not doctor_exam.right_tympanic 
			and not doctor_exam.earr_others):
			result += '\nRight: No Abnormality'
		else:
			result_list = []
			if doctor_exam.right_cerumen:
				result_list.append('Cerumen')
			if doctor_exam.right_cerumen_prop:
				result_list.append('Cerumen Prop')
			if doctor_exam.right_tympanic:
				result_list.append('Tympanic membrance intact')
			if doctor_exam.earl_others:
				result_list.append(f'Other ({doctor_exam.ear_right_others})')
			result += '\nRight: ' + ','.join(result_list)
	else:
		result = 'Left: No Abnormality \n Right: No Abnormality'
	return {
		'examination': result_line,
		'gradable': 0,
		'result': result,
		'status': status,
		'document': doctor_exam.name,
		'hidden_item_group': item_group,
		'hidden_item': item_code,
		'position': str(pos) + '-2',}

def process_nose(doctor_exam, item_group, item_code, status, pos):
	result_line = 'Nose'
	if not doctor_exam.nose_check:
		if (not doctor_exam.left_enlarged 
			and not doctor_exam.left_hyperemic 
			and not doctor_exam.left_polyp 
			and not doctor_exam.nl_others):
			result = 'Left: No Abnormality'
		else:
			result_list = []
			if doctor_exam.left_enlarged:
				result_list.append('Enlarged')
			if doctor_exam.left_hyperemic:
				result_list.append('Hyperemic')
			if doctor_exam.left_polyp:
				result_list.append('Polyp')
			if doctor_exam.nl_others:
				result_list.append(f'Other ({doctor_exam.nose_left_others})')
			result = 'Left: ' + ','.join(result_list)
		if (not doctor_exam.left_enlarged 
			and not doctor_exam.left_hyperemic 
			and not doctor_exam.left_polyp 
			and not doctor_exam.nl_others):
			result += '\nRight: No Abnormality'
		else:
			result_list = []
			if doctor_exam.right_enlarged:
				result_list.append('Enlarged')
			if doctor_exam.right_hyperemic:
				result_list.append('Hyperemic')
			if doctor_exam.right_polyp:
				result_list.append('Polyp')
			if doctor_exam.nr_others:
				result_list.append(f'Other ({doctor_exam.nose_right_others})')
			result += '\nRight: ' + ','.join(result_list)
		if doctor_exam.deviated:
			if result:
				result += '\nDeviated'
			else:
				result = 'Deviated'
	else:
		result = 'Left: No Abnormality \n Right: No Abnormality'
	return {
		'examination': result_line,
		'gradable': 0,
		'result': result,
		'status': status,
		'document': doctor_exam.name,
		'hidden_item_group': item_group,
		'hidden_item': item_code,
		'position': str(pos) + '-3',}

def process_throat(doctor_exam, item_group, item_code, status, pos):
	result_line = 'Throat'
	if not doctor_exam.throat_check:
		if (not doctor_exam.enlarged_tonsil 
			and not doctor_exam.hyperemic_pharynx 
			and not doctor_exam.t_others):
			result = 'No Abnormality'
		else:
			result_list = []
			if doctor_exam.enlarged_tonsil:
				result_list.append('Enlarged Tonsil')
			if doctor_exam.hyperemic_pharynx:
				result_list.append('Hyperemic Pharynx')
			if doctor_exam.t_others:
				result_list.append(f'Other ({doctor_exam.throat_others})')
			result = ','.join(result_list)
	else:
		result = 'No Abnormality'
	return{
		'examination': result_line,
		'gradable': 0,
		'result': result,
		'status': status,
		'document': doctor_exam.name,
		'hidden_item_group': item_group,
		'hidden_item': item_code,
		'position': str(pos) + '-4',}

def process_neck(doctor_exam, item_group, item_code, status, pos):
	result_line = 'Neck'
	if not doctor_exam.neck_check:
		if (not doctor_exam.enlarged_thyroid 
			and not doctor_exam.enlarged_lymph_node 
			and not doctor_exam.n_others):
			result = 'No Abnormality'
		else:
			result_list = []
			if doctor_exam.enlarged_thyroid:
				result_list.append(f'Enlarged Tonsil ({doctor_exam.enlarged_thyroid_details})')
			if doctor_exam.enlarged_lymph_node:
				result_list.append(f'Enlarged Lymph Node ({doctor_exam.enlarged_lymph_node_details})')
			if doctor_exam.n_others:
				result_list.append(f'Other ({doctor_exam.neck_others})')
			result = ','.join(result_list)
	else:
		result = 'No Abnormality'
	return {
		'examination': result_line,
		'gradable': 0,
		'result': result,
		'status': status,
		'document': doctor_exam.name,
		'hidden_item_group': item_group,
		'hidden_item': item_code,
		'position': str(pos) + '-5',}

def process_cardiac(doctor_exam, item_group, item_code, status, pos):
	result_line = 'Cardiac'
	if not doctor_exam.cardiac_check:
		if (not doctor_exam.regular_heart_sound 
			and not doctor_exam.murmur 
			and not doctor_exam.gallop 
			and not doctor_exam.c_others):
			result = 'No Abnormality'
		else:
			result_list = []
			if doctor_exam.regular_heart_sound:
				result_list.append('Regular Heart Sound')
			if doctor_exam.murmur:
				result_list.append('Murmur')
			if doctor_exam.gallop:
				result_list.append('Gallop')
			if doctor_exam.c_others:
				result_list.append(f'Other ({doctor_exam.cardiac_others})')
			result = ','.join(result_list)
	else:
		result = 'No Abnormality'
	return{
		'examination': result_line,
		'gradable': 0,
		'result': result,
		'status': status,
		'document': doctor_exam.name,
		'hidden_item_group': item_group,
		'hidden_item': item_code,
		'position': str(pos) + '-6',}

def process_breast(doctor_exam, item_group, item_code, status, pos):
	result_line = 'Breast'
	if not doctor_exam.breast_check:
		if (not doctor_exam.left_enlarged_breast 
			and not doctor_exam.left_lumps 
			and not doctor_exam.bl_others):
			result = 'Left: No Abnormality'
		else:
			result_list = []
			if doctor_exam.left_enlarged_breast:
				result_list.append('Enlarged Breast Glands')
			if doctor_exam.left_lumps:
				result_list.append('Lumps')
			if doctor_exam.bl_others:
				result_list.append(f'Other ({doctor_exam.breast_left_others})')
			result = 'Left: ' + ','.join(result_list)
		if (not doctor_exam.right_enlarged_breast 
			and not doctor_exam.right_lumps 
			and not doctor_exam.br_others):
			result += '\nRight: No Abnormality'
		else:
			result_list = []
			if doctor_exam.right_enlarged_breast:
				result_list.append('Enlarged Breast Glands')
			if doctor_exam.right_lumps:
				result_list.append('Lumps')
			if doctor_exam.br_others:
				result_list.append(f'Other ({doctor_exam.breast_right_others})')
			result += '\nRight: ' + ','.join(result_list)
	else:
		result = 'Left: No Abnormality \n Right: No Abnormality'
	return {
		'examination': result_line,
		'gradable': 0,
		'result': result,
		'status': status,
		'document': doctor_exam.name,
		'hidden_item_group': item_group,
		'hidden_item': item_code,
		'position': str(pos) + '-7',}

def process_resp(doctor_exam, item_group, item_code, status, pos):
	result_line = 'Respiratory System'
	if not doctor_exam.resp_check:
		if (not doctor_exam.left_ronkhi 
			and not doctor_exam.left_wheezing 
			and not doctor_exam.r_others):
			result = 'Left: No Abnormality'
		else:
			result_list = []
			if doctor_exam.left_ronkhi:
				result_list.append('Ronkhi')
			if doctor_exam.left_wheezing:
				result_list.append('Wheezing')
			if doctor_exam.r_others:
				result_list.append(f'Other ({doctor_exam.resp_left_others})')
			result = 'Left: ' + ','.join(result_list)
		if (not doctor_exam.right_ronkhi 
			and not doctor_exam.right_wheezing 
			and not doctor_exam.rr_others):
			result += '\nRight: No Abnormality'
		else:
			result_list = []
			if doctor_exam.right_ronkhi:
				result_list.append('Ronkhi')
			if doctor_exam.right_wheezing:
				result_list.append('Wheezing')
			if doctor_exam.br_others:
				result_list.append(f'Other ({doctor_exam.resp_right_others})')
			result += '\nRight: ' + ','.join(result_list)
	else:
		result = 'Left: No Abnormality \n Right: No Abnormality'
	return {
		'examination': result_line,
		'gradable': 0,
		'result': result,
		'status': status,
		'document': doctor_exam.name,
		'hidden_item_group': item_group,
		'hidden_item': item_code,
		'position': str(pos) + '-8',}
	
def process_abdomen(doctor_exam, item_group, item_code, status, pos):
	result_line = 'Abdomen'
	if not doctor_exam.abd_check:
		if (not doctor_exam.tenderness 
			and not doctor_exam.hepatomegaly 
			and not doctor_exam.splenomegaly 
			and not doctor_exam.increased_bowel_sounds 
			and not doctor_exam.a_others):
			result = 'No Abnormality'
		else:
			result_list = []
			if doctor_exam.tenderness:
				result_list.append(f'Tenderness ({doctor_exam.abd_tender_details})')
			if doctor_exam.hepatomegaly:
				result_list.append('Hepatomegaly')
			if doctor_exam.splenomegaly:
				result_list.append('Splenomegaly')
			if doctor_exam.increased_bowel_sounds:
				result_list.append('Increased Bowel Sounds')
			if doctor_exam.a_others:
				result_list.append(f'Other ({doctor_exam.abd_others})')
			result = ','.join(result_list)
	else:
		result = 'No Abnormality'
	return {
		'examination': result_line,
		'gradable': 0,
		'result': result,
		'status': status,
		'document': doctor_exam.name,
		'hidden_item_group': item_group,
		'hidden_item': item_code,
		'position': str(pos) + '-9',}

def process_spine(doctor_exam, item_group, item_code, status, pos):
	result_line = 'Spine'
	if not doctor_exam.spine_check:
		result = doctor_exam.spine_details
	else:
		result = 'No Abnormality'
	return {
		'examination': result_line,
		'gradable': 0,
		'result': result,
		'status': status,
		'document': doctor_exam.name,
		'hidden_item_group': item_group,
		'hidden_item': item_code,
		'position': str(pos) + '-10',}

def process_genit(doctor_exam, item_group, item_code, status, pos):
	result_line = 'Genitourinary'
	if not doctor_exam.genit_check:
		if (not doctor_exam.hernia 
			and not doctor_exam.hemorrhoid 
			and not doctor_exam.inguinal_nodes 
			and not doctor_exam.g_others):
			result = 'No Abnormality'
		else:
			result_list = []
			if doctor_exam.hernia:
				result_list.append(f'Hernia ({doctor_exam.hernia_details})')
			if doctor_exam.hemorrhoid:
				result_list.append('Hemorrhoid')
			if doctor_exam.inguinal_nodes:
				result_list.append('Inguinal Nodes')
			if doctor_exam.g_others:
				result_list.append(f'Other ({doctor_exam.genit_others})')
			result = ','.join(result_list)
	else:
		result = 'No Abnormality'
	return {
		'examination': result_line,
		'gradable': 0,
		'result': result,
		'status': status,
		'document': doctor_exam.name,
		'hidden_item_group': item_group,
		'hidden_item': item_code,
		'position': str(pos) + '-11',}

def process_neuro(doctor_exam, item_group, item_code, status, pos):
	result_line = 'Neurological System'
	if not doctor_exam.neuro_check:
		if (not doctor_exam.motoric_system_abnormality 
			and not doctor_exam.sensory_system_abnormality 
			and not doctor_exam.reflexes_abnormality 
			and not doctor_exam.ne_others):
			result = 'No Abnormality'
		else:
			result_list = []
			if doctor_exam.motoric_system_abnormality:
				result_list.append(f'Motoric System Abnormality ({doctor_exam.motoric_details})')
			if doctor_exam.sensory_system_abnormality:
				result_list.append(f'Sensory System Abnormality ({doctor_exam.sensory_details})')
			if doctor_exam.reflexes_abnormality:
				result_list.append(f'Reflexes Abnormality ({doctor_exam.reflex_details})')
			if doctor_exam.ne_others:
				result_list.append(f'Other ({doctor_exam.neuro_others})')
			result = ','.join(result_list)
	else:
		result = 'No Abnormality'
	return {
		'examination': result_line,
		'gradable': 0,
		'result': result,
		'status': status,
		'document': doctor_exam.name,
		'hidden_item_group': item_group,
		'hidden_item': item_code,
		'position': str(pos) + '-12',}

def process_skin(doctor_exam, item_group, item_code, status, pos):
	result_line = 'Skin'
	if not doctor_exam.skin_check:
		if (not doctor_exam.skin_psoriasis 
			and not doctor_exam.skin_tattoo 
			and not doctor_exam.skin_tag 
			and not doctor_exam.sk_others):
			result = 'No Abnormality'
		else:
			result_list = []
			if doctor_exam.skin_psoriasis:
				result_list.append('Psoriasis')
			if doctor_exam.skin_tattoo:
				result_list.append('Tattoo')
			if doctor_exam.skin_tag:
				result_list.append('Skin Tag')
			if doctor_exam.sk_others:
				result_list.append(f'Other ({doctor_exam.skin_others})')
			result = ','.join(result_list)
	else:
		result = 'No Abnormality'
	return {
		'examination': result_line,
		'gradable': 0,
		'result': result,
		'status': status,
		'document': doctor_exam.name,
		'hidden_item_group': item_group,
		'hidden_item': item_code,
		'position': str(pos) + '-13',}

@frappe.whitelist()
def get_queued_branch(branch):
	count = frappe.db.sql(f"""
		SELECT thsu.name, COALESCE(COUNT(tdr.healthcare_service_unit), 0) AS status_count, 
			tra.`user`, thsu.custom_default_doctype
		FROM `tabHealthcare Service Unit` thsu
		LEFT JOIN `tabDispatcher Room` tdr 
			ON thsu.name = tdr.healthcare_service_unit 
			AND tdr.status in ('Waiting to Enter the Room', 'Ongoing Examination')
		LEFT JOIN `tabRoom Assignment` tra 
			ON thsu.name = tra.healthcare_service_unit 
			AND tra.`date` = CURDATE()
		WHERE thsu.custom_branch = '{branch}' 
		AND thsu.is_group = 0 
		AND thsu.custom_default_doctype IS NOT NULL
		GROUP BY thsu.name""", as_dict=True)
	return count

@frappe.whitelist()
def checkin_room(dispatcher_id, hsu, doctype, docname):
	doc = frappe.get_doc('Dispatcher', dispatcher_id)
	doc.status = 'In Room'
	doc.room = hsu
	related_rooms = get_related_rooms (hsu, dispatcher_id)
	for room in doc.assignment_table:
		if room.healthcare_service_unit == hsu:
			room.status = 'Ongoing Examination'
			room.reference_doctype = doctype
			room.reference_doc = docname
		elif room.healthcare_service_unit in related_rooms:
			room.reference_doc = docname
	doc.save(ignore_permissions=True)
	return 'Checked In.'

@frappe.whitelist()
def removed_from_room(dispatcher_id, hsu, doctype, docname):
	doc = frappe.get_doc('Dispatcher', dispatcher_id)
	doc.status = 'In Queue'
	doc.room = ''
	for room in doc.assignment_table:
		if room.healthcare_service_unit == hsu:
			room.status = 'Wait for Room Assignment'
			room.reference_doc = ''
	doc.add_comment('Comment', f"""Removed from {hsu} examination room.""")
	doc.save(ignore_permissions=True)
	dispatcher_user = frappe.db.get_value(
		"Dispatcher Settings", 
		{"branch": doc.branch, 'enable_date': doc.date}, 
		['dispatcher'])
	notification_doc = frappe.new_doc('Notification Log')
	notification_doc.for_user = dispatcher_user
	notification_doc.from_user = frappe.session.user
	notification_doc.document_type = 'Dispatcher'
	notification_doc.document_name = doc.name
	notification_doc.subject = f"""Patient <strong>{doc.patient}</strong> removed from {hsu} room."""
	notification_doc.insert(ignore_permissions=True)
	exam_doc = frappe.get_doc(doctype, docname)
	exam_doc.db_set('docstatus', 2)
	exam_doc.db_set('status', 'Removed')
	return 'Removed from examination room.'

def get_related_rooms (hsu, dispatcher_id):
	return frappe.db.sql(f"""
		SELECT service_unit FROM `tabItem Group Service Unit` tigsu1
		WHERE tigsu1.parentfield = 'custom_room'
		AND 	tigsu1.parenttype = 'Item'
		AND 	tigsu1.service_unit != '{hsu}'
		AND 	EXISTS (
			SELECT 1 FROM `tabItem Group Service Unit` tigsu 
			WHERE tigsu.parentfield = 'custom_room'
			AND 	tigsu.parenttype = 'Item'
			AND 	tigsu.service_unit = '{hsu}'
			AND 	tigsu.parent = tigsu1.parent
			AND EXISTS (
				SELECT 1 FROM `tabMCU Appointment` tma
				WHERE tma.parent = '{dispatcher_id}'
				AND 	tma.parentfield = 'package'
				AND		tma.parenttype = 'Dispatcher'
				AND 	tma.examination_item = tigsu.parent))""", pluck = 'service_unit')

@frappe.whitelist()
def finish_exam(dispatcher_id, hsu, status, doctype, docname):
	if status == 'Removed':
		status = 'Wait for Room Assignment'
	doc = frappe.get_doc('Dispatcher', dispatcher_id)

	room_count = 0
	final_count = 0
	final_status = ['Finished', 'Refused', 'Rescheduled', 'Partial Finished']
	target = ''

	related_rooms = get_related_rooms (hsu, dispatcher_id)

	exists_to_retest = False
	source_doc = frappe.get_doc(doctype, docname)
	if doctype == 'Sample Collection':
		for sample in source_doc.custom_sample_table:
			if sample.status == 'To Retest':
				exists_to_retest = True
	else:
		for item in source_doc.examination_item:
			if item.status == 'To Retest':
				exists_to_retest = True

	for room in doc.assignment_table:
		room_count += 1
		if room.status in final_status:
			final_count += 1
		if room.healthcare_service_unit == hsu:
			room.status = 'Additional or Retest Request' if exists_to_retest else status
		if room.healthcare_service_unit in related_rooms:
			room.status = 'Additional or Retest Request' if exists_to_retest else status
	doc.status = 'Waiting to Finish' if room_count == final_count else 'In Queue'
	doc.room = ''
	doc.save(ignore_permissions=True)

	if (status == 'Finished' or status == 'Partial Finished') and not exists_to_retest:
		match doctype:
			case 'Radiology':
				target = 'Radiology Result'
			case 'Nurse Examination':
				target = 'Nurse Result'
			case 'Sample Collection':
				target = 'Lab Test'
		if target:
			result_doc_name = create_result_doc(source_doc, target)
			return {'message': 'Finished', 'docname': result_doc_name}
	return {'message': 'Finished'}

@frappe.whitelist()
def update_exam_item_status(dispatcher_id, examination_item, status):
	flag = frappe.db.sql(f"""
		SELECT 1 result 
		FROM `tabMCU Appointment` tma 
		WHERE `parent` = '{dispatcher_id}' 
		AND item_name = '{examination_item}' 
		UNION ALL 
		SELECT 2 result 
		FROM `tabMCU Appointment` tma 
		WHERE `parent` = '{dispatcher_id}' 
		AND EXISTS (SELECT 1 
			FROM `tabLab Test Template` tltt 
			WHERE tltt.sample = '{examination_item}' 
			AND tltt.name = tma.item_name)""", as_dict=True)
	if flag[0].result == 1:
		frappe.db.sql(f"""
			UPDATE `tabMCU Appointment` 
			SET `status` = '{status}' 
			WHERE parent = '{dispatcher_id}' 
			AND item_name = '{examination_item}' 
			AND parentfield = 'package' 
			AND parenttype = 'Dispatcher'
			""")
	elif flag[0].result == 2:
		items = frappe.db.sql(f"""
			SELECT name 
			FROM `tabMCU Appointment` tma 
			WHERE `parent` = '{dispatcher_id}' 
			AND EXISTS (SELECT 1 
				FROM `tabLab Test Template` tltt 
				WHERE tltt.sample = '{examination_item}' 
				AND tltt.name = tma.item_name)""", as_dict=True)
		for item in items:
			sql_update = f"""UPDATE `tabMCU Appointment` SET `status` = '{status}'""" \
			f"""WHERE name = '{item.name}'"""
			frappe.db.sql(sql_update)
	else:
		frappe.throw(f"Examination item {examination_item} does not exist.")
	return f"""Updated Dispatcher item: {examination_item} status to {status}."""

def create_result_doc(doc, target):
	not_created = True
	if target == 'Lab Test':
		not_created = False
		normal_toggle = 0
		new_doc = frappe.get_doc({
			'doctype': target,
			'company': doc.company,
			'custom_branch': doc.custom_branch,
			'patient': doc.patient,
			'patient_name': doc.patient_name,
			'patient_sex': doc.patient_sex,
			'patient_age': doc.patient_age,
			'custom_appointment': doc.custom_appointment,
			'custom_sample_collection': doc.name
		})
		for item in doc.custom_sample_table:
			if item.status == 'Finished':
				lab_test = frappe.db.sql(f"""
					SELECT name
					FROM `tabLab Test Template` tltt
					WHERE tltt.sample = '{item.sample}'
					AND EXISTS (
					SELECT 1 
					FROM `tabMCU Appointment` tma 
					WHERE tltt.name = tma.item_name
					AND tma.parent = '{doc.custom_dispatcher}'
					AND tma.parentfield = 'package'
					AND tma.parenttype = 'Dispatcher')""", pluck='name')
				for exam in lab_test:
					template_doc = frappe.get_doc('Lab Test Template', exam)
					non_selective = template_doc.get('normal_test_templates')
					selective = template_doc.get('custom_selective')
					if non_selective:
						match = re.compile(r'(\d+) Years?').match(doc.patient_age)
						age = int(match.group(1)) if match else None
						minmax = frappe.db.sql(f"""
							WITH cte AS (
								SELECT
									parent, lab_test_event, lab_test_uom, custom_age, custom_sex, 
									custom_min_value, custom_max_value,
									MAX(CASE WHEN custom_age <= {age} THEN custom_age END) 
										OVER (PARTITION BY parent, lab_test_event, custom_sex 
											ORDER BY custom_age DESC) AS max_age
								FROM `tabNormal Test Template`
							)
							SELECT
								lab_test_event,
								lab_test_uom,
								COALESCE(
									(
										SELECT custom_min_value 
										FROM cte 
										WHERE parent = '{exam}' 
										AND lab_test_event = c.lab_test_event 
										AND custom_sex = '{doc.patient_sex}' 
										AND max_age = {age} 
										ORDER BY custom_age desc LIMIT 1
									),
									(
										SELECT custom_min_value 
										FROM cte 
										WHERE parent = '{exam}' 
										AND lab_test_event = c.lab_test_event 
										AND custom_sex = '{doc.patient_sex}' 
										AND custom_age = (
											SELECT MAX(max_age) 
											FROM cte WHERE parent = '{exam}' 
											AND lab_test_event = c.lab_test_event 
											AND custom_sex = '{doc.patient_sex}' 
											AND max_age < {age}
										)
									)
								) AS custom_min_value,
								COALESCE(
									(
										SELECT custom_max_value 
										FROM cte 
										WHERE parent = '{exam}' 
										AND lab_test_event = c.lab_test_event 
										AND custom_sex = '{doc.patient_sex}' 
										AND max_age = {age} ORDER BY custom_age DESC LIMIT 1
									),
									(
										SELECT custom_max_value 
										FROM cte 
										WHERE parent = '{exam}' 
										AND lab_test_event = c.lab_test_event 
										AND custom_sex = '{doc.patient_sex}' 
										AND custom_age = (
											SELECT MAX(max_age) 
											FROM cte WHERE parent = '{exam}' 
											AND lab_test_event = c.lab_test_event 
											AND custom_sex = '{doc.patient_sex}' 
											AND max_age < {age}
										)
									)
								) AS custom_max_value
							FROM cte c
							WHERE parent = '{exam}'
							AND custom_sex = '{doc.patient_sex}'
							GROUP BY
								lab_test_event;""", as_dict=True)
						for mm in minmax:
							new_doc.append('normal_test_items', {
								'lab_test_name': exam, 
								'custom_min_value': mm.custom_min_value, 
								'custom_max_value': mm.custom_max_value, 
								'lab_test_event': mm.lab_test_event, 
								'lab_test_uom': mm.lab_test_uom,
								'custom_sample': item.sample
							})
							normal_toggle = 1
					if selective:
						for sel in template_doc.custom_selective:
							new_doc.append('custom_selective_test_result', {
								'event': exam,
								'result_set': sel.result_select, 
								'result': sel.result_select.splitlines()[0],
								'sample': item.sample
							})
		new_doc.normal_toggle = normal_toggle
	else:
		new_doc = frappe.get_doc({
			'doctype': target,
			'company': doc.company,
			'branch': doc.branch,
			'queue_pooling': doc.queue_pooling,
			'patient': doc.patient,
			'patient_name': doc.patient_name,
			'patient_sex': doc.patient_sex,
			'patient_age': doc.patient_age,
			'patient_encounter': doc.patient_encounter,
			'appointment': doc.appointment,
			'dispatcher': doc.dispatcher,
			'service_unit': doc.service_unit,
			'created_date': today(),
			'remark': doc.remark,
			'exam': doc.name
		})
		if target == 'Nurse Result':
			count_nurse_result = frappe.db.sql(f"""SELECT count(*) count 
				FROM `tabNurse Examination Template` tnet
				WHERE EXISTS (SELECT * FROM `tabNurse Examination Request` tner 
				WHERE tner.parent = '{doc.name}' AND tnet.name = tner.template)
				AND tnet.result_in_exam = 0""", as_dict = True)
			if count_nurse_result[0].count == 0:
				return
		for item in doc.examination_item:
			if item.status == 'Finished':
				item_status = 'Started'
				if target == 'Nurse Result' and frappe.db.get_value(
					'Nurse Examination Template', item.template, 'result_in_exam'):
					item_status = 'Finished'
				new_doc.append('examination_item', {
					'status': item_status,
					'template': item.template,
					'status_time': item.status_time if item.status == 'Finished' else None
				})
				match target:
					case 'Radiology Result':
						not_created = False
						template = 'Radiology Result Template'
						template_doc = frappe.get_doc(template, item.template)
						for result in template_doc.items:
							if result.sex:
								if result.sex == doc.patient_sex:
									new_doc.append('result', {
										'result_line': result.result_text,
										'normal_value': result.normal_value,
										'mandatory_value': result.mandatory_value,
										'result_check': result.normal_value,
										'item_code': template_doc.item_code,
										'result_options': result.result_select
									})
							else:
								new_doc.append('result', {
									'result_line': result.result_text,
									'normal_value': result.normal_value,
									'mandatory_value': result.mandatory_value,
									'result_check': result.normal_value,
									'item_code': template_doc.item_code,
									'result_options': result.result_select
								})
					case 'Nurse Result':
						not_created = False
						template = 'Nurse Examination Template'
						template_doc = frappe.get_doc(template, item.template)
						if getattr(template_doc, 'result_in_exam', None):
							for result in doc.result:
								if template_doc.item_code == result.item_code:
									new_doc.append('result', {
										'item_code': result.item_code,
										'item_name': result.item_name,
										'result_line': result.result_line,
										'result_check': result.result_check,
										'result_text': result.result_text,
										'normal_value': result.normal_value,
										'result_options': result.result_options,
										'mandatory_value': result.mandatory_value,
										'is_finished': True
									})
							for normal_item in doc.non_selective_result:
								if template_doc.item_code == normal_item.item_code:
									new_doc.append('non_selective_result', {
										'item_code': normal_item.item_code,
										'test_name': normal_item.test_name,
										'test_event': normal_item.test_event,
										'result_value': normal_item.result_value,
										'test_uom': normal_item.test_uom,
										'min_value': normal_item.min_value,
										'max_value': normal_item.max_value,
										'is_finished': True
									})
						else:
							for result in template_doc.items:
								new_doc.append('result', {
									'result_line': result.result_text,
									'normal_value': result.normal_value,
									'mandatory_value': result.mandatory_value,
									'result_check': result.normal_value,
									'item_code': template_doc.item_code,
									'result_options': result.result_select,
									'is_finished': False
								})
							for normal_item in template_doc.normal_items:
								new_doc.append('non_selective_result', {
									'item_code': template_doc.item_code,
									'test_name': normal_item.heading_text,
									'test_event': normal_item.lab_test_event,
									'test_uom': normal_item.lab_test_uom,
									'min_value': normal_item.min_value,
									'max_value': normal_item.max_value,
									'is_finished': False
								})
					case _:
						frappe.throw(f"Unhandled Template for {target} DocType.")
	if not not_created:
		new_doc.insert(ignore_permissions=True)
	return new_doc.name

@frappe.whitelist()
def new_doctor_result(appointment):
	appt = frappe.get_doc('Patient Appointment', appointment)
	dispatcher = frappe.get_all(
		'Dispatcher', filters={'patient_appointment': appointment}, pluck='name')
	if dispatcher:
		disp = dispatcher[0]
	doc = frappe.new_doc('Doctor Result')
	doc.appointment = appt.name
	doc.patient = appt.patient
	doc.age = appt.patient_age
	doc.gender = appt.patient_sex
	doc.dispatcher = disp
	doc.created_date = today()
	package_line = frappe.db.sql(f"""SELECT examination_item, item_name, item_group,
		(select custom_gradable from `tabItem Group` tig 
			where tig.name = item_group) group_gradable, 
		(select custom_bundle_position from `tabItem Group` tig 
			where tig.name = item_group) group_position,
		(select custom_gradable from `tabItem` ti 
			where ti.name = examination_item) item_gradable, 
		(select custom_bundle_position from `tabItem` ti 
			where ti.name = examination_item) item_position,
		(select 1 from `tabNurse Examination Template` tnet 
			where tnet.item_code = examination_item) nurse,
		(select 1 from `tabDoctor Examination Template` tnet 
			where tnet.item_code = examination_item) doctor,
		(select 1 from `tabRadiology Result Template` tnet 
			where tnet.item_code = examination_item) radiology,
		(select 1 from `tabLab Test Template` tnet 
			where tnet.lab_test_code = examination_item) lab_test
		from `tabMCU Appointment`
		where parent = '{appt.name}'""", as_dict = True)
	group_result = get_examination_items(package_line)
	combined_items = appt.custom_mcu_exam_items + appt.custom_additional_mcu_items
	process_examination_items(doc, group_result, combined_items)
	doc.insert(ignore_permissions=True)
