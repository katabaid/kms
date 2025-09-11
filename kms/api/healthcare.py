import frappe, re
from frappe.utils import now, today, now_datetime
from datetime import timedelta
from kms.mcu_dispatcher import _get_related_service_units


@frappe.whitelist()
def set_mqp_meal_time(exam_id):
	mqps = frappe.db.get_all(
		'MCU Queue Pooling', filters={'patient_appointment': exam_id}, pluck='name')
	for mqp in mqps:
		frappe.db.set_value('MCU Queue Pooling', mqp, {'meal_time': now(), 'meal_time_block': 1})

@frappe.whitelist()
def is_meal(exam_id, doctype=None, docname=None):
	def any_lab_done():
		return any(item.examination_item in lab_tests and item.status in valid_status for item in appt_exams)
	def all_radiology_done(statuses):
		return all(status in valid_status for status in statuses) if statuses else False

	appt_exams = frappe.db.get_all(
		'MCU Appointment', filters={'parent': exam_id}, fields=['examination_item', 'status'])
	radiology = [exam.exam_required for exam in frappe.get_doc('MCU Settings', 'MCU Settings').required_exam]
	lab_tests = frappe.db.get_all('Item', pluck='name', 
		filters=[['item_group', 'descendants of (inclusive)', 'Laboratory'],['custom_is_mcu_item', '=', 1]])
	#appt = frappe.get_doc('Patient Appointment', exam_id)
	if not frappe.db.exists('Patient Appointment', {'name': exam_id, 'appointment_type': 'MCU'}):
		return False
	if frappe.db.get_value('Dispatcher', {'patient_appointment': exam_id}, 'had_meal'):
		return False
	if frappe.db.exists('MCU Queue Pooling', {'patient_appointment': exam_id, 'is_meal_time': 1}):
		return False
	radiology_exist = any(exam in [item['examination_item'] for item in appt_exams] for exam in radiology)
	lab_test_exist = any(exam in [item['examination_item'] for item in appt_exams] for exam in lab_tests)
	if not radiology_exist and not lab_test_exist:
		return False
	#check_list = (getattr(appt, 'custom_mcu_exam_items', []) or []) + \
	#	(getattr(appt, 'custom_additional_mcu_items', []) or [])
	valid_status = ['Finished', 'Refused', 'Rescheduled']
	if docname and doctype: # for room
		if doctype not in {'Sample Collection', 'Radiology'}:
			return False
		doc = frappe.get_doc(doctype, docname)
		radiology_statuses = [item.status for item in appt_exams if item.examination_item in radiology]
		if doctype == 'Sample Collection':
			return all_radiology_done(radiology_statuses) if radiology_exist else True
		current_radiology = [
			item.examination_item for item in appt_exams
			if item.examination_item in radiology and
			any(row.get("item") == item.examination_item for row in doc.examination_item)]
		other_radiology_statuses = [
			item.status for item in appt_exams
			if item.examination_item in radiology and
			item.examination_item not in current_radiology]
		if lab_test_exist:
			return any_lab_done() and all_radiology_done(other_radiology_statuses) and bool(current_radiology)
		else:
			all_radiology_done(other_radiology_statuses) and bool(current_radiology)
	else: # for dispatcher
		radiology_statuses = [item.status for item in appt_exams if item.examination_item in radiology]
		if not lab_test_exist:
			return all_radiology_done(radiology_statuses)
		elif not radiology_exist:
			return any_lab_done()  
		return any_lab_done() and all_radiology_done(radiology_statuses)

@frappe.whitelist()
def get_mcu_settings(is_item=False):
	base_fields = ['phallen_test', 'physical_examination', 'rectal_test', 'ecg',
		'romberg_test', 'tinnel_test', 'visual_field_test', 'dental_examination']
	fields = base_fields if is_item else [f'{f}_name' for f in base_fields]
	return frappe.db.sql(f"""SELECT field, value FROM tabSingles
		WHERE doctype = 'MCU Settings' AND field IN ({', '.join(['%s']*len(fields))})
		""", tuple(fields), as_dict=True)

@frappe.whitelist()
def get_ecg(exam_id):
	return frappe.db.sql("""
		SELECT parent
		FROM `tabNurse Examination Request` tner
		WHERE parent IN (
			SELECT name FROM `tabNurse Examination` tne 
			WHERE tne.appointment = %s and tne.docstatus IN (0,1))
		AND template = (
			SELECT value FROM tabSingles ts WHERE doctype = 'MCU Settings' and `field` = 'ecg_name')
	""", (exam_id), as_dict=True)

@frappe.whitelist()
def get_exam_items(root):
	exam_items_query = """
	SELECT name, item_name, item_group, custom_bundle_position
	FROM tabItem ti
	WHERE EXISTS (
		WITH RECURSIVE ItemHierarchy AS (
			SELECT name, parent_item_group, is_group, custom_bundle_position
			FROM `tabItem Group`
			WHERE parent_item_group = %s
			UNION ALL
			SELECT t.name, t.parent_item_group, t.is_group, t.custom_bundle_position
			FROM `tabItem Group` t
			INNER JOIN ItemHierarchy ih ON t.parent_item_group = ih.name
		)
		SELECT name FROM ItemHierarchy
		WHERE name = ti.item_group AND is_group = 0 AND ti.custom_is_mcu_item = 1
	);
	"""
	exam_group_query = """
	WITH RECURSIVE Hierarchy AS (
		SELECT name, parent_item_group, custom_bundle_position, is_group, 0 AS level
		FROM `tabItem Group`
		WHERE name = %s
		UNION ALL
		SELECT t.name, t.parent_item_group, t.custom_bundle_position, t.is_group, h.level + 1 AS level
		FROM `tabItem Group` t
		INNER JOIN Hierarchy h ON t.parent_item_group = h.name
	)
	SELECT name, parent_item_group, custom_bundle_position, is_group
	FROM Hierarchy
	WHERE name != %s
	ORDER BY level, custom_bundle_position;
	"""
	exam_items = frappe.db.sql(exam_items_query, (root,), as_dict=True)
	exam_group = frappe.db.sql(exam_group_query, (root, root), as_dict=True)
	return {'exam_items': exam_items, 'exam_group': exam_group}

@frappe.whitelist()
def create_eye_specialist_result(docname):
	exam = frappe.get_doc('Nurse Examination', docname)
	if not exam.service_unit:
		frappe.throw("Service Unit is required to create Eye Specialist Result.")
	if not frappe.db.exists('MCU Eye Specialist', {'eye_specialist_room': exam.service_unit}):
		frappe.throw(f"No Eye Specialist found for Service Unit: {exam.service_unit}")
	if frappe.db.exists('Nurse Result', {'exam': exam.name}):
		frappe.throw("Eye Specialist Result already exists for this appointment.")
	name, _ = create_result_doc(exam, 'Nurse Result')
	return name

@frappe.whitelist()
def is_eye_specialist_exam(hsu):
	return frappe.db.exists('MCU Eye Specialist', {'eye_specialist_room': hsu})

@frappe.whitelist()
def get_queued_branch(branch):
	sql = """SELECT thsu.name, COALESCE(COUNT(tdr.healthcare_service_unit), 0) AS status_count, 
		tra.`user`, thsu.custom_default_doctype
	FROM `tabHealthcare Service Unit` thsu
	LEFT JOIN `tabDispatcher Room` tdr 
		ON thsu.name = tdr.healthcare_service_unit 
		AND tdr.status in ('Waiting to Enter the Room', 'Ongoing Examination')
		AND EXISTS (SELECT 1 FROM tabDispatcher td WHERE td.name = tdr.parent and td.`date` = CURDATE())
	LEFT JOIN `tabRoom Assignment` tra 
		ON thsu.name = tra.healthcare_service_unit 
		AND tra.`date` = CURDATE()
	WHERE thsu.custom_branch = %s
	AND thsu.is_group = 0 
	AND thsu.custom_default_doctype IS NOT NULL
	GROUP BY thsu.name
	ORDER BY custom_room"""
	return frappe.db.sql(sql, (branch,), as_dict=True)

@frappe.whitelist()
def finish_exam(hsu, status, doctype, docname):
	exists_to_retest = False
	source_doc = frappe.get_doc(doctype, docname)
	is_sc = doctype == 'Sample Collection'
	exam_id = source_doc.custom_appointment if is_sc else source_doc.appointment
	dispatcher_id = source_doc.custom_dispatcher if is_sc else source_doc.dispatcher
	queue_pooling_id = source_doc.custom_queue_pooling if is_sc else source_doc.queue_pooling
	child = source_doc.custom_sample_table if is_sc else source_doc.examination_item
	related_rooms = _get_related_service_units(hsu, exam_id)
	no_target = frappe.db.exists('MCU Eye Specialist', {'eye_specialist_room': hsu})
	exists_to_retest = any(item.status == 'To Retest' for item in child)
	target = ''
	is_meal_time = is_meal(exam_id)
	room_count = 0
	final_count = 0
	final_status = ['Finished', 'Refused', 'Rescheduled', 'Partial Finished', \
		'Ineligible for Testing', 'Finished Collection']
	if dispatcher_id:
		if status == 'Removed':
			status = 'Wait for Room Assignment'
		doc = frappe.get_doc('Dispatcher', dispatcher_id)
		for room in doc.assignment_table:
			room_count += 1
			if room.status in final_status:
				final_count += 1
			if room.healthcare_service_unit in related_rooms:
				room.status = 'Additional or Retest Request' if exists_to_retest else status
		doc.status = 'Waiting to Finish' if room_count == final_count else 'In Queue'
		doc.room = ''
		if is_meal_time:
			doc.status = 'Meal Time'
			doc.had_meal = True
			doc.meal_time = now()
		doc.save(ignore_permissions=True)
	elif queue_pooling_id:
		item_status = ['Started', 'To Retest', 'To be Added']
		if not frappe.db.exists('MCU Appointment', {'parent': exam_id, 'status': ['in', item_status]}):
			frappe.db.set_value('Patient Appointment', exam_id, 'status', 'Ready to Check Out')
		qps = frappe.get_all('MCU Queue Pooling', filters={'patient_appointment': exam_id}, pluck='name')
		meal_time = now()
		submit_time = now_datetime()
		for qp in qps:
			if is_meal_time:
				frappe.db.set_value(
					'MCU Queue Pooling', qp, {'is_meal_time': 1, 'meal_time': meal_time, 'had_meal': 0})
			delay_in_minutes = frappe.db.get_single_value('MCU Settings', 'queue_pooling_submit_delay')
			if delay_in_minutes:
				delay_time = submit_time + timedelta(minutes=delay_in_minutes)
				frappe.db.set_value('MCU Queue Pooling', qp, 'delay_time', delay_time)
			else:
				frappe.db.set_value('MCU Queue Pooling', qp, 'in_room', 0)
			#room_count += 1
			#if frappe.db.get_value('MCU Queue Pooling', qp, 'status') in final_status:
			#	final_count += 1
			if frappe.db.get_value('MCU Queue Pooling', qp, 'service_unit') in related_rooms:
				status_to_set = 'Additional or Retest Request' if exists_to_retest else status
				frappe.db.set_value('MCU Queue Pooling', qp, 'status', status_to_set)
		#if  final_count+1 >= room_count:
		#	frappe.db.set_value('Patient Appointment', exam_id, 'status', 'Ready to Check Out')
	if (status == 'Finished' or status == 'Partial Finished') and not exists_to_retest and not no_target:
		match doctype:
			case 'Radiology':
				target = 'Radiology Result'
			case 'Nurse Examination':
				target = 'Nurse Result'
			case 'Sample Collection':
				target = 'Lab Test'
		if target:
			result_doc_name, patient = create_result_doc(source_doc, target)
			return {'message': 'Finished', 'docname': result_doc_name, 'patient': patient}
	return {'message': 'Finished'}

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
				lab_test_sql = """SELECT tltt.name, tltt.lab_test_code FROM `tabLab Test Template` tltt, tabItem ti
					WHERE tltt.sample = %s AND ti.name = tltt.lab_test_code
					AND EXISTS (SELECT 1 FROM `tabLab Test Request` tltr
						WHERE tltr.item_code = tltt.item AND tltr.parent = %s
						AND tltr.parentfield = 'custom_examination_item'
						AND tltr.parenttype = 'Sample Collection')
					ORDER BY ti.custom_bundle_position"""
				lab_test = frappe.db.sql(lab_test_sql, (item.sample, doc.name), as_dict=True)
				for exam in lab_test:
					template_doc = frappe.get_doc('Lab Test Template', exam.name)
					non_selective = template_doc.get('normal_test_templates')
					selective = template_doc.get('custom_selective')
					if non_selective:
						match = re.compile(r'(\d+) Years?').match(doc.patient_age)
						age = int(match.group(1)) if match else None
						minmax_sql = """WITH ranked AS (
								SELECT parent, lab_test_event, lab_test_uom, custom_age,
									custom_sex, custom_min_value, custom_max_value, idx,
									ROW_NUMBER() OVER (PARTITION BY parent, lab_test_event ORDER BY custom_age DESC) as rn
								FROM `tabNormal Test Template`
								WHERE parent = %(test)s
									AND (%(sex)s IS NULL OR custom_sex = %(sex)s)
									AND custom_age <= %(age)s)
							SELECT lab_test_event, lab_test_uom, custom_min_value, custom_max_value
							FROM ranked WHERE rn = 1 ORDER BY idx"""
						minmax_val = {'age': age, 'test': exam.name, 'sex': doc.patient_sex}
						minmax = frappe.db.sql(minmax_sql, minmax_val, as_dict=True)
						for mm in minmax:
							new_doc.append('normal_test_items', {
								'lab_test_name': exam.name, 
								'custom_min_value': mm.custom_min_value, 
								'custom_max_value': mm.custom_max_value, 
								'lab_test_event': mm.lab_test_event, 
								'lab_test_uom': mm.lab_test_uom,
								'custom_sample': item.sample,
								'custom_item': exam.lab_test_code
							})
							normal_toggle = 1
					if selective:
						for sel in template_doc.custom_selective:
							new_doc.append('custom_selective_test_result', {
								'item': template_doc.item,
								'event': sel.event,
								'result_set': sel.result_select, 
								'result': sel.result_select.splitlines()[0],
								'sample': item.sample,
          			'normal_value': sel.normal_value,
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
			cnr_sql = """SELECT count(*) count 
				FROM `tabNurse Examination Template` tnet
				WHERE EXISTS (SELECT * FROM `tabNurse Examination Request` tner 
				WHERE tner.parent = %s AND tnet.name = tner.template)
				AND tnet.result_in_exam = 0"""
			count_nurse_result = frappe.db.sql(cnr_sql, (doc.name), as_dict = True)
			if count_nurse_result[0].count == 0:
				return None, None
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
	return new_doc.name, new_doc.patient_name
