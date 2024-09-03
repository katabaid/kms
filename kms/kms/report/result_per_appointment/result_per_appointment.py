# Copyright (c) 2024, GIS and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	return columns, data

def make_column (label, name, type='Data', width=150, align='left'):
	return {
		'label': label,								'fieldname': name,						'fieldtype': type,
		'width': width,								'align': align
	}

def make_row (
	indent, exam_type='', status='', result_line='', result_check='', result_value='', uom='', 
	min_value='', max_value=''):
	return {
		'exam_type': exam_type,				'status': status,							'result_line': result_line,
		'result_check': result_check,	'result_value': result_value,	'uom': uom,
		'min_value': min_value,				'max_value': max_value,				'indent': indent
	}

def get_columns():
	return [
		make_column(_('Exam Type'), 'exam_type', 'Data', 250),
		make_column(_('Status'), 'status', 'Data', 100),
		make_column(_('Result Line'), 'result_line', 'Data', 250),
		make_column(_('Result Check'), 'result_check', 'Data', 250),
		make_column(_('Result Value'), 'result_value', 'Data', 100),
		make_column(_('UOM'), 'uom', 'Data', 100),
		make_column(_('Min Value'), 'min_value', 'Float', 100, 'right'),
		make_column(_('Max Value'), 'max_value', 'Float', 100, 'right'),
	]

def get_data(filters):
	exams = frappe.db.sql(f"""
		SELECT tma.examination_item, tma.item_name, tma.status, tma.parent, tdr.healthcare_service_unit, tdr.reference_doctype, tdr.reference_doc 
		FROM `tabMCU Appointment` tma, tabItem ti, `tabDispatcher Room` tdr, `tabItem Group Service Unit` tigsu 
		WHERE EXISTS (SELECT 1 FROM `tabDispatcher` td WHERE patient_appointment = '{filters.exam_id}' AND tma.parent = td.name)
		AND (EXISTS (SELECT 1 FROM `tabNurse Examination Template` tnet WHERE tnet.result_in_exam = 1 AND tnet.item_code = tma.examination_item)
		OR EXISTS (SELECT 1 FROM `tabDoctor Examination Template` tdet WHERE tdet.item_code = tma.examination_item))
		AND tma.examination_item = ti.name
		AND tma.parent = tdr.parent
		AND ti.name = tigsu.parent 
		AND tigsu.service_unit = tdr.healthcare_service_unit 
		AND NOT (tma.status = 'Finished' AND tdr.reference_doc IS NULL)
		ORDER BY ti.custom_bundle_position""", as_dict = 1)
	group_data = []
	previous_exam_item = ''
	for exam in exams:
		group_data.append(make_row(0, exam.item_name, exam.status))
		if previous_exam_item != exam.item_code:
			for child in get_children(exam.reference_doc, exam.examination_item, exam.reference_doctype):
				group_data.append(make_row(
					1, '', '', child.result_line, child.result_check, child.result_text, child.uom, child.min_value, child.max_value
				))
		previous_exam_item = exam.examination_item
	return group_data

def get_children(name, item, doctype):
	def find_field_for_item(item):
		result = frappe.call('kms.healthcare.get_mcu_settings', is_item=True)
		return next((entry["field"] for entry in result if entry["value"] == item), None)
	
	if doctype == 'Doctor Examination':
		matching_field = find_field_for_item(item)
		if matching_field:
			if matching_field == 'physical_examination':
				return frappe.db.sql(f"""SELECT 
					'Physical Examination' AS result_line, tde.phallen_details AS result_text, NULL AS uom, NULL AS min_value, NULL AS max_value,
					IF(tde.phallen_check>0, 'No Abnormality', '') AS result_check
					FROM `tabDoctor Examination` tde WHERE name = '{name}'""", as_dict=1)
			elif matching_field == 'visual_field_test':
				return frappe.db.sql(f"""SELECT 
					'Visual Field Test' AS result_line, tde.visual_details AS result_text, NULL AS uom, NULL AS min_value, NULL AS max_value,
					IF(tde.visual_check>0, 'Same As Examiner', '') AS result_check
					FROM `tabDoctor Examination` tde WHERE name = '{name}'""", as_dict=1)
			elif matching_field == 'romberg_test':
				return frappe.db.sql(f"""SELECT 
					'Romberg Test' AS result_line, tde.phallen_details AS result_text, NULL AS uom, NULL AS min_value, NULL AS max_value,
					IF(tde.romberg_check>0, 'No Abnormality', tde.romberg_abnormal) AS result_check
					FROM `tabDoctor Examination` tde WHERE name = '{name}'""", as_dict=1)
			elif matching_field == 'tinnel_test':
				return frappe.db.sql(f"""SELECT 
					'Tinnel Test' AS result_line, tde.tinnel_details AS result_text, NULL AS uom, NULL AS min_value, NULL AS max_value,
					IF(tde.tinnel_check>0, 'No Abnormality', '') AS result_check
					FROM `tabDoctor Examination` tde WHERE name = '{name}'""", as_dict=1)
			elif matching_field == 'phallen_test':
				return frappe.db.sql(f"""SELECT 
					'Phallen Test' AS result_line, tde.phallen_details AS result_text, NULL AS uom, NULL AS min_value, NULL AS max_value,
					IF(tde.phallen_check>0, 'No Abnormality', '') AS result_check
					FROM `tabDoctor Examination` tde WHERE name = '{name}'""", as_dict=1)
			elif matching_field == 'rectal_test':
				return frappe.db.sql(f"""SELECT 
					'Rectal Examination' AS result_line, tde.rectal_others AS result_text, NULL AS uom, NULL AS min_value, NULL AS max_value,
					IF(tde.rectal_check>0, 'No Abnormality', CONCAT_WS(', ', IF(tde.enlarged_prostate>0, 'Enlarged Prostate', ''), CONCAT('Hemorrhoid: ', tde.rectal_hemorrhoid))) AS result_check
					FROM `tabDoctor Examination` tde WHERE name = '{name}'""", as_dict=1)
	return frappe.db.sql(f"""
		SELECT tnesr.result_line, tnesr.result_check, tnesr.result_text, NULL AS uom, NULL AS min_value, NULL AS max_value 
		FROM `tab{doctype} Selective Result` tnesr 
		WHERE tnesr.parent = '{name}' AND tnesr.item_code = '{item}'
		UNION
		SELECT CONCAT(tner.test_name, NVL2(tner.test_event, CONCAT(': ', tner.test_event), '')), NULL, tner.result_value, tner.test_uom, tner.min_value, tner.max_value 
		FROM `tab{doctype} Result` tner 
		WHERE tner.parent = '{name}' AND tner.item_code = '{item}'
		UNION
		SELECT tce.test_label, NULL, tce.RESULT, NULL, NULL, NULL 
		FROM `tabCalculated Exam` tce 
		WHERE tce.parent = '{name}' AND tce.item_code = '{item}'""", as_dict=1)