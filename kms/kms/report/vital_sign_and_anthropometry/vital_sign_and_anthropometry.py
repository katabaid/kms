# Copyright (c) 2024, GIS and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	message = frappe.db.get_value('Patient Appointment', filters.exam_id, 'patient_name')
	return columns, data, message

def make_column (label, name, type='Data', width=150, align='left'):
	return {
		'label': label,								'fieldname': name,						'fieldtype': type,
		'width': width,								'align': align
	}
def get_columns():
	return [
		make_column(_('Test Name'), 'test_name', 'Data', 250),
		make_column(_('Test Event'), 'test_event', 'Data', 250),
		make_column(_('Result Value'), 'result_value', 'Float', 100, 'right'),
		make_column(_('UOM'), 'test_uom', 'Data', 100),
		make_column(_('Min Value'), 'min_value', 'Float', 100, 'right'),
		make_column(_('Max Value'), 'max_value', 'Float', 100, 'right'),
	]
def get_data(filters):
	return frappe.db.sql(f"""
		SELECT test_name, test_event, result_value, test_uom, min_value, max_value FROM `tabNurse Examination Result` tner, `tabNurse Examination` tne 
		WHERE EXISTS (SELECT 1 FROM `tabNurse Examination Template` tnet WHERE tner.item_code = tnet.item_code 
		AND EXISTS (SELECT 1 FROM  `tabMCU Vital SIgn` tmvs WHERE tmvs.template = tnet.name))
		AND tne.name = tner.parent AND tne.appointment = '{filters.exam_id}' AND tne.docstatus = 1
		UNION
		SELECT test_label, NULL, `result`, NULL, NULL, NULL FROM `tabCalculated Exam` tce, `tabNurse Examination` tne 
		WHERE EXISTS (SELECT 1 FROM `tabNurse Examination Template` tnet WHERE tce.item_code = tnet.item_code 
		AND EXISTS (SELECT 1 FROM  `tabMCU Vital SIgn` tmvs WHERE tmvs.template = tnet.name))
		AND tne.name = tce.parent AND tne.appointment = '{filters.exam_id}' AND tne.docstatus = 1""", as_dict = 1)
