# Copyright (c) 2024, GIS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class Dispatcher(Document):
	def after_insert(self):
		if self.name:
			self.queue_no = self.name.split('-')[-1].lstrip('0')
			self.db_update()

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
	frappe.db.sql(f"""UPDATE `tabDispatcher` SET `status` = 'In Room', room = '{hsu}' WHERE `name` = '{dispatcher_id}'""")
	return 'Checked In.'

@frappe.whitelist()
def finish_exam(dispatcher_id, hsu, status):
	# Update Dispatcher Room status to Finished on selected room
	frappe.db.sql(f"""UPDATE `tabDispatcher Room` SET `status` = '{status}'  WHERE `parent` = '{dispatcher_id}' and healthcare_service_unit = '{hsu}'""")
	# Update Dispatcher Room status to Finished on related room
	frappe.db.sql(f"""
		UPDATE `tabDispatcher Room`
		SET `status` = '{status}'
		WHERE `parent` = '{dispatcher_id}'
		AND healthcare_service_unit IN (
			SELECT name 
			FROM `tabHealthcare Service Unit` thsu1
			WHERE EXISTS (
				SELECT 1 
				FROM `tabHealthcare Service Unit` thsu 
				WHERE EXISTS (
					SELECT 1 FROM `tabDispatcher Room` tdr
					WHERE tdr.parent = '{dispatcher_id}'
					AND tdr.parenttype = 'Dispatcher'
					AND tdr.parentfield = 'assignment_table'
					AND tdr.healthcare_service_unit  = '{hsu}'
					AND tdr.healthcare_service_unit = thsu.name)
				AND thsu.service_unit_type = thsu1.service_unit_type
				AND thsu.custom_branch = thsu1.custom_branch
				AND thsu1.name != '{hsu}'
			)
			AND EXISTS (
				SELECT 1
				FROM `tabDispatcher Room` tdr
				WHERE tdr.parent = '{dispatcher_id}'
				AND tdr.parenttype = 'Dispatcher'
				AND tdr.parentfield = 'assignment_table'
				AND tdr.healthcare_service_unit  = thsu1.name
			)
		)
	""")
	# Update Dispatcher status to Finished
	frappe.db.sql(f"""UPDATE `tabDispatcher` SET `status` = 'In Queue', room = '' WHERE `name` = '{dispatcher_id}'""")
	return 'Finished.'

@frappe.whitelist()
def removed_from_room(dispatcher_id, hsu):
	frappe.db.sql(f"""UPDATE `tabDispatcher Room` SET `status` = 'Wait for Room Assignment', reference_doctype = '', reference_doc = ''  WHERE `parent` = '{dispatcher_id}' and healthcare_service_unit = '{hsu}'""")
	frappe.db.sql(f"""UPDATE `tabDispatcher` SET `status` = 'In Queue', room = '' WHERE `name` = '{dispatcher_id}'""")
	return 'Removed from examination room.'

@frappe.whitelist()
def update_exam_item_status(dispatcher_id, examination_item, status):
	flag = frappe.db.sql(f""" SELECT 1 result FROM `tabMCU Appointment` tma WHERE `parent` = '{dispatcher_id}'  and item_name = '{examination_item}' UNION ALL SELECT 2 result FROM `tabMCU Appointment` tma WHERE `parent` = '{dispatcher_id}' and EXISTS (SELECT 1 FROM `tabLab Test Template` tltt WHERE tltt.sample = '{examination_item}' AND tltt.name = tma.item_name) """, as_dict=True)
	print('-------------------')
	print(flag[0].result)
	if flag[0].result == 1:
		frappe.db.sql(f"""UPDATE `tabMCU Appointment` SET `status` = '{status}' WHERE parent = '{dispatcher_id}' AND item_name = '{examination_item}' AND parentfield = 'package' AND parenttype = 'Dispatcher'""")
	elif flag[0].result == 2:
		items = frappe.db.sql(f"""SELECT name FROM `tabMCU Appointment` tma WHERE `parent` = '{dispatcher_id}' and EXISTS (SELECT 1 FROM `tabLab Test Template` tltt WHERE tltt.sample = '{examination_item}' AND tltt.name = tma.item_name)""", as_dict=True)
		for item in items:
			frappe.db.sql(f"""UPDATE `tabMCU Appointment` SET `status` = '{status}' WHERE name = '{item.name}'""")
	else:
		frappe.throw(f"Examination item {examination_item} does not exist.")
	return f"""Updated Dispatcher item: {examination_item} status to {status}."""