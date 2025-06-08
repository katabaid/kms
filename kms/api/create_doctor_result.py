import frappe
from frappe.utils import today
from kms.utils import assess_mcu_grade

@frappe.whitelist()
def create_doctor_result(appointment):
	appt = frappe.get_doc('Patient Appointment', appointment)
	disp = frappe.db.get_value('Dispatcher', {'patient_appointment': appointment}, 'name')
	doc = frappe.new_doc('Doctor Result')
	doc.appointment = appt.name
	doc.patient = appt.patient
	doc.age = appt.patient_age
	doc.gender = appt.patient_sex
	doc.dispatcher = disp
	doc.created_date = today()
	exam_dict = _get_exam_dict(appointment)
	results = _create_examination_items(appointment, exam_dict)
	for result in results:
		if len(result) != 2:
			frappe.log_error(f"Invalid row format: {result}")
			continue
		grade_type, data_dict = result
		doc.append(grade_type, data_dict)
	doc.insert(ignore_permissions=True)

def _get_exam_dict(appointment):
	return frappe.db.sql('''
		SELECT examination_item, item_name, item_group,
			(SELECT custom_gradable FROM `tabItem Group` tig WHERE tig.name = item_group) AS group_gradable,
			(SELECT custom_bundle_position FROM `tabItem Group` tig WHERE tig.name = item_group) AS group_position,
			(SELECT custom_gradable FROM `tabItem` ti WHERE ti.name = examination_item) AS item_gradable,
			(SELECT custom_bundle_position FROM `tabItem` ti WHERE ti.name = examination_item) AS item_position,
			CASE
        WHEN EXISTS (
					SELECT 1 FROM `tabNurse Examination Template` tnet WHERE tnet.item_code = examination_item
        ) THEN 'nurse'
        WHEN EXISTS (
					SELECT 1 FROM `tabDoctor Examination Template` tdet WHERE tdet.item_code = examination_item
        ) THEN 'doctor'
        WHEN EXISTS (
					SELECT 1 FROM `tabRadiology Result Template` tret WHERE tret.item_code = examination_item
        ) THEN 'radiology'
        WHEN EXISTS (
					SELECT 1 FROM `tabLab Test Template` tlt WHERE tlt.lab_test_code = examination_item
        ) THEN 'lab_test'
        ELSE NULL
			END AS exam_type
		FROM `tabMCU Appointment`
		WHERE parent = %s AND status = 'Finished'
		ORDER BY 8, 5, 7''', (appointment), as_dict = True)

def _create_examination_items(appointment, exam_dict):
	result = []
	template = frappe.db.get_single_value('MCU Settings', 'vital_sign_with_systolicdiastolic')
	blood_pressure_item_code = frappe.db.get_value(
		'Nurse Examination Template', template, 'item_code') if template else None
	grouped_exams = {}
	for exam in exam_dict:
		category = exam.get('exam_type')
		group = exam.get('item_group')
		if category not in grouped_exams:
			grouped_exams[category] = {}
		if group not in grouped_exams[category]:
			grouped_exams[category][group] = {
				'item_group': group,
				'group_gradable': exam.get('group_gradable'),
				'group_position': exam.get('group_position'),
				'items': []
			}
		grouped_exams[category][group]['items'].append({
			'examination_item': exam.get('examination_item'),
			'item_name': exam.get('item_name'),
			'item_gradable': exam.get('item_gradable'),
			'item_position': exam.get('item_position')
		})
	for category, groups in grouped_exams.items():
		for group in groups.values():
			result.append([f'{category}_grade', {
				'examination': group['item_group'],
				'gradable': group['group_gradable'],
				'hidden_item_group': group['item_group'],
			}])
			if category == 'doctor':
				result.extend(__create_doctor_category(appointment, group['item_group']))
			for item in group['items']:
				if category == 'nurse':
					result.extend(
						__create_nurse_category(appointment, item, group['item_group'], blood_pressure_item_code))
				elif category == 'radiology':
					result.extend(__create_radiology_category(appointment, item, group['item_group']))
				elif category == 'lab_test':
					result.extend(__create_lab_test_category(appointment, item, group['item_group']))
	return result

def __create_doctor_category(appt, item_group):
	result = []
	custom_result_items = [
		'physical_examination', 'visual_field_test', 'romberg_test', 'tinnel_test',
		'phallen_test', 'rectal_test', 'dental_examination']
	custom_results = [
		{'item_code': frappe.db.get_single_value('MCU Settings', a), 'tab': a} 
		for a in custom_result_items]
	items = frappe.db.sql("""
		SELECT item, parent, template FROM `tabDoctor Examination Request` tder
		WHERE parent IN (
			SELECT name FROM `tabDoctor Examination` tde WHERE tde.appointment = %s AND docstatus = 1)
		AND EXISTS (SELECT 1 FROM tabItem WHERE item_group = %s AND name = item)	
		ORDER BY (SELECT custom_bundle_position FROM tabItem ti WHERE tder.item = ti.name)
	""", (appt, item_group), as_dict=True)
	for item in items:
		item_name, gradable = frappe.db.get_value('Item', item.item, ['item_name', 'custom_gradable'])
		result.append(['doctor_grade', {
			'examination': item_name,
			'gradable': gradable,
			'hidden_item_group': item_group,
			'hidden_item': item.item,
			'is_item': 1, 
			'document_type': 'Doctor Examination', 
			'document_name': item.parent
		}])
		is_single_result = frappe.db.get_value(
			'Doctor Examination Template', item['template'], 'is_single_result')
		if is_single_result:
			if item.item in [item['item_code'] for item in custom_results]:
				de_doc = frappe.get_doc('Doctor Examination', item.parent)
				single_result = ___find_single_item_result(
					de_doc.result, de_doc.non_selective_result, item['item'])
				if single_result:
					result[0][1].update(single_result)
					if gradable:
						grade, description = assess_mcu_grade(
							result[0][1].get('result', ''), item_group, item['item'],
							min_value=result[0][1].get('min_value', 0), max_value=result[0][1].get('max_value', 0),
							normal_value=result[0][1].get('normal_value', 0))
						if grade:
							result[0][1].update({'grade': grade, 'description': description})
					if result[0][1].get('normal_value'):
						result[0][1].pop('normal_value')
			else:
				tab = next((cr['tab'] for cr in custom_results if cr['item_code'] == item.item), None)
				single_result = ___build_doctor_tab_result(item.parent, item.item, item_group, tab)
				if single_result:
					result[0][1].update(single_result)
					if tab != 'dental_examination':
						if gradable:
							grade, description = assess_mcu_grade(
								result[0][1].get('result', ''), item_group, item['item'],
								min_value=result[0][1].get('min_value', 0), max_value=result[0][1].get('max_value', 0),
								normal_value=result[0][1].get('normal_value', 0))
							if grade:
								result[0][1].update({'grade': grade, 'description': description})
						if result[0][1].get('normal_value'):
							result[0][1].pop('normal_value')
		else:
			if item.item in [item['item_code'] for item in custom_results]:
				tab = next((cr['tab'] for cr in custom_results if cr['item_code'] == item.item), None)
				result.extend(___build_doctor_tab_result(item.parent, item.item, item_group, tab))
			else:
				result.extend(___fetch_doctor_result_per_item(item.parent, item.item, item_group))
	return result

def __create_lab_test_category(appointment, item, item_group):
	result = []
	doc_no = frappe.db.sql("""
	SELECT name FROM `tabLab Test` tlt
	WHERE custom_appointment = %s
	AND docstatus IN (0, 1)
	AND EXISTS (
		SELECT 1 FROM `tabLab Test Request` tltr 
		WHERE parent = tlt.custom_sample_collection 
		AND tltr.item_code = %s)""", (appointment, item['examination_item']), as_dict=True)[0]
	result.append(['lab_test_grade', {
		'examination': item['item_name'],
		'gradable': item.get('item_gradable', 0),
		'hidden_item_group': item_group,
		'hidden_item': item['examination_item'],
		'is_item': 1, 
		'document_type': 'Lab Test', 
		'document_name': doc_no.name
	}])
	result_rows = ___fetch_lab_result_per_item(appointment, item['examination_item'], item_group)
	if result_rows:
		if len(result_rows) == 1:
			row = result_rows[0]
			result_value = (f"{row['result_text']}: {row['result_desc']}" 
				if row.get('result_desc') else convert_if_whole(row.get('result_text')))
			grade_desc = (frappe.db.get_value('MCU Grade', row.get('grade'), 'description') 
				if row.get('grade') else None)
			std_value = (
				f"{convert_if_whole(row.get('min_value'))} - {convert_if_whole(row.get('max_value'))}" 
				if row.get('min_value') or row.get('max_value') else None)
			updated_attr = {
				'result': result_value,
				'min_value': convert_if_whole(row.get('min_value')) or None,
				'max_value': convert_if_whole(row.get('max_value')) or None,
				'grade': row.get('grade', None),
				'uom': row.get('uom', None),
				'status': row.get('status'),
				'incdec': row.get('incdec', None),
				'incdec_desc': row.get('incdec_desc', None),
				'description': grade_desc,
				'std_value': std_value,
			}
			result[0][1].update(updated_attr)
		else:
			for row in result_rows:
				result.append(build_result_dict(
					row, item['examination_item'], item_group, 'lab_test_grade', 'lab Test'))
	return result

def __create_nurse_category(appointment, item, item_group, bp):
	result = []
	if item['examination_item'] == bp:
		return ___create_blood_pressure_exam(appointment, item, item_group)
	result_in_exam, is_single_result = frappe.db.get_value(
		'Nurse Examination Template', {'item_code': item['examination_item']}, 
		['result_in_exam', 'is_single_result'])
	doc_no = frappe.db.get_value('Nurse Examination Request',
		{
			'parent': ['in', 
				frappe.db.get_all('Nurse Examination', pluck='name', 
					filters={'appointment': appointment, 'docstatus': 1})],
			'item': item['examination_item']
		}, 'parent')
	result.append(['nurse_grade', {
		'examination': item['item_name'],
		'gradable': item.get('item_gradable', 0),
		'hidden_item_group': item_group,
		'hidden_item': item['examination_item'],
		'is_item': 1, 
		'document_type': 'Nurse Examination', 
		'document_name': doc_no
	}])
	if not is_single_result and result_in_exam:
		result.extend(
			___create_nurse_result_per_item_in_exam(appointment, item['examination_item'], item_group))
	else:
		if result_in_exam:
			nurse_result = frappe.db.get_value('Nurse Examination', doc_no, 'exam_result')
			nr_doc = frappe.get_doc('Nurse Result', nurse_result)
			if nr_doc:
				result[0][1]['document_type'] = 'Nurse Result'
				result[0][1]['document_name'] = nurse_result
				result[0][1]['result'] = ', '. join([row.conclusion for row in nr_doc.conclusion])
		else:
			ne_doc = frappe.get_doc('Nurse Examination', doc_no)
			single_result = ___find_single_item_result(
				ne_doc.result, ne_doc.non_selective_result, item['examination_item'])
			if single_result:
				result[0][1].update(single_result)
				if item.get('item_gradable', 0):
					grade, description = assess_mcu_grade(
						result[0][1].get('result', ''), item_group, item['examination_item'],
						min_value=result[0][1].get('min_value', 0), max_value=result[0][1].get('max_value', 0),
						normal_value=result[0][1].get('normal_value', 0))
					if grade:
						result[0][1].update({'grade': grade, 'description': description})
				if result[0][1].get('normal_value'):
					result[0][1].pop('normal_value')
	return result

def ___find_single_item_result(result_table, non_selective_table, item_code):
  return next((
		{'result': r.result_value, 'min_value': r.min_value, 'max_value': r.max_value} 
		for r in (non_selective_table or []) if r.item_code == item_code), 
    	next((
				{'result': f"{r.result_check}: {r.result_text}" 
		 			if r.result_check and r.result_text else (r.result_check or ""), 
				'normal_value': r.normal_value}
				for r in (result_table or []) if r.item_code == item_code), {}))

def __create_radiology_category(appointment, item, item_group):
	result = []
	doc_no = frappe.db.get_value('Radiology Request',
		{
			'parent': ['in', 
				frappe.db.get_all('Radiology Result', pluck='name', 
					filters={'appointment': appointment, 'docstatus': 1})],
			'item': item['examination_item']
		}, 'parent')
	r_doc = frappe.get_doc('Radiology Result', doc_no)
	result.append(['radiology_grade', {
		'examination': item['item_name'],
		'gradable': item.get('item_gradable', 0),
		'hidden_item_group': item_group,
		'hidden_item': item['examination_item'],
		'is_item': 1, 
		'document_type': 'Radiology Result', 
		'document_name': doc_no,
		'result': ', '. join([row.conclusion for row in r_doc.conclusion]),
	}])
	return result

def ___fetch_lab_result_per_item(appointment, item_code, item_group):
	sql_args = {
		'appt': appointment,
		'item': item_code,
		'group': item_group
	}
	sql = """
		SELECT idx, result_line, min_value, max_value, result_text, uom, doc, status, gradable,
			IF(STRCMP(incdec,'---'), incdec, NULL) incdec,
			(SELECT description FROM `tabMCU Category`
				WHERE name = CONCAT_WS('.', %(group)s, %(item)s, result_line, incdec)) AS incdec_desc,
			IF(STRCMP(incdec,'---'), NULL,
				IF(gradable, CONCAT_WS('.',%(group)s, %(item)s, CONCAT(result_line,'-A')), 
					NULL)) AS grade
		FROM (
			SELECT tntr.idx, lab_test_event AS result_line, custom_min_value min_value, 
				custom_max_value AS max_value, CAST(result_value AS DECIMAL(10,3)) AS result_text,
				tntr.lab_test_uom AS uom, tntr.parent AS doc, tlt.status AS status,
				CASE
					WHEN (custom_min_value != 0 OR custom_max_value != 0) 
						AND CAST(result_value AS DECIMAL(10,3)) > custom_max_value 
						THEN 'Increase'
					WHEN (custom_min_value != 0 OR custom_max_value != 0) 
						AND CAST(result_value AS DECIMAL(10,3)) < custom_min_value 
						THEN 'Decrease'
					WHEN (custom_min_value != 0 OR custom_max_value != 0) 
						AND CAST(result_value AS DECIMAL(10,3)) BETWEEN custom_min_value AND custom_max_value
						THEN '---'
				END AS incdec,
				IFNULL((SELECT 1 FROM `tabMCU Grade` 
					WHERE name LIKE CONCAT_WS('.', %(group)s, %(item)s, CONCAT(lab_test_event,'%%')) LIMIT 1), 
					0) AS gradable
			FROM `tabNormal Test Result` tntr, `tabLab Test` tlt, `tabLab Test Template` tltt
			WHERE tntr.parent = tlt.name
			AND tlt.custom_appointment = %(appt)s
			AND tlt.docstatus IN (0, 1)
			AND tltt.item = %(item)s
			AND tltt.name = tntr.lab_test_name) AS a
		UNION
		SELECT idx, result_line, NULL, NULL, IF(text_value, CONCAT(result_text, ': ', text_value), result_text), 
			NULL, doc, status, gradable, NULL, NULL,
			IF(STRCMP(result_text, normal_value), NULL, 
				IF(gradable, CONCAT_WS('.',%(group)s, %(item)s, CONCAT(result_line,'-A')), NULL)) 
		FROM (SELECT tstt.idx + 500 AS idx, event AS result_line, result AS result_text, tlt.name AS doc, 
			tlt.status, tstt.normal_value, tstt.text_value,
			IFNULL((SELECT 1 FROM `tabMCU Grade` 
				WHERE name LIKE CONCAT_WS('.', %(group)s, %(item)s, CONCAT(event,'%%')) LIMIT 1), 0) AS gradable
		FROM  `tabSelective Test Template` tstt, `tabLab Test` tlt 
		WHERE tstt.parent = tlt.name AND tlt.custom_appointment = %(appt)s
		AND tlt.docstatus IN (0, 1) AND item = %(item)s) AS b ORDER BY 1"""
	return frappe.db.sql(sql, sql_args, as_dict=True)

#region Nurse
def ___create_nurse_result_per_item_in_exam(appointment, item, item_group):
	result = []
	result_rows = ____fetch_nurse_result_per_item(appointment, item, item_group)
	for row in result_rows:
		if row.result_line == 'BMI':
			result.append(____create_BMI_record(row, item, item_group))
		else:
			result.append(build_result_dict(row, item, item_group, 'nurse_grade', 'Nurse Examination'))
	return result

def ___create_blood_pressure_exam(appointment, item, item_group):
	to_return = []
	systolic_result = diastolic_result = grade = None
	systolic_line = diastolic_line = doc_no = incdec_category = None
	nurse_exams = frappe.db.get_all(
		'Nurse Examination', pluck='name',filters={'appointment': appointment, 'docstatus': 1})
	if not nurse_exams:
		return None
	results = frappe.get_all('Nurse Examination Result',
		fields=['name', 'test_name', 'result_value', 'min_value', 'max_value', 'parent', 'test_uom'],
		filters={'parent': ['in', nurse_exams], 'test_name': ['in', ['Systolic','Diastolic']]}
	)
	if not results:
		return None
	for result in results:
		try:
			result_value = int(result.result_value) if result.result_value else None
			min_value = int(result.min_value) if result.min_value else None
			max_value = int(result.max_value) if result.max_value else None
		except (ValueError, TypeError):
			continue
		if not all([result_value, min_value, max_value]):
			continue
		is_grade_a = min_value <= result_value <= max_value
		line = {
			'result_line': result.test_name,
			'gradable': 0,
			'result_text': result_value,
			'min_value': min_value,
			'max_value': max_value,
			'uom': result.test_uom,
			'status': 'Finished',
			'doc': result.parent,
		}
		if result.test_name == 'Systolic':
			systolic_result = result_value
			systolic_a_grade = is_grade_a
			systolic_line = line
		elif result.test_name == 'Diastolic':
			diastolic_result = result_value
			diastolic_a_grade = is_grade_a
			diastolic_line = line
		doc_no = result.parent
	if systolic_result is None or diastolic_result is None or not doc_no:
		return None
	incdec = (
		'Normal' if systolic_result < 120 and diastolic_result < 80 else
		'Prehypertension' if (120 <= systolic_result < 140 or 80 <= diastolic_result < 90) else
		'Stage 1 Hypertension' if (140 <= systolic_result < 160 or 90 <= diastolic_result < 100) else
		'Stage 2 Hypertension' if systolic_result >= 160 or diastolic_result >= 100 else
		None)
	if not incdec:
		return None
	incdec_category = frappe.db.get_value(
		'MCU Category', f'{item_group}.{item['examination_item']}..{incdec}', 'description')
	if systolic_a_grade and diastolic_a_grade:
		grade = f'{item_group}.{item['examination_item']}.-A'
	item_line =  ['nurse_grade', {
		'examination': item['item_name'],
		'gradable': item.get('item_gradable', 0),
		'hidden_item_group': item_group,
		'hidden_item': item['examination_item'],
		'is_item': 1, 
		'grade': grade,
		'incdec': incdec, 
		'incdec_category': incdec_category, 
		'document_type': 'Nurse Examination', 
		'document_name': doc_no
	}]
	to_return.append(item_line)
	if systolic_line:
		to_return.append(build_result_dict(
			systolic_line, item['examination_item'], item_group, 'nurse_grade', 'Nurse Examination'))
	if diastolic_line:
		to_return.append(build_result_dict(
			diastolic_line, item['examination_item'], item_group, 'nurse_grade', 'Nurse Examination'))
	return to_return

def ____fetch_nurse_result_per_item(appointment, item_code, item_group):
	sql_args = {
		'appt': appointment,
		'item': item_code,
		'group': item_group
	}
	sql = """
		SELECT idx, result_line, min_value, max_value, result_text, uom, doc, status, gradable,
			IF(STRCMP(incdec,'---'), incdec, NULL) incdec,
			(SELECT description FROM `tabMCU Category`
				WHERE name = CONCAT_WS('.', %(group)s, %(item)s, result_line, incdec)) AS incdec_desc,
			IF(STRCMP(incdec,'---'), NULL, 
				IF(gradable, CONCAT_WS('.', %(group)s, %(item)s, CONCAT(result_line,'-A')), 
					NULL)) AS grade
		FROM (
			SELECT tner.idx AS idx, test_name AS result_line, min_value, 
				max_value, CAST(result_value AS DECIMAL(10,3)) AS result_text, 
				test_uom AS uom, tne.name AS doc, tnerq.status AS status, 
				CASE 
					WHEN (min_value != 0 OR max_value != 0) 
						AND CAST(result_value AS DECIMAL(10,3)) > max_value 
						THEN 'Increase'
					WHEN (min_value != 0 OR max_value != 0) 
						AND CAST(result_value AS DECIMAL(10,3)) < min_value 
						THEN 'Decrease'
					WHEN (min_value != 0 OR max_value != 0) 
						AND CAST(result_value AS DECIMAL(10,3)) BETWEEN min_value AND max_value 
						THEN '---'
				END AS incdec,
				IFNULL((SELECT 1 FROM `tabMCU Grade` 
					WHERE name LIKE CONCAT_WS('.', %(group)s, %(item)s, CONCAT(result_line, '%%')) LIMIT 1), 
					0) AS gradable
			FROM `tabNurse Examination Result` tner, `tabNurse Examination` tne, 
				`tabNurse Examination Request` tnerq
			WHERE tne.appointment = %(appt)s
			AND tne.docstatus = 1
			AND tne.name = tner.parent
			AND tne.name = tnerq.parent
			AND tner.item_code = %(item)s
			AND EXISTS (
				SELECT 1 FROM `tabNurse Examination Template` tnet 
				WHERE tnet.item_code = tner.item_code AND tnerq.template = tnet.item_name)
		) AS a
		UNION
		SELECT idx, result_line, NULL, NULL, 
			IF(result_text, CONCAT(result_check, ': ', result_text), result_check), 
			NULL, doc, status, gradable, NULL, NULL,
			IF(STRCMP(result_check, normal_value), NULL, 
				IF(gradable, CONCAT_WS('.',%(group)s, %(item)s, CONCAT(result_line,'-A')), NULL)) 
		FROM (
			SELECT tnesr.idx+100 AS idx, result_line, normal_value, result_text, result_check, 
				tne.name AS doc, tnerq.status,
				IFNULL((SELECT 1 FROM `tabMCU Grade` 
					WHERE name LIKE CONCAT_WS('.', %(group)s, %(item)s, CONCAT(result_line, '%%')) LIMIT 1), 
					0) AS gradable
			FROM `tabNurse Examination Selective Result` tnesr, `tabNurse Examination` tne, 
				`tabNurse Examination Request` tnerq
			WHERE tne.name = tnesr.parent AND tne.appointment = %(appt)s AND tne.docstatus = 1 
			AND tnesr.item_code = %(item)s AND tnerq.parent = tne.name 
			AND EXISTS (SELECT 1 FROM `tabNurse Examination Template` tnet 
				WHERE tnet.item_code = tnesr.item_code AND tnerq.template = tnet.item_name)) AS b
		UNION
		SELECT tce.idx+200, test_label, NULL, NULL, FORMAT(result, 2), NULL, tne.name, tnerq.status, 
			0, NULL, NULL, NULL
		FROM `tabCalculated Exam` tce, `tabNurse Examination` tne, `tabNurse Examination Request` tnerq
		WHERE tne.name = tce.parent AND tne.appointment = %(appt)s AND tne.docstatus = 1 
		AND tce.item_code = %(item)s AND tnerq.parent = tne.name 
		AND EXISTS (SELECT 1 FROM `tabNurse Examination Template` tnet 
			WHERE tnet.item_code = tce.item_code AND tnerq.template = tnet.item_name)
		ORDER BY idx"""
	return frappe.db.sql(sql, sql_args, as_dict=True)

def ____create_BMI_record(row, item, item_group):
	bmi = float(row.result_text)
	bmi_data = frappe.db.get_value('BMI Classification', 
		{'min_value': ['<=', bmi], 'max_value': ['>', bmi]}, 
		['name', 'grade'], as_dict=True)
	row.grade = f"{item_group}.{item}.BMI-{bmi_data['grade']}{bmi_data['name']}"
	row.incdec = bmi_data['name']
	row.incdec_desc = frappe.db.get_value('MCU Category', 
		f"{item_group}.{item}.BMI.{bmi_data['name']}", 'description') or None
	row.grade_desc = frappe.db.get_value('MCU Grade', row.grade, 'description')
	return build_result_dict(row, item, item_group, 'nurse_grade', 'Nurse Examination')
#endregion

#region Doctor
def ___fetch_doctor_result_per_item(doc_name, item, item_group):
	result = []
	non_selective = frappe.db.get_all('Doctor Examination Result', 
		filters={'parent': doc_name, 'item_code': item}, 
		fields=[
			'test_name as result_line', 'result_value as result_text', 
			'test_uom as uom', 'min_value', 'max_value', 'parent as doc'])
	selective = frappe.db.get_all('Doctor Examination Selective Result', 
		filters={'parent': doc_name, 'item_code': item}, 
		fields=[
			'result_line', 'result_check as result_text', 'result_text as result_desc', 'parent as doc'])
	if non_selective:
		result.extend([build_result_dict(ns, item, item_group, 'doctor_grade', 'Doctor Examination') 
			for ns in non_selective])
	if selective:
		result.extend([build_result_dict(s, item, item_group, 'doctor_grade', 'Doctor Examination') 
			for s in selective])
	return result

def ___build_doctor_tab_result(docname, item, item_group, tab):
	try:
		func = globals()[f'____process_{tab}']
		doc = frappe.get_doc('Doctor Examination', docname)
	except KeyError:
		func = lambda *args: []
	return func(doc, item, item_group)	

def ____process_physical_examination(doc, item, item_group):
	result = []
	result.append(_____process_eyes(doc, item, item_group))
	result.append(_____process_ears(doc, item, item_group))
	result.append(_____process_nose(doc, item, item_group))
	result.append(_____process_thrt(doc, item, item_group))
	result.append(_____process_neck(doc, item, item_group))
	result.append(_____process_card(doc, item, item_group))
	result.append(_____process_brst(doc, item, item_group))
	result.append(_____process_resp(doc, item, item_group))
	result.append(_____process_abdm(doc, item, item_group))
	result.append(_____process_spne(doc, item, item_group))
	result.append(_____process_gent(doc, item, item_group))
	result.append(_____process_neur(doc, item, item_group))
	result.append(_____process_skin(doc, item, item_group))
	return result

def _____process_eyes(doc, item, item_group):
	data = {
		'result_line': 'Eyes',
		'gradable': 0,
		'doc': doc.name,
		'result_text': build_dual_result_text(
			'eyes_check',
			[[('left_anemic', 'Anemic', None), 
				('left_icteric', 'Icteric', None), 
				('el_others', 'Left Others', 'eyes_left_others')],
				[('right_anemic', 'Anemic', None), 
				('right_icteric', 'Icteric', None), 
				('er_others', 'Left Others', 'eyes_right_others')]],
			doc)
	}
	return build_result_dict(data, item, item_group, 'doctor_grade', 'Doctor Examination')

def _____process_ears(doc, item, item_group):
	data = {
		'result_line': 'Ears',
		'gradable': 0,
		'doc': doc.name,
		'result_text': build_dual_result_text(
			'ear_check',
			[[('left_cerumen', 'Cerumen', None), 
				('left_cerumen_prop', 'Cerumen Prop', None), 
				('left_tympanic', 'Tympanic membrance intact', None), 
				('earl_others', 'Others', 'ear_left_others')],
				[('right_cerumen', 'Cerumen', None), 
				('right_cerumen_prop', 'Cerumen Prop', None), 
				('right_tympanic', 'Tympanic membrance intact', None), 
				('earr_others', 'Others', 'ear_right_others')]],
			doc)
	}
	return build_result_dict(data, item, item_group, 'doctor_grade', 'Doctor Examination')

def _____process_nose(doc, item, item_group):
	data = {
		'result_line': 'Nose',
		'gradable': 0,
		'doc': doc.name,
		'result_text': build_dual_result_text(
			'nose_check',
			[[('left_enlarged', 'Enlarged', None), 
				('left_hyperemic', 'Hyperemic', None), 
				('left_polyp', 'Polyp', None), 
				('nl_others', 'Others', 'nose_left_others')],
				[('right_enlarged', 'Enlarged', None), 
				('right_hyperemic', 'Hyperemic', None), 
				('right_polyp', 'Polyp', None), 
				('nr_others', 'Others', 'nose_right_others')]],
			doc,
			extra_conditions=[('deviated', 'Deviated')])
	}
	return build_result_dict(data, item, item_group, 'doctor_grade', 'Doctor Examination')

def _____process_thrt(doc, item, item_group):
	data = {
		'result_line': 'Throat',
		'gradable': 0,
		'doc': doc.name,
		'result_text': build_result_text(
			'throat_check',
			[('enlarged_tonsil', 'Enlarged Tonsil', None), 
				('hyperemic_pharynx', 'Hyperemic Pharynx', None), 
				('t_others', 'Others', 'throat_others')],
			doc)
	}
	return build_result_dict(data, item, item_group, 'doctor_grade', 'Doctor Examination')

def _____process_neck(doc, item, item_group):
	data = {
		'result_line': 'Neck',
		'gradable': 0,
		'doc': doc.name,
		'result_text': build_result_text(
			'neck_check',
			[('enlarged_thyroid', 'Enlarged Thyroid', 'enlarged_thyroid_details'), 
				('enlarged_lymph_node', 'Enlarged Lymph Node', 'enlarged_lymph_node_details'), 
				('n_others', 'Others', 'neck_others')],
			doc)
	}
	return build_result_dict(data, item, item_group, 'doctor_grade', 'Doctor Examination')

def _____process_card(doc, item, item_group):
	data = {
		'result_line': 'Cardiac',
		'gradable': 0,
		'doc': doc.name,
		'result_text': build_result_text(
			'cardiac_check',
			[('regular_heart_sound', 'Regular Heart Sound', None), 
				('murmur', 'Murmur', None), 
				('gallop', 'Gallop', None), 
				('c_others', 'Others', 'cardiac_others')],
			doc)
	}
	return build_result_dict(data, item, item_group, 'doctor_grade', 'Doctor Examination')

def _____process_brst(doc, item, item_group):
	data = {
		'result_line': 'Breast',
		'gradable': 0,
		'doc': doc.name,
		'result_text': build_dual_result_text(
			'breast_check',
			[[('left_enlarged_breast', 'Enlarged Breast Glands', None), 
				('left_lumps', 'Lumps', None), 
				('bl_others', 'Others', 'breast_left_others')],
				[('right_enlarged_breast', 'Enlarged Breast Glands', None), 
				('right_lumps', 'Lumps', None), 
				('br_others', 'Others', 'breast_right_others')]],
			doc)
	}
	return build_result_dict(data, item, item_group, 'doctor_grade', 'Doctor Examination')

def _____process_resp(doc, item, item_group):
	data = {
		'result_line': 'Respiratory System',
		'gradable': 0,
		'doc': doc.name,
		'result_text': build_dual_result_text(
			'resp_check',
			[[('left_ronkhi', 'Ronkhi', None), 
				('left_wheezing', 'Wheezing', None), 
				('r_others', 'Others', 'resp_left_others')],
				[('right_ronkhi', 'Ronkhi', None), 
				('right_wheezing', 'Wheezing', None), 
				('rr_others', 'Others', 'resp_right_others')]],
			doc)
	}
	return build_result_dict(data, item, item_group, 'doctor_grade', 'Doctor Examination')

def _____process_abdm(doc, item, item_group):
	data = {
		'result_line': 'Abdomen',
		'gradable': 0,
		'doc': doc.name,
		'result_text': build_result_text(
			'abd_check',
			[('tenderness', 'Tenderness', 'abd_tender_details'), 
				('hepatomegaly', 'Hepatomegaly', None), 
				('splenomegaly', 'Splenomegaly', None), 
				('increased_bowel_sounds', 'Increased Bowel Sounds', None), 
				('a_others', 'Others', 'abd_others')],
			doc)
	}
	return build_result_dict(data, item, item_group, 'doctor_grade', 'Doctor Examination')

def _____process_spne(doc, item, item_group):
	data = {
		'result_line': 'Spine',
		'gradable': 0,
		'doc': doc.name,
		'result_text': 'No Abnormality' if doc.cardiac_check else doc.spine_details,
	}
	return build_result_dict(data, item, item_group, 'doctor_grade', 'Doctor Examination')

def _____process_gent(doc, item, item_group):
	data = {
		'result_line': 'Genitourinary',
		'gradable': 0,
		'doc': doc.name,
		'result_text': build_result_text(
			'genit_check',
			[('hernia', 'Hernia', 'hernia_details'), 
				('hemorrhoid', 'Hemorrhoid', None), 
				('inguinal_nodes', 'Inguinal Nodes', None), 
				('g_others', 'Others', 'genit_others')],
			doc)
	}
	return build_result_dict(data, item, item_group, 'doctor_grade', 'Doctor Examination')

def _____process_neur(doc, item, item_group):
	data = {
		'result_line': 'Neurological System',
		'gradable': 0,
		'doc': doc.name,
		'result_text': build_result_text(
			'neuro_check',
			[('motoric_system_abnormality', 'Motoric System Abnormality', 'motoric_details'), 
				('sensory_system_abnormality', 'Sensory System Abnormality', 'sensory_details'), 
				('reflexes_abnormality', 'Reflexes Abnormality', 'reflex_details'), 
				('ne_others', 'Others', 'neuro_others')],
			doc)
	}
	return build_result_dict(data, item, item_group, 'doctor_grade', 'Doctor Examination')

def _____process_skin(doc, item, item_group):
	data = {
		'result_line': 'Skin',
		'gradable': 0,
		'doc': doc.name,
		'result_text': build_result_text(
			'skin_check',
			[('skin_psoriasis', 'Psoriasis', None), 
				('skin_tattoo', 'Tattoo', 'skin_tattoo_location'), 
				('skin_tag', 'Skin Tag', None), 
				('sk_others', 'Others', 'skin_others')],
			doc)
	}
	return build_result_dict(data, item, item_group, 'doctor_grade', 'Doctor Examination')

def ____process_visual_field_test(doc, item, item_group):
	return {
		'result': 'Same As Examiner' if doc.visual_check else doc.visual_details,}

def ____process_romberg_test(doc, item, item_group):
	return {
		'result_text': 'No Abnormality' if doc.romberg_check else '\n'.join(filter(None, 
			[doc.romberg_abnormal or '', doc.romberg_others or ''])),
	}

def ____process_tinnel_test(doc, item, item_group):
	return {
		'result_text': 'No Abnormality' if doc.tinnel_check else doc.tinnel_details,
	}

def ____process_phallen_test(doc, item, item_group):
	return {
		'result_text': 'No Abnormality' if doc.phallen_check else doc.phallen_details,
	}

def ____process_rectal_test(doc, item, item_group):
	return {
		'result_text': build_result_text(
			'rectal_check',
			[('rectal_hemorrhoid', None, 'rectal_hemorrhoid'), 
				('enlarged_prostate', 'Enlarged Prostate', None), 
				('re_others', 'Others', 'rectal_others')],
			doc)
	}

def ____process_dental_examination(doc, item, item_group):
	return {
		'result': ', '. join([row.conclusion for row in doc.conclusion]),
		'grade': doc.grade_table[0].grade if doc.grade_table else None,
		'description': doc.grade_table[0].suggestion if doc.grade_table else None
	}
#endregion

#region utility
def build_result_text(check_field, fields, doc, prefix=None, separator=','):
	if not getattr(doc, check_field):
		result_list = []
		for field, label, detail_field in fields:
			if getattr(doc, field):
				result = label
				if detail_field and getattr(doc, detail_field):
					result += f' ({getattr(doc, detail_field)})'
				result_list.append(result)
		if not result_list:
			return f'{prefix + ": " if prefix else ""}No Abnormality'
		return f'{prefix + ": " if prefix else ""}{separator.join(result_list)}'
	return f'{prefix + ": " if prefix else ""}No Abnormality'

def build_dual_result_text(check_field, fields, doc, extra_conditions=None):
	results = []
	if not getattr(doc, check_field):
		left_text = build_result_text(check_field, fields[0], doc, 'Left')
		right_text = build_result_text(check_field, fields[1], doc, 'Right')
		results = [left_text, right_text]
		if extra_conditions:
			for condition_field, condition_text in extra_conditions:
				if getattr(doc, condition_field):
					results.append(condition_text)
		return '\n'.join(filter(None, results))
	return 'Left: No Abnormality\nRight: No Abnormality'

def build_result_dict(data, item, item_group, grade_key, document_type):
	grade_desc = frappe.db.get_value('MCU Grade', data.get('grade'), 'description') or None
	result_value = (
		f"{data['result_text']}: {data['result_desc']}" if data.get('result_desc') 
		else convert_if_whole(data.get('result_text')))
	std_value = (
		f"{convert_if_whole(data.get('min_value'))} - {convert_if_whole(data.get('max_value'))}" 
		if data.get('min_value') or data.get('max_value') else None)
	return [
		grade_key, {
			'examination': data.get('result_line'),
			'gradable': data.get('gradable', 0),
			'result': result_value,
			'min_value': convert_if_whole(data.get('min_value')) or None,
			'max_value': convert_if_whole(data.get('max_value')) or None,
			'grade': data.get('grade') or None,
			'std_value': std_value or None,
			'description': data.get('grade_desc', grade_desc) or None,
			'uom': data.get('uom') or None,
			'status': data.get('status', 'Finished'),
			'document_type': document_type,
			'document_name': data.get('doc'),
			'incdec': data.get('incdec') or None,
			'incdec_category': data.get('incdec_desc') or None,
			'hidden_item_group': item_group,
			'hidden_item': item,
			'is_item': 0
		}
	]

def get_conclusion(appointment, doctype, item):
	conclusions = frappe.db.get_all(
		'Radiology Conclusion Table', pluck = 'name',
		filters={
			'parent': [
				'in', 
				frappe.db.get_all(doctype, pluck='name', 
						filters={'appointment': appointment, 'docstatus': 1})],
			'item': item}
		)
	conclusion_text = []
	parent = ''
	for conclusion in conclusions:
		text, parent_get = frappe.db.get_value(
			'Radiology Conclusion Table', conclusion, ['conclusion', 'parent'])
		conclusion_text.append(text)
		parent = parent_get
	return ', '.join(conclusion_text), parent

def convert_if_whole(number):
	try:
		num = float(str(number).replace(',', '.'))
		return int(num) if num.is_integer() else num
	except ValueError:
		return number
#endregion