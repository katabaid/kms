# Copyright (c) 2024, GIS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class Dispatcher(Document):
	pass
@frappe.whitelist()
def get_exam_items(dispatcher_id, hcsu, hcsu_type):
	items = frappe.db.sql(f"""select tma.examination_item from `tabMCU Appointment` tma, tabItem ti, `tabItem Group Service Unit` tigsu, `tabHealthcare Service Unit` thsu, `tabPatient Appointment` tpa, tabDispatcher td 
		where tma.parenttype = 'Dispatcher'
		and tma.parent = '{dispatcher_id}'
		and ti.name = tma.examination_item
		and ti.item_group = tigsu.parent
		and tigsu.service_unit  = '{hcsu}'
		and tigsu.parenttype = 'Item Group'
		and tigsu.service_unit = thsu.name
		and thsu.service_unit_type = '{hcsu_type}'
		and tma.parent = td.name 
		and td.patient_appointment = tpa.name 
		and tpa.custom_branch = tigsu.branch """, as_dict=True)
	if hcsu_type == 'Radiology':
		