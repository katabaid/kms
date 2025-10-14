# Copyright (c) 2025, GIS and contributors
# For license information, please see license.txt

import frappe
from itertools import groupby

def execute(filters=None):
	columns = [
		{'label': 'Name', 'fieldname': 'patient_name', 'fieldtype': 'Data'},
		{'label': 'Sex', 'fieldname': 'patient_sex', 'fieldtype': 'Data'},
		{'label': 'Age', 'fieldname': 'patient_age', 'fieldtype': 'Int'},
		{'label': 'Exam Date', 'fieldname': 'exam_date', 'fieldtype': 'Date'},
		{'label': 'Job Position', 'fieldname': 'position', 'fieldtype': 'Data'},
		{'label': 'Chief Complain', 'fieldname': 'complain', 'fieldtype': 'Data'},
		{'label': 'Life Style', 'fieldname': 'life_style', 'fieldtype': 'Data'},
		{'label': 'Past Medical History', 'fieldname': 'past_history', 'fieldtype': 'Data'},
		{'label': 'Family Medical History', 'fieldname': 'family_history', 'fieldtype': 'Data'},
		{'label': 'COF', 'fieldname': 'cof', 'fieldtype': 'Data'},		
	]
	required_filters = ['customer', 'from_date', 'to_date']
	if not all(filters.get(key) for key in required_filters):
		return columns, []
	pa_dr = _get_valid_loop_list(filters)
	if not pa_dr:
		return columns, []
	columns.extend(get_result_columns(pa_dr))
	data = get_data(pa_dr)
	return columns, data

def get_result_columns(filters):
	final_columns = []
	pa = [list(d.values())[0] for d in filters]
	pb = frappe.get_all('Patient Appointment', filters={'name': ['in', pa]}, pluck='mcu', distinct=True)
	item_list = frappe.get_all('Product Bundle Item', pluck = 'item_code', distinct = True,
    filters= { 'parent': ['in', pb]})
	if not item_list:
		return final_columns
	items = frappe.get_all('Item', fields=['name', 'item_name', 'item_group'], distinct=True, 
		order_by='custom_bundle_position ASC', filters={'name': ['in', item_list]})
	key_function = lambda item: item['item_group']
	items.sort(key=key_function)
	for group_name, group_iterator in groupby(items, key=key_function):
		items_in_group = list(group_iterator)
		for item in items_in_group:
			template = _get_template_for_item(item['name'])
			if not template:
				return final_columns
			is_single = template.get('custom_is_single_result') or template.get('is_single_result')
			final_columns.append(
				{'label': item['item_name'], 'fieldname': f"{group_name}__{item['name']}", 'fieldtype': 'Data'})
			if not template.get('result_in_exam') or is_single:
				continue
			if template.get('doctype') in ['Lab Test Template', 'Nurse Examination Template']:
				if template.get('doctype') == 'Lab Test Template':
					normal_field = 'normal_test_templates'
					event_key = 'lab_test_event'
					selective_field = 'custom_selective'
					selective_key = 'event'
					calculated_field = 'custom_calculated_exam'
					calculated_key = 'test_label'
				else:
					normal_field = 'normal_items'
					event_key = 'heading_text'
					selective_field = 'items'
					selective_key = 'result_text'
					calculated_field = 'calculated_exam'
					calculated_key = 'test_label'
				normal_list = template.get(normal_field) or []
				distinct_events = {
					c.get(event_key) for c in normal_list
					if c.get(event_key)
				}
				for event in distinct_events:
					final_columns.append(
						{ 'label': event, 
							'fieldname': f"{group_name}__{item['name']}__{frappe.scrub(event)}", 
							'fieldtype': 'Data'})
				for selective in template.get(selective_field) or []:
					final_columns.append(
						{ 'label': selective[selective_key], 
							'fieldname': f"{group_name}__{item['name']}__{frappe.scrub(selective[selective_key])}", 
							'fieldtype': 'Data'})
				for calculated in template.get(calculated_field) or []:
					final_columns.append(
						{ 'label': calculated.get(calculated_key), 
							'fieldname': f"{group_name}__{item['name']}__{frappe.scrub(calculated.get(calculated_key))}", 
							'fieldtype': 'Data'})
			else:
				pass
		final_columns.append({'label': group_name, 'fieldname': group_name, 'fieldtype': 'Data'})
	frappe.log_error('Kolom', final_columns)
	return final_columns

def get_data(filters):
	data = []
	for pa_dr in filters or []:
		doc = frappe.get_doc('Patient Appointment', pa_dr.get('pa'))
		job_position = frappe.get_value('Patient', doc.patient, 'occupation') or ''
		cof = frappe.get_value( 'Doctor Result', {'name': pa_dr.get('dr'), 'docstatus': 1}, 'fitness_level')
		q = frappe.get_all('Questionnaire', 
			fields=['name'], 
			filters={'patient_appointment': pa_dr.get('pa'), 'template': 'MCU', 'status': 'Completed'}, 
			limit=1)
		questionnaire = frappe.get_doc('Questionnaire', q[0].name) if q else None
		frappe.log_error('Questionnaire', pa_dr.get('pa'))
		if q:
			frappe.log_error(q[0].name, questionnaire)
		complain = ''
		life_style = ''
		past_history = ''
		family_history = ''
		if questionnaire:
			if len(questionnaire.detail) > 50:
				complain = questionnaire.detail[1].answer if questionnaire.detail[1].answer else questionnaire.detail[0].answer
				ls = []
				ls.append(f'{questionnaire.detail[45].question}: {questionnaire.detail[45].answer}' if questionnaire.detail[45].answer else '')
				ls.append(f'{questionnaire.detail[47].question}: {questionnaire.detail[47].answer}' if questionnaire.detail[47].answer else '')
				ls.append(f'{questionnaire.detail[49].question}: {questionnaire.detail[49].answer}' if questionnaire.detail[49].answer else '')
				life_style = '\n'.join([x for x in ls if x])
				ph = []
				ph.append(
					f'{questionnaire.detail[2].question} {questionnaire.detail[3].question}: {questionnaire.detail[3].answer}'
					if questionnaire.detail[3].answer else '')
				ph.append(
					f'{questionnaire.detail[4].question} {questionnaire.detail[5].question}: {questionnaire.detail[5].answer}'
					if questionnaire.detail[5].answer else '')
				ph.append(
					f'{questionnaire.detail[6].question} {questionnaire.detail[7].question}: {questionnaire.detail[7].answer}'
					if questionnaire.detail[7].answer else '')
				ph.append(
					f'{questionnaire.detail[8].question} {questionnaire.detail[9].question}: {questionnaire.detail[9].answer}'
					if questionnaire.detail[9].answer else '')
				ph.append(
					f'{questionnaire.detail[10].question} {questionnaire.detail[11].question}: {questionnaire.detail[11].answer}'
					if questionnaire.detail[11].answer else '')
				ph.append(
					f'{questionnaire.detail[12].question} {questionnaire.detail[13].question}: {questionnaire.detail[13].answer}'
					if questionnaire.detail[13].answer else '')
				ph.append(
					f'{questionnaire.detail[14].question} {questionnaire.detail[15].question}: {questionnaire.detail[15].answer}'
					if questionnaire.detail[15].answer else '')
				ph.append(
					f'{questionnaire.detail[16].question} {questionnaire.detail[17].question}: {questionnaire.detail[17].answer}'
					if questionnaire.detail[17].answer else '')
				ph.append(
					f'{questionnaire.detail[18].question} {questionnaire.detail[19].question}: {questionnaire.detail[19].answer}'
					if questionnaire.detail[19].answer else '')
				ph.append(
					f'{questionnaire.detail[20].question}: {questionnaire.detail[20].answer}' 
					if questionnaire.detail[20].answer else '')
				past_history = '\n'.join([x for x in ph if x])
				fh =[]
				fh.append(
					f'{questionnaire.detail[21].question} {questionnaire.detail[22].question}: {questionnaire.detail[22].answer}'
					if questionnaire.detail[22].answer else '')
				fh.append(
					f'{questionnaire.detail[23].question} {questionnaire.detail[24].question}: {questionnaire.detail[24].answer}'
					if questionnaire.detail[24].answer else '')
				fh.append(
					f'{questionnaire.detail[25].question} {questionnaire.detail[26].question}: {questionnaire.detail[26].answer}'
					if questionnaire.detail[26].answer else '')
				fh.append(
					f'{questionnaire.detail[27].question} {questionnaire.detail[28].question}: {questionnaire.detail[28].answer}'
					if questionnaire.detail[28].answer else '')
				fh.append(
					f'{questionnaire.detail[29].question} {questionnaire.detail[30].question}: {questionnaire.detail[30].answer}'
					if questionnaire.detail[30].answer else '')
				fh.append(
					f'{questionnaire.detail[31].question} {questionnaire.detail[32].question}: {questionnaire.detail[32].answer}'
					if questionnaire.detail[32].answer else '')
				fh.append(
					f'{questionnaire.detail[33].question} {questionnaire.detail[34].question}: {questionnaire.detail[34].answer}'
					if questionnaire.detail[34].answer else '')
				fh.append(
					f'{questionnaire.detail[35].question} {questionnaire.detail[36].question}: {questionnaire.detail[36].answer}'
					if questionnaire.detail[36].answer else '')
				fh.append(
					f'{questionnaire.detail[37].question}: {questionnaire.detail[37].answer}' 
					if questionnaire.detail[37].answer else '')
				family_history = '\n'.join([x for x in fh if x])
				frappe.log_error('past_history', past_history)
				frappe.log_error('life_style', life_style)
		row = {
			'patient_name': doc.patient_name,
			'patient_sex': doc.patient_sex,
			'patient_age': doc.patient_age,
			'exam_date': doc.appointment_date,
			'position': job_position,
			'complain': complain,
			'life_style': life_style,
			'past_history': past_history,
			'family_history': family_history,
			'cof': cof,
		}
		grades = frappe.get_all('MCU Exam Grade', 
			fields=['examination', 'result', 'hidden_item_group', 'hidden_item', 'is_item', 'description', 'grade'],
			filters={'parent': pa_dr.get('dr')},
			order_by='parentfield, idx')
		for grade in grades:
			group_grade = grade.grade.split('-')[-1] if grade.grade else ''
			if not grade.hidden_item:
				row[grade.hidden_item_group] = group_grade
			elif grade.is_item:
				key = f"{grade.hidden_item_group}__{grade.hidden_item}"
				row[key] = grade.result or grade.description
			else:
				key = f"{grade.hidden_item_group}__{grade.hidden_item}__{frappe.scrub(grade.examination)}"
				row[key] = grade.result
		data.append(row)
	return data

def _get_template_for_item(item_name):
	lt = frappe.db.exists('Lab Test Template', {'lab_test_code': item_name})
	if lt:
		return frappe.get_doc('Lab Test Template', lt)
	ne = frappe.db.exists('Nurse Examination Template', {'item_code': item_name})
	if ne:
		return frappe.get_doc('Nurse Examination Template', ne)
	de = frappe.db.exists('Doctor Examination Template', {'item_code': item_name})
	if de:
		return frappe.get_doc('Doctor Examination Template', de)
	rr = frappe.db.exists('Radiology Result Template', {'item_code': item_name})
	if rr:
		return frappe.get_doc('Radiology Result Template', rr)
	return None

def _get_valid_loop_list(filters):
	pa_dr = []
	pa = frappe.get_all('Patient Appointment', pluck = 'name', order_by = 'name ASC',
		filters={
			'custom_patient_company': filters.customer,
			'appointment_date': ['between', [filters.from_date, filters.to_date]],
			'status': 'Checked Out',
			'appointment_type': 'MCU'
		})
	if not pa:
		return pa_dr
	for appointment in pa:
		dr = frappe.db.get_value('Doctor Result', 
			{'appointment': appointment, 'docstatus': 1}, 'name')
		if dr:
			pa_dr.append({'pa': appointment, 'dr': dr})
	return pa_dr