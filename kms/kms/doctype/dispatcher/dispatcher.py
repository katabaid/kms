# Copyright (c) 2024, GIS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import today

class Dispatcher(Document):
	def after_insert(self):
		if self.name:
			self.queue_no = self.name.split('-')[-1].lstrip('0')
			self.db_update()

@frappe.whitelist()
def get_queued_branch(branch):
	count = frappe.db.sql(f"""
		SELECT thsu.name, COALESCE(COUNT(tdr.healthcare_service_unit), 0) AS status_count, tra.`user` 
		FROM `tabHealthcare Service Unit` thsu
		LEFT JOIN `tabDispatcher Room` tdr ON thsu.name = tdr.healthcare_service_unit AND tdr.status in ('Waiting to Enter the Room', 'Ongoing Examination')
		LEFT JOIN `tabRoom Assignment` tra ON thsu.name = tra.healthcare_service_unit and tra.`date` = CURDATE()
		WHERE thsu.custom_branch = '{branch}' and thsu.is_group = 0
		GROUP BY thsu.name
		""", as_dict=True)
	return count

@frappe.whitelist()
def checkin_room(dispatcher_id, hsu, doctype, docname):
	frappe.db.sql(f"""
		UPDATE `tabDispatcher Room` 
		SET `status` = 'Ongoing Examination', reference_doctype = '{doctype}', reference_doc = '{docname}' 
		WHERE `parent` = '{dispatcher_id}' and healthcare_service_unit = '{hsu}'
		""")
	frappe.db.sql(f"""UPDATE `tabDispatcher` SET `status` = 'In Room', room = '{hsu}' WHERE `name` = '{dispatcher_id}'""")
	return 'Checked In.'

@frappe.whitelist()
def finish_exam(dispatcher_id, hsu, status):
	# Update Dispatcher Room status to Finished on selected room
	frappe.db.sql(f"""
		UPDATE `tabDispatcher Room` SET `status` = '{status}'  
		WHERE `parent` = '{dispatcher_id}' and healthcare_service_unit = '{hsu}'
		""")
	# Update Dispatcher Room status to Finished on related room
	frappe.db.sql(f"""
		UPDATE `tabDispatcher Room`
		SET `status` = '{status}'
		WHERE `parent` = '{dispatcher_id}'
		AND healthcare_service_unit IN (
			SELECT service_unit FROM `tabItem Group Service Unit` tigsu1
			WHERE tigsu1.parentfield = 'custom_room'
			AND 	tigsu1.parenttype = 'Item'
			AND 	tigsu1.service_unit != '{hsu}'
			AND 	EXISTS (
				SELECT 1 FROM `tabItem Group Service Unit` tigsu 
				WHERE tigsu.parentfield = 'custom_room'
				AND 	tigsu.parenttype = 'Item'
				AND 	tigsu.service_unit = '{hsu}'
				AND 	tigsu.parent = tigsu1.parent
				AND EXISTS (
					SELECT 1 FROM `tabMCU Appointment` tma
					WHERE tma.parent = '{dispatcher_id}'
					AND 	tma.parentfield = 'package'
					AND		tma.parenttype = 'Dispatcher'
					AND 	tma.examination_item = tigsu.parent
				)
			)
	""")
	#Verify whether all rooms are finished
	final_status = "('Finished', 'Refused', 'Rescheduled', 'Partial Finished')"
	room_count = frappe.db.sql(f"""
		SELECT COUNT(*) count FROM `tabDispatcher Room` WHERE `parent` = '{dispatcher_id}'
		""", as_dict=True)[0]['count']
	finished_room_count = frappe.db.sql(f"""
		SELECT COUNT(*) count 
		FROM `tabDispatcher Room` 
		WHERE `parent` = '{dispatcher_id}' 
		AND status in {final_status}
		""", as_dict=True)[0]['count']
	if room_count == finished_room_count:
		# Update Dispatcher status to Finished
		frappe.db.sql(f"""UPDATE `tabDispatcher` SET `status` = 'Waiting to Finish', room = ''  WHERE `name` = '{dispatcher_id}'""")
	else:
		# Update Dispatcher status to Finished
		frappe.db.sql(f"""UPDATE `tabDispatcher` SET `status` = 'In Queue', room = '' WHERE `name` = '{dispatcher_id}'""")
	#check whether status is Finished/Partial Finished
	if status == 'Finished' or status == 'Partial Finished':
		pass
		#doc = ''
		#target = ''
		#create_result_doc(doc, target)
	#determine hsu is using what doctype
	#get doctype's doc
	#create_result_doc(doc, source, target)
	return 'Finished.'

@frappe.whitelist()
def removed_from_room(dispatcher_id, hsu):
	frappe.db.sql(f"""
		UPDATE `tabDispatcher Room` 
		SET `status` = 'Wait for Room Assignment', reference_doctype = '', reference_doc = ''  
		WHERE `parent` = '{dispatcher_id}' and healthcare_service_unit = '{hsu}'
		""")
	frappe.db.sql(f"""
		UPDATE `tabDispatcher` SET `status` = 'In Queue', room = '' WHERE `name` = '{dispatcher_id}'
		""")
	return 'Removed from examination room.'

@frappe.whitelist()
def update_exam_item_status(dispatcher_id, examination_item, status):
	flag = frappe.db.sql(
		f"""
		SELECT 1 result 
		FROM `tabMCU Appointment` tma 
		WHERE `parent` = '{dispatcher_id}' 
		AND item_name = '{examination_item}' 
		UNION ALL 
		SELECT 2 result 
		FROM `tabMCU Appointment` tma 
		WHERE `parent` = '{dispatcher_id}' 
		AND EXISTS (SELECT 1 FROM `tabLab Test Template` tltt WHERE tltt.sample = '{examination_item}' AND tltt.name = tma.item_name)
		""", as_dict=True)
	if flag[0].result == 1:
		frappe.db.sql(f"""
			UPDATE `tabMCU Appointment` 
			SET `status` = '{status}' 
			WHERE parent = '{dispatcher_id}' 
			AND item_name = '{examination_item}' 
			AND parentfield = 'package' 
			AND parenttype = 'Dispatcher'
			""")
	elif flag[0].result == 2:
		items = frappe.db.sql(f"""
			SELECT name 
			FROM `tabMCU Appointment` tma 
			WHERE `parent` = '{dispatcher_id}' 
			AND EXISTS (SELECT 1 FROM `tabLab Test Template` tltt WHERE tltt.sample = '{examination_item}' AND tltt.name = tma.item_name)
			""", as_dict=True)
		for item in items:
			frappe.db.sql(f"""UPDATE `tabMCU Appointment` SET `status` = '{status}' WHERE name = '{item.name}'""")
	else:
		frappe.throw(f"Examination item {examination_item} does not exist.")
	return f"""Updated Dispatcher item: {examination_item} status to {status}."""

def create_result_doc(doc, target):
	doc = frappe.get_doc({
		'doctype': target,
		'company': doc.company,
		'branch': doc.branch,
		'queue_pooling': doc.queue_pooling,
		'patient': doc.patient,
		'patient_name': doc.patient_name,
		'patient_sex': doc.patient_sex,
		'patient_age': doc.patient_age,
		'patient_encounter': doc.patient_encounter,
		'appointment': doc.appointment,
		'dispatcher': doc.dispatcher,
		'service_unit': doc.service_unit,
		'created_date': today(),
		'remark': doc.remark,
		'exam': doc.name
	})
	doc.insert()
	#append items
	#append result
	#update exam_result in source ........
	#check whether source is finished/partial finished .........