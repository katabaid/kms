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

	return items
	
@frappe.whitelist()
def get_queued_branch(branch):
	count = frappe.db.sql(f"""SELECT thsu.name, COALESCE(COUNT(tdr.healthcare_service_unit), 0) AS status_count, tra.`user` 
			FROM `tabHealthcare Service Unit` thsu
			LEFT JOIN `tabDispatcher Room` tdr ON thsu.name = tdr.healthcare_service_unit AND tdr.status in ('Waiting to Enter the Room', 'Ongoing Examination')
			LEFT JOIN `tabRoom Assignment` tra ON thsu.name = tra.healthcare_service_unit and tra.`date` = CURDATE()
			WHERE thsu.custom_branch = '{branch}' and thsu.is_group = 0
			GROUP BY thsu.name""", as_dict=True)
	return count

@frappe.whitelist()
def checkin_room(dispatcher_id, hsu, doctype, docname):
	frappe.db.sql(f"""UPDATE `tabDispatcher Room` SET `status` = 'Ongoing Examination', reference_doctype = '{doctype}', reference_doc = '{docname}'  WHERE `parent` = '{dispatcher_id}' and healthcare_service_unit = '{hsu}'""")
	return 'Checked In.'
@frappe.whitelist()
def finish_exam(dispatcher_id, hsu):
	frappe.db.sql(f"""UPDATE `tabDispatcher Room` SET `status` = 'Finished Examination'  WHERE `parent` = '{dispatcher_id}' and healthcare_service_unit = '{hsu}'""")
	return 'Finished Examination.'
@frappe.whitelist()
def removed_from_room(dispatcher_id, hsu):
	frappe.db.sql(f"""UPDATE `tabDispatcher Room` SET `status` = 'Wait for Room Assignment', reference_doctype = '', reference_doc = ''  WHERE `parent` = '{dispatcher_id}' and healthcare_service_unit = '{hsu}'""")
	return 'Removed from examination room.'