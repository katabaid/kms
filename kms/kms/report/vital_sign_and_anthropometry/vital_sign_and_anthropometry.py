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
		make_column(_('Result Value'), 'result_value', 'Data', 100, 'right'),
		make_column(_('UOM'), 'test_uom', 'Data', 100),
		make_column(_('Min Value'), 'min_value', 'Data', 100, 'right'),
		make_column(_('Max Value'), 'max_value', 'Data', 100, 'right'),
	]
def get_data(filters):
	return frappe.db.sql("""
		SELECT test_name, test_uom, min_value, max_value, tner.idx, custom_bundle_position, 
		CASE WHEN result_value MOD 1 = 0 THEN FORMAT(result_value, 0, 'id_ID')
    ELSE FORMAT(result_value, 1, 'id_ID') END result_value
		FROM `tabNurse Examination Result` tner, `tabNurse Examination` tne, tabItem ti
		WHERE tne.name = tner.parent AND tne.appointment = %s AND tne.docstatus = 1
		AND EXISTS (SELECT 1 FROM `tabNurse Examination Template` tnet WHERE tner.item_code = tnet.item_code
		AND EXISTS (SELECT 1 FROM  `tabMCU Vital Sign` tmvs WHERE tmvs.template = tnet.name))
		AND ti.name = tner.item_code
		UNION
		SELECT test_label, NULL, NULL, NULL, 999, custom_bundle_position,
		CASE WHEN result MOD 1 = 0 THEN FORMAT(result, 0, 'id_ID') ELSE FORMAT(result, 1, 'id_ID') END
		FROM `tabCalculated Exam` tce, `tabNurse Examination` tne, tabItem ti
		WHERE tne.name = tce.parent AND tne.appointment = %s AND tne.docstatus = 1
		AND EXISTS (SELECT 1 FROM `tabNurse Examination Template` tnet WHERE tce.item_code = tnet.item_code
		AND EXISTS (SELECT 1 FROM  `tabMCU Vital Sign` tmvs WHERE tmvs.template = tnet.name))
		AND ti.name = tce.item_code ORDER BY 6, 5""", (filters.exam_id, filters.exam_id), as_dict = True)
