# Copyright (c) 2024, GIS and contributors
# For license information, please see license.txt

import frappe, re
from frappe.model.document import Document
from frappe.utils import today, now, now_datetime
from frappe import _
from statistics import mean
from datetime import timedelta

FINISHED_STATUSES = {
  'Refused', 
  'Finished', 
  'Rescheduled', 
  'Partial Finished', 
  'Finished Collection'
}

class Dispatcher(Document):
#region class methods events
	def after_insert(self):
		if self.name:
			self.queue_no = self.name.split('-')[-1].lstrip('0')
			self.db_update()

	def validate(self):
		self.progress = self._calculate_progress()
		if self.status == "In Queue":
			self._update_status_if_all_rooms_finished()
		if self.status in ("Finished", "Rescheduled") and self._status_changed_to_final():
			self._update_patient_appointment_status()
	
	def before_insert(self):
		if frappe.db.exists(self.doctype,{
			'patient_appointment': self.patient_appointment,
			'date': self.date,
		}):
			frappe.throw(_("Patient already has an active Dispatcher entry for this date."))
#endregion
#region class methods helpers
	def _update_status_if_all_rooms_finished(self):
		if all(room.status in FINISHED_STATUSES for room in self.assignment_table):
			if self._check_if_any_rescheduled():
				self.status = 'Rescheduled'
			else:	
				self.status = 'Waiting to Finish'

	def _status_changed_to_final(self) -> bool:
		doc_before_save = self.get_doc_before_save()
		return bool(
			doc_before_save and 
			(doc_before_save.status != "Finished" or doc_before_save.status != "Rescheduled"))

	def _update_patient_appointment_status(self):
		if not self.patient_appointment:
			frappe.msgprint(_("No linked Patient Appointment found to update."))
			return
		try:
			if self._check_if_any_rescheduled():
				frappe.db.set_value('Patient Appointment', self.patient_appointment, 'status', 'Scheduled')
			else:
				status = frappe.db.get_value('Patient Appointment', self.patient_appointment, 'status')
				if status not in {"Closed", "Checked Out", "Ready to Check Out"}:
					frappe.db.set_value('Patient Appointment', self.patient_appointment, 'status', 'Ready to Check Out')
		except Exception as e:
			frappe.log_error(
				f"Failed to update Patient Appointment {self.patient_appointment}. Error: {e}",
				"Dispatcher Update Appointment")
			frappe.msgprint(_('Error updating linked Patient Appointment status.'))
	
	def _check_if_any_rescheduled(self) -> bool:
		room = any(room.status == 'Rescheduled' for room in self.assignment_table)
		exam = any(exam.status == 'Rescheduled' for exam in self.package)
		return room or exam
	
	def _calculate_progress(self) -> int:
		child_items = frappe.get_all(
			'MCU Appointment', filters={'parent': self.name}, fields=['status'])
		if not child_items:
			return 0
		return round(mean([100 if item.status == 'Finished' else 0 for item in child_items]))
#endregion

def convert_to_float(value):
	return float(str(value).replace(",", "."))

def is_within_range(value, min_value, max_value):
	return min_value < value < max_value

@frappe.whitelist()
def get_queued_branch(branch):
	return frappe.db.sql(f"""
		SELECT thsu.name, COALESCE(COUNT(tdr.healthcare_service_unit), 0) AS status_count, 
			tra.`user`, thsu.custom_default_doctype
		FROM `tabHealthcare Service Unit` thsu
		LEFT JOIN `tabDispatcher Room` tdr 
			ON thsu.name = tdr.healthcare_service_unit 
			AND tdr.status in ('Waiting to Enter the Room', 'Ongoing Examination')
			AND EXISTS (SELECT 1 FROM tabDispatcher td WHERE td.name = tdr.parent and td.`date` = CURDATE())
		LEFT JOIN `tabRoom Assignment` tra 
			ON thsu.name = tra.healthcare_service_unit 
			AND tra.`date` = CURDATE()
		WHERE thsu.custom_branch = %s
		AND thsu.is_group = 0 
		AND thsu.custom_default_doctype IS NOT NULL
		GROUP BY thsu.name
		ORDER BY custom_room""", (branch), as_dict=True)

@frappe.whitelist()
def is_meal(exam_id, doctype=None, docname=None):
	appt = frappe.get_doc('Patient Appointment', exam_id)
	if not appt.mcu:
		return False
	dispatcher_exists = frappe.db.exists('Dispatcher', 
		frappe.db.get_value('Dispatcher', {'patient_appointment': exam_id}, 'name'))
	if dispatcher_exists:
		if frappe.db.get_value('Dispatcher', {'patient_appointment': exam_id}, 'had_meal'):
			return False
	else:
		if frappe.db.exists(
			'MCU Queue Pooling', {'patient_appointment': exam_id, 'is_meal_time': 1}):
			return False

	check_list = (getattr(appt, "custom_mcu_exam_items", []) or []) + (getattr(appt, "custom_additional_mcu_items", []) or [])
	mcu_setting = frappe.get_doc("MCU Settings", "MCU Settings")
	radiology = [exam.exam_required for exam in mcu_setting.required_exam]
	lab_test = frappe.db.get_all(
		'Item', pluck='name', 
		filters=[["item_group", "descendants of (inclusive)", "Laboratory"],["custom_is_mcu_item", "=", 1]])
	valid_status = ['Finished', 'Refused', 'Rescheduled']
	lab_test_result = False
	radiology_items = []
	if docname and doctype: # for room 
		if doctype == 'Sample Collection':
			lab_test_result = True
			for item in check_list:
				if item.examination_item in radiology:
					radiology_items.append(item.status)
			if radiology_items:
				radiology_result = all(status in valid_status for status in radiology_items)
			else:
				radiology_result = False
		else:
			doc = frappe.get_doc(doctype, docname)
			current_item = False
			for item in check_list:
				if item.examination_item in lab_test and item.status in valid_status:
					lab_test_result = True
				if item.examination_item in radiology:
					if any(row.get("item") == item.examination_item for row in doc.examination_item):
						current_item = True
					else:
						radiology_items.append(item.status)
			if radiology_items:
				radiology_result = all(status in valid_status for status in radiology_items)
			else:
				radiology_result = True if current_item else False
		return lab_test_result and radiology_result
	else: # for dispatcher
		for item in check_list:
			if item.examination_item in lab_test and item.status in valid_status:
				lab_test_result = True
			if item.examination_item in radiology:
				radiology_items.append(item.status)
		if radiology_items:
			radiology_result = all(status in valid_status for status in radiology_items)
		else:
			radiology_result = False
		return lab_test_result and radiology_result

from kms.mcu_dispatcher import _get_related_service_units

@frappe.whitelist()
def finish_exam(hsu, status, doctype, docname):
	exists_to_retest = False
	source_doc = frappe.get_doc(doctype, docname)
	is_sc = doctype == 'Sample Collection'
	exam_id = source_doc.custom_appointment if is_sc else source_doc.appointment
	dispatcher_id = source_doc.custom_dispatcher if is_sc else source_doc.dispatcher
	queue_pooling_id = source_doc.custom_queue_pooling if is_sc else source_doc.queue_pooling
	child = source_doc.custom_sample_table if is_sc else source_doc.examination_item
	related_rooms = _get_related_service_units(hsu, exam_id)
	exists_to_retest = any(item.status == 'To Retest' for item in child)
	target = ''
	is_meal_time = is_meal(exam_id)
	room_count = 0
	final_count = 0
	final_status = ['Finished', 'Refused', 'Rescheduled', 'Partial Finished', 'Ineligible for Testing', 'Finished Collection']
	if dispatcher_id:
		if status == 'Removed':
			status = 'Wait for Room Assignment'
		doc = frappe.get_doc('Dispatcher', dispatcher_id)
		for room in doc.assignment_table:
			room_count += 1
			if room.status in final_status:
				final_count += 1
			if room.healthcare_service_unit in related_rooms:
				room.status = 'Additional or Retest Request' if exists_to_retest else status
		doc.status = 'Waiting to Finish' if room_count == final_count else 'In Queue'
		doc.room = ''
		if is_meal_time:
			doc.status = 'Meal Time'
			doc.had_meal = True
			doc.meal_time = now()
		doc.save(ignore_permissions=True)
	elif queue_pooling_id:
		item_status = ['Started', 'To Retest', 'To be Added']
		if not frappe.db.exists('MCU Appointment', filters = {'parent': exam_id, status: ['in', item_status]}):
			frappe.db.set_value('Patient Appointment', exam_id, 'status', 'Ready to Check Out')
		qps = frappe.get_all('MCU Queue Pooling', filters={'patient_appointment': exam_id}, pluck='name')
		meal_time = now()
		submit_time = now_datetime()
		for qp in qps:
			if is_meal_time:
				frappe.db.set_value(
					'MCU Queue Pooling', qp, {'is_meal_time': 1, 'meal_time': meal_time, 'had_meal': 0})
			delay_in_minutes = frappe.db.get_single_value('MCU Settings', 'queue_pooling_submit_delay')
			if delay_in_minutes:
				delay_time = submit_time + timedelta(minutes=delay_in_minutes)
				frappe.db.set_value('MCU Queue Pooling', qp, 'delay_time', delay_time)
			else:
				frappe.db.set_value('MCU Queue Pooling', qp, 'in_room', 0)
			#room_count += 1
			#if frappe.db.get_value('MCU Queue Pooling', qp, 'status') in final_status:
			#	final_count += 1
			if frappe.db.get_value('MCU Queue Pooling', qp, 'service_unit') in related_rooms:
				status_to_set = 'Additional or Retest Request' if exists_to_retest else status
				frappe.db.set_value('MCU Queue Pooling', qp, 'status', status_to_set)
		#if  final_count+1 >= room_count:
		#	frappe.db.set_value('Patient Appointment', exam_id, 'status', 'Ready to Check Out')
	if (status == 'Finished' or status == 'Partial Finished') and not exists_to_retest:
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

def create_result_doc(doc, target):
	not_created = True
	if target == 'Lab Test':
		not_created = False
		normal_toggle = 0
		new_doc = frappe.get_doc({
			'doctype': target,
			'company': doc.company,
			'custom_branch': doc.custom_branch,
			'patient': doc.patient,
			'patient_name': doc.patient_name,
			'patient_sex': doc.patient_sex,
			'patient_age': doc.patient_age,
			'custom_appointment': doc.custom_appointment,
			'custom_sample_collection': doc.name
		})
		for item in doc.custom_sample_table:
			if item.status == 'Finished':
				lab_test = frappe.db.sql("""
					SELECT tltt.name, tltt.lab_test_code FROM `tabLab Test Template` tltt, tabItem ti
					WHERE tltt.sample = %s AND ti.name = tltt.lab_test_code
					AND EXISTS (SELECT 1 FROM `tabLab Test Request` tltr
						WHERE tltr.item_code = tltt.item AND tltr.parent = %s
						AND tltr.parentfield = 'custom_examination_item'
						AND tltr.parenttype = 'Sample Collection')
					ORDER BY ti.custom_bundle_position""", (item.sample, doc.name), as_dict=True)
				for exam in lab_test:
					template_doc = frappe.get_doc('Lab Test Template', exam.name)
					non_selective = template_doc.get('normal_test_templates')
					selective = template_doc.get('custom_selective')
					if non_selective:
						match = re.compile(r'(\d+) Years?').match(doc.patient_age)
						age = int(match.group(1)) if match else None
						minmax = frappe.db.sql("""
							WITH ranked AS (
								SELECT parent, lab_test_event, lab_test_uom, custom_age,
									custom_sex, custom_min_value, custom_max_value, idx,
									ROW_NUMBER() OVER (PARTITION BY parent, lab_test_event ORDER BY custom_age DESC) as rn
								FROM `tabNormal Test Template`
								WHERE parent = %(test)s
									AND (%(sex)s IS NULL OR custom_sex = %(sex)s)
									AND custom_age <= %(age)s
							)
							SELECT lab_test_event, lab_test_uom, custom_min_value, custom_max_value
							FROM ranked
							WHERE rn = 1
							ORDER BY idx""", 
							{'age': age, 'test': exam.name, 'sex': doc.patient_sex}, as_dict=True)
						for mm in minmax:
							new_doc.append('normal_test_items', {
								'lab_test_name': exam.name, 
								'custom_min_value': mm.custom_min_value, 
								'custom_max_value': mm.custom_max_value, 
								'lab_test_event': mm.lab_test_event, 
								'lab_test_uom': mm.lab_test_uom,
								'custom_sample': item.sample,
								'custom_item': exam.lab_test_code
							})
							normal_toggle = 1
					if selective:
						for sel in template_doc.custom_selective:
							new_doc.append('custom_selective_test_result', {
								'item': template_doc.item,
								'event': sel.event,
								'result_set': sel.result_select, 
								'result': sel.result_select.splitlines()[0],
								'sample': item.sample,
          			'normal_value': sel.normal_value,
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
		if target == 'Nurse Result':
			count_nurse_result = frappe.db.sql("""
				SELECT count(*) count 
				FROM `tabNurse Examination Template` tnet
				WHERE EXISTS (SELECT * FROM `tabNurse Examination Request` tner 
				WHERE tner.parent = %s AND tnet.name = tner.template)
				AND tnet.result_in_exam = 0""", (doc.name), as_dict = True)
			if count_nurse_result[0].count == 0:
				return
		for item in doc.examination_item:
			if item.status == 'Finished':
				item_status = 'Started'
				if target == 'Nurse Result' and frappe.db.get_value(
					'Nurse Examination Template', item.template, 'result_in_exam'):
					item_status = 'Finished'
				new_doc.append('examination_item', {
					'status': item_status,
					'template': item.template,
					'status_time': item.status_time if item.status == 'Finished' else None
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
										'mandatory_value': result.mandatory_value,
										'result_check': result.normal_value,
										'item_code': template_doc.item_code,
										'result_options': result.result_select
									})
							else:
								new_doc.append('result', {
									'result_line': result.result_text,
									'normal_value': result.normal_value,
									'mandatory_value': result.mandatory_value,
									'result_check': result.normal_value,
									'item_code': template_doc.item_code,
									'result_options': result.result_select
								})
					case 'Nurse Result':
						not_created = False
						template = 'Nurse Examination Template'
						template_doc = frappe.get_doc(template, item.template)
						if getattr(template_doc, 'result_in_exam', None):
							for result in doc.result:
								if template_doc.item_code == result.item_code:
									new_doc.append('result', {
										'item_code': result.item_code,
										'item_name': result.item_name,
										'result_line': result.result_line,
										'result_check': result.result_check,
										'result_text': result.result_text,
										'normal_value': result.normal_value,
										'result_options': result.result_options,
										'mandatory_value': result.mandatory_value,
										'is_finished': True
									})
							for normal_item in doc.non_selective_result:
								if template_doc.item_code == normal_item.item_code:
									new_doc.append('non_selective_result', {
										'item_code': normal_item.item_code,
										'test_name': normal_item.test_name,
										'test_event': normal_item.test_event,
										'result_value': normal_item.result_value,
										'test_uom': normal_item.test_uom,
										'min_value': normal_item.min_value,
										'max_value': normal_item.max_value,
										'is_finished': True
									})
						else:
							for result in template_doc.items:
								new_doc.append('result', {
									'result_line': result.result_text,
									'normal_value': result.normal_value,
									'mandatory_value': result.mandatory_value,
									'result_check': result.normal_value,
									'item_code': template_doc.item_code,
									'result_options': result.result_select,
									'is_finished': False
								})
							for normal_item in template_doc.normal_items:
								new_doc.append('non_selective_result', {
									'item_code': template_doc.item_code,
									'test_name': normal_item.heading_text,
									'test_event': normal_item.lab_test_event,
									'test_uom': normal_item.lab_test_uom,
									'min_value': normal_item.min_value,
									'max_value': normal_item.max_value,
									'is_finished': False
								})
					case _:
						frappe.throw(f"Unhandled Template for {target} DocType.")
	if not not_created:
		new_doc.insert(ignore_permissions=True)
	return new_doc.name
