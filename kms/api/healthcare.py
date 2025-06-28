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
	appt = frappe.get_doc('Patient Appointment', exam_id)
	if not appt.mcu:
		return False
	dispatcher_exists = frappe.db.exists('Dispatcher', 
		frappe.db.get_value('Dispatcher', {'patient_appointment': exam_id}, 'name'))
	if dispatcher_exists:
		if frappe.db.get_value('Dispatcher', {'patient_appointment': exam_id}, 'had_meal'):
			return False
	else:
		if frappe.db.exists(
			'MCU Queue Pooling', {'patient_appointment': exam_id, 'is_meal_time': 1}):
			return False

	check_list = (getattr(appt, "custom_mcu_exam_items", []) or []) + \
		(getattr(appt, "custom_additional_mcu_items", []) or [])
	mcu_setting = frappe.get_doc("MCU Settings", "MCU Settings")
	radiology = [exam.exam_required for exam in mcu_setting.required_exam]
	lab_test = frappe.db.get_all(
		'Item', pluck='name', 
		filters=[["item_group", "descendants of (inclusive)", "Laboratory"],["custom_is_mcu_item", "=", 1]])
	valid_status = ['Finished', 'Refused', 'Rescheduled']
	lab_test_result = False
	radiology_items = []
	if docname and doctype: # for room 
		doc = frappe.get_doc(doctype, docname)
		hsu = doc.custom_service_unit if doctype == 'Sample Collection' else doc.service_unit
		if doctype == 'Sample Collection':
			lab_test_result = True
			for item in check_list:
				if item.examination_item in radiology:
					radiology_items.append(item.status)
			if radiology_items:
				radiology_result = all(status in valid_status for status in radiology_items)
			else:
				radiology_result = False
		else:
			current_item = False
			for item in check_list:
				if item.examination_item in lab_test and item.status in valid_status:
					lab_test_result = True
				if item.examination_item in radiology:
					if any(row.get("item") == item.examination_item for row in doc.examination_item):
						current_item = True
					else:
						radiology_items.append(item.status)
			if radiology_items:
				radiology_result = all(status in valid_status for status in radiology_items)
			else:
				radiology_result = True if current_item else False
		return lab_test_result and radiology_result
	else: # for dispatcher
		for item in check_list:
			if item.examination_item in lab_test and item.status in valid_status:
				lab_test_result = True
			if item.examination_item in radiology:
				radiology_items.append(item.status)
		if radiology_items:
			radiology_result = all(status in valid_status for status in radiology_items)
		else:
			radiology_result = False
		return lab_test_result and radiology_result
