# Copyright (c) 2025, GIS and contributors
# For license information, please see license.txt

import frappe


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	message = frappe.db.get_value('Patient Appointment', filters.exam_id, 'patient_name')
	return columns, data, message

def get_columns():
	return [
		{'label': 'Type', 'fieldname': 'type', 'fieldtype': 'Data', 'width': 100},
		{'label': 'Service Unit', 'fieldname': 'service_unit', 'fieldtype': 'Data', 'width': 200},
		{'label': 'Doc. No.', 'fieldname': 'doc_no', 'fieldtype': 'Data', 'width': 250},
		{'label': 'Exam Note', 'fieldname': 'exam_note', 'fieldtype': 'Small Text', 'width': 700},
	]

def get_data(filters):
	sql = frappe.db.sql(f"""
		SELECT 'Nurse' type, tne.name doc_no, tne.service_unit, tne.exam_note 
		FROM `tabNurse Examination` tne 
		WHERE tne.appointment = '{filters.exam_id}' AND tne.docstatus = 1
		AND tne.exam_note IS NOT NULL UNION
		SELECT 'Doctor', tde.name, tde.service_unit, tde.exam_note 
		FROM `tabDoctor Examination` tde 
		WHERE tde.appointment = '{filters.exam_id}' AND tde.docstatus = 1
		AND tde.exam_note IS NOT NULL UNION
		SELECT 'Radiology', tr.name, tr.service_unit, tr.exam_note 
		FROM `tabRadiology` tr 
		WHERE tr.appointment = '{filters.exam_id}' AND tr.docstatus = 1
		AND tr.exam_note IS NOT NULL UNION
		SELECT 'Sample', tsc.name, tsc.custom_service_unit, tsc.custom_exam_note 
		FROM `tabSample Collection` tsc 
		WHERE tsc.custom_appointment = '{filters.exam_id}' AND tsc.docstatus = 1
		AND tsc.custom_exam_note IS NOT NULL""", as_dict = 1)
	return sql