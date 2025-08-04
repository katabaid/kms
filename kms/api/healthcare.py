import frappe
from frappe.utils import now

@frappe.whitelist()
def set_mqp_meal_time(exam_id):
	mqps = frappe.db.get_all(
		'MCU Queue Pooling', filters={'patient_appointment': exam_id}, pluck='name')
	for mqp in mqps:
		frappe.db.set_value('MCU Queue Pooling', mqp, {'meal_time': now(), 'meal_time_block': 1})

@frappe.whitelist()
def is_meal(exam_id, doctype=None, docname=None):
	def any_lab_done():
		return any(item.examination_item in lab_tests and item.status in valid_status for item in check_list)
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

