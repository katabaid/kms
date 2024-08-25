# Copyright (c) 2024, GIS and contributors
# For license information, please see license.txt

import frappe, re
from frappe.model.document import Document
from frappe.utils import today
from frappe import _

class Dispatcher(Document):
	def after_insert(self):
		if self.name:
			self.queue_no = self.name.split('-')[-1].lstrip('0')
			self.db_update()

	def validate(self):
		if self.status == "In Queue":
			self.update_status_if_all_rooms_finished()
		if self.status == "Finished" and self.status_changed_to_finished():
			self.update_patient_appointment()
	
	def before_insert(self):
		if frappe.db.exists(self.doctype,{
			'patient_appointment': self.patient_appointment,
			'date': self.date,
		}):
			frappe.throw(_("Patient already in Dispatcher's queue."))

	def update_status_if_all_rooms_finished(self):
		finished_statuses = {'Refused', 'Finished', 'Rescheduled', 'Partial Finished'}
		if all(room.status in finished_statuses for room in self.assignment_table):
			self.status = 'Waiting to Finish'

	def status_changed_to_finished(self):
		doc_before_save = self.get_doc_before_save()
		return doc_before_save and doc_before_save.status != "Finished"

	def update_patient_appointment(self):
		if self.patient_appointment:
			appointment = frappe.get_doc("Patient Appointment", self.patient_appointment)
			if appointment.status not in {"Closed", "Checked Out"}:
				appointment.db_set('status', 'Checked Out', commit=True)
				frappe.msgprint(_("Patient Appointment {0} has been Checked Out.").format(self.patient_appointment))
		else:
			frappe.msgprint(_("No linked Patient Appointment found."))

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
	doc = frappe.get_doc('Dispatcher', dispatcher_id)
	doc.status = 'In Room'
	doc.room = hsu
	for room in doc.assignment_table:
		if room.healthcare_service_unit == hsu:
			room.status = 'Ongoing Examination'
			room.reference_doctype = doctype
			room.reference_doc = docname
	doc.save(ignore_permissions=True)
	return 'Checked In.'

@frappe.whitelist()
def removed_from_room(dispatcher_id, hsu):
	doc = frappe.get_doc('Dispatcher', dispatcher_id)
	doc.status = 'In Queue'
	doc.room = ''
	for room in doc.assignment_table:
		if room.healthcare_service_unit == hsu:
			room.status = 'Wait for Room Assignment'
			room.reference_doc = ''
	doc.save(ignore_permissions=True)
	return 'Removed from examination room.'

@frappe.whitelist()
def finish_exam(dispatcher_id, hsu, status):
	if status == 'Removed':
		status = 'Wait for Room Assignment'

	doc = frappe.get_doc('Dispatcher', dispatcher_id)

	room_count = 0
	final_count = 0
	final_status = ['Finished', 'Refused', 'Rescheduled', 'Partial Finished']
	target = ''

	related_rooms = frappe.db.sql(f"""
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
		)""", pluck = 'service_unit')

	for room in doc.assignment_table:
		room_count += 1
		if room.status in final_status:
			final_count += 1
		if room.healthcare_service_unit == hsu:
			doctype = room.reference_doctype
			docname = room.reference_doc
			room.status = status
		if room.healthcare_service_unit in related_rooms:
			room.status = status
	doc.status = 'Waiting to Finish' if room_count == final_count else 'In Queue'
	doc.room = ''
	doc.save(ignore_permissions=True)

	if status == 'Finished' or status == 'Partial Finished':
		source_doc = frappe.get_doc(doctype, docname)
		match doctype:
			case 'Radiology':
				target = 'Radiology Result'
			case 'Nurse Examination':
				target = 'Nurse Result'
			case 'Sample Collection':
				target = 'Lab Test'
		if target:
			result_doc_name = create_result_doc(source_doc, target)
			return {'message': 'Finished', 'docname': result_doc_name}
	return {'message': 'Finished'}

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

@frappe.whitelist()
def add_additional():
	pass

def create_result_doc(doc, target):
	not_created = True
	if target == 'Lab Test':
		not_created = False
		normal_toggle = 0
		new_doc = frappe.get_doc({
			'doctype': target,
			'company': doc.company,
			'custom_branch': doc.custom_branch,
			#'queue_pooling': doc.queue_pooling,
			'patient': doc.patient,
			'patient_name': doc.patient_name,
			'patient_sex': doc.patient_sex,
			'patient_age': doc.patient_age,
			#'patient_encounter': doc.patient_encounter,
			'custom_appointment': doc.custom_appointment,
			#'dispatcher': doc.dispatcher,
			#'service_unit': doc.service_unit,
			#'created_date': today(),
			#'remark': doc.remark,
			'custom_sample_collection': doc.name
		})
		for item in doc.custom_sample_table:
			if item.status == 'Finished':
				lab_test = frappe.db.sql(f"""
					SELECT name
					FROM `tabLab Test Template` tltt
					WHERE tltt.sample = '{item.sample}'
					AND EXISTS (
					SELECT 1 
					FROM `tabMCU Appointment` tma 
					WHERE tltt.name = tma.item_name
					AND tma.parent = '{doc.custom_dispatcher}'
					AND tma.parentfield = 'package'
					AND tma.parenttype = 'Dispatcher')""", pluck='name')
				for exam in lab_test:
					template_doc = frappe.get_doc('Lab Test Template', exam)
					non_selective = template_doc.get('normal_test_templates')
					selective = template_doc.get('custom_selective')
					if non_selective:
						match = re.compile(r'(\d+) Years?').match(doc.patient_age)
						age = int(match.group(1)) if match else None
						minmax = frappe.db.sql(f"""
							WITH cte AS (
								SELECT
									parent,
									lab_test_event,
									lab_test_uom,
									custom_age,
									custom_sex,
									custom_min_value,
									custom_max_value,
									MAX(CASE WHEN custom_age <= {age} THEN custom_age END) OVER (PARTITION BY parent, lab_test_event, custom_sex ORDER BY custom_age DESC) AS max_age
								FROM
									`tabNormal Test Template`
							)
							SELECT
								lab_test_event,
								lab_test_uom,
								COALESCE(
									(SELECT custom_min_value FROM cte WHERE parent = '{exam}' AND lab_test_event = c.lab_test_event AND custom_sex = '{doc.patient_sex}' AND max_age = {age} order by custom_age desc limit 1),
									(SELECT custom_min_value FROM cte WHERE parent = '{exam}' AND lab_test_event = c.lab_test_event AND custom_sex = '{doc.patient_sex}' AND custom_age = (SELECT MAX(max_age) FROM cte WHERE parent = '{exam}' AND lab_test_event = c.lab_test_event AND custom_sex = '{doc.patient_sex}' AND max_age < {age}))
								) AS custom_min_value,
								COALESCE(
									(SELECT custom_max_value FROM cte WHERE parent = '{exam}' AND lab_test_event = c.lab_test_event AND custom_sex = '{doc.patient_sex}' AND max_age = {age} order by custom_age desc limit 1),
									(SELECT custom_max_value FROM cte WHERE parent = '{exam}' AND lab_test_event = c.lab_test_event AND custom_sex = '{doc.patient_sex}' AND custom_age = (SELECT MAX(max_age) FROM cte WHERE parent = '{exam}' AND lab_test_event = c.lab_test_event AND custom_sex = '{doc.patient_sex}' AND max_age < {age}))
								) AS custom_max_value
							FROM
								cte c
							WHERE
								parent = '{exam}'
								AND custom_sex = '{doc.patient_sex}'
							GROUP BY
								lab_test_event;
						""", as_dict=True)
						for mm in minmax:
							new_doc.append('normal_test_items', {
								'lab_test_name': exam, 
								'custom_min_value': mm.custom_min_value, 
								'custom_max_value': mm.custom_max_value, 
								'lab_test_event': mm.lab_test_event, 
								'lab_test_uom': mm.lab_test_uom
							})
							normal_toggle = 1
					if selective:
						for sel in template_doc.custom_selective:
							new_doc.append('custom_selective_test_result', {
								'event': exam,
								'result_set': sel.result_select, 
								'result': sel.result_select.splitlines()[0]
							})
		new_doc.normal_toggle = normal_toggle
	else:
		new_doc = frappe.get_doc({
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
		for item in doc.examination_item:
			if item.status == 'Finished':
				new_doc.append('examination_item', {
					'status': 'Started',
					'template': item.template
				})
				match target:
					case 'Radiology Result':
						not_created = False
						template = 'Radiology Result Template'
						template_doc = frappe.get_doc(template, item.template)
						for result in template_doc.items:
							if result.sex:
								if result.sex == doc.patient_sex:
									new_doc.append('result', {
										'result_line': result.result_text,
										'normal_value': result.normal_value,
										'result_check': result.normal_value,
										'item_code': template_doc.item_code,
										'result_options': result.result_select
									})
							else:
								new_doc.append('result', {
									'result_line': result.result_text,
									'normal_value': result.normal_value,
									'result_check': result.normal_value,
									'item_code': template_doc.item_code,
									'result_options': result.result_select
								})
					case 'Nurse Result':
						template = 'Nurse Examination Template'
						template_doc = frappe.get_doc(template, item.template)
						if not template_doc.result_in_exam:
							for result in template_doc.items:
								new_doc.append('result', {
									'result_line': result.result_text,
									'normal_value': result.normal_value,
									'result_check': result.normal_value,
									'item_code': template_doc.item_code,
									'result_options': result.result_select
								})
							for selective_result in template_doc.normal_items:
								new_doc.append('non_selective_result', {
									'item_code': template_doc.item_code,
									'test_name': selective_result.heading_text,
									'test_event': selective_result.lab_test_event,
									'test_uom': selective_result.lab_test_uom,
									'min_value': selective_result.min_value,
									'max_value': selective_result.max_value
								})
							not_created = False
					case _:
						frappe.throw(f"Unhandled Template for {target} DocType.")
	if not not_created:
		new_doc.insert(ignore_permissions=True)
	return new_doc.name
