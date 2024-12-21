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

def get_columns():
	return [
		make_column(_('Exam Date'), 'exam_date', 'Date', 100),
		make_column(_('Room'), 'room', 'Data', 200),
		make_column(_('Patient'), 'patient', 'Data', 250),
		make_column(_('Package'), 'package', 'Data', 100),
		make_column(_('Exam ID'), 'exam_id', 'Data', 200),
		make_column(_('Exam Item'), 'exam_item', 'Data', 250),
		make_column(_('DOB'), 'dob', 'Date', 100),
		make_column(_('Company'), 'company', 'Data', 150),
		make_column(_('Sex'), 'sex', 'Data', 100),
	]

def get_data(filters):
	filters.department = filters.department or ''
	filters.room = filters.room or ''
	return frappe.db.sql(f"""
		SELECT tpa.appointment_date exam_date, tigsu.service_unit room, tpa.patient, 
			tpa.mcu package, tpa.name exam_id, GROUP_CONCAT(tpbi.description SEPARATOR ', ') exam_item,
			tp.dob, tp.custom_company company, tpa.patient_sex sex
		FROM `tabPatient Appointment` tpa, 
			`tabProduct Bundle Item` tpbi, 
			`tabItem Group Service Unit` tigsu, 
			`tabHealthcare Service Unit` thsu,
			tabPatient tp
		WHERE tpa.appointment_type = 'MCU'
		AND tpa.appointment_date =	'{filters.exam_date}'
		AND tpa.custom_branch = tigsu.branch 
		AND tpbi.parent = tpa.mcu 
		AND tpbi.item_code = tigsu.parent
		AND tpa.custom_branch = '{filters.branch}'
		AND tigsu.service_unit = thsu.name
		AND thsu.name LIKE '%{filters.room}'
		AND thsu.service_unit_type LIKE '%{filters.department}'
		AND tp.name = tpa.patient 
		group by tpa.patient, tpa.appointment_date, tigsu.service_unit""", as_dict = 1)