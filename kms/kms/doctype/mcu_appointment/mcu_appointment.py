# Copyright (c) 2024, GIS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class MCUAppointment(Document):
	pass

@frappe.whitelist()
def fetch_mcu_appointment(sample_reception_name):
	"""
	Fetch MCU Appointment items for a given Sample Reception.
	
	Filters:
	- Item Group is descendant of "Laboratory"
	- Item is linked to Lab Test Template
	- Lab Test Template's sample matches Sample Reception's lab_test_sample
	
	Returns data separated by parentfield: custom_mcu_exam_items and custom_additional_mcu_items
	
	Args:
		sample_reception_name (str): The name of the Sample Reception document
		
	Returns:
		dict: Contains two lists - 'exam_items' and 'additional_items'
	"""
	if not sample_reception_name:
		return {'exam_items': [], 'additional_items': []}
	
	# Get Sample Reception document to find the appointment and lab_test_sample
	sr_doc = frappe.get_doc('Sample Reception', sample_reception_name)
	
	if not sr_doc.appointment:
		return {'exam_items': [], 'additional_items': []}
	
	lab_test_sample = sr_doc.lab_test_sample
	
	# Get Patient Appointment
	appointment_name = sr_doc.appointment
	
	# SQL to check if item group is descendant of Laboratory
	# Using recursive CTE similar to lab_sample.py
	item_group_filter = """
		WITH RECURSIVE ItemHierarchy AS (
			SELECT name, parent_item_group, is_group
			FROM `tabItem Group` tig 
			WHERE parent_item_group = 'Laboratory'
			UNION ALL
			SELECT t.name, t.parent_item_group, t.is_group
			FROM `tabItem Group` t
			INNER JOIN ItemHierarchy ih ON t.parent_item_group = ih.name)
		SELECT name FROM ItemHierarchy
	"""
	
	# Fetch MCU Appointment items from Patient Appointment
	# Filter by item group descendant of Laboratory AND linked to Lab Test Template with matching sample
	query = """
		SELECT 
			mcu.examination_item as item_code,
			mcu.item_name,
			mcu.item_group,
			mcu.status,
			mcu.parentfield,
			mcu.name as mcu_item_name,
			tltt.name as lab_test_template,
			tltt.sample as lab_test_sample,
			tltt.lab_test_name
		FROM `tabMCU Appointment` mcu
		INNER JOIN `tabPatient Appointment` pa ON mcu.parent = pa.name
		LEFT JOIN `tabLab Test Template` tltt ON tltt.item = mcu.examination_item
		WHERE pa.name = %s
		AND mcu.item_group IN ({item_group_subquery})
		AND tltt.sample IS NOT NULL
		AND tltt.sample = %s
	""".format(item_group_subquery=item_group_filter)
	
	# Get exam items (custom_mcu_exam_items)
	exam_items_query = query + " AND mcu.parentfield = 'custom_mcu_exam_items' ORDER BY mcu.idx"
	exam_items = frappe.db.sql(exam_items_query, (appointment_name, lab_test_sample), as_dict=True)
	
	# Get additional items (custom_additional_mcu_items)
	additional_items_query = query + " AND mcu.parentfield = 'custom_additional_mcu_items' ORDER BY mcu.idx"
	additional_items = frappe.db.sql(additional_items_query, (appointment_name, lab_test_sample), as_dict=True)
	
	# Format the data for the datatable
	exam_items_data = []
	for item in exam_items:
		exam_items_data.append({
			'name': item.mcu_item_name,
			'item_code': item.item_code or '',
			'item_name': item.item_name or '',
			'item_group': item.item_group or '',
			'status': item.status or '',
			'lab_test_template': item.lab_test_template or '',
			'lab_test_sample': item.lab_test_sample or '',
			'lab_test_name': item.lab_test_name or ''
		})
	
	additional_items_data = []
	for item in additional_items:
		additional_items_data.append({
			'name': item.mcu_item_name,
			'item_code': item.item_code or '',
			'item_name': item.item_name or '',
			'item_group': item.item_group or '',
			'status': item.status or '',
			'lab_test_template': item.lab_test_template or '',
			'lab_test_sample': item.lab_test_sample or '',
			'lab_test_name': item.lab_test_name or ''
		})
	
	return {
		'exam_items': exam_items_data,
		'additional_items': additional_items_data
	}
