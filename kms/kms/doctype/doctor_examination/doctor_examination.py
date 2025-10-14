# Copyright (c) 2024, GIS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from kms.utils import set_pa_notes
from kms.api.healthcare import finish_exam

class DoctorExamination(Document):
	def before_insert(self):
		pa_doc = frappe.get_doc('Patient Appointment', self.appointment)
		self.exam_note = pa_doc.notes
		if not self.is_dental_record_inserted:
			item_name = frappe.db.get_single_value ('MCU Settings', 'dental_examination_name')
			if any(exam_item.template == item_name for exam_item in self.examination_item):
				teeth_map = [
					{"type": "Permanent Teeth", "loc": "ul", "range": range(18, 10, -1)},
					{"type": "Permanent Teeth", "loc": "ur", "range": range(21, 29)},
					{"type": "Permanent Teeth", "loc": "ll", "range": range(48, 40, -1)},
					{"type": "Permanent Teeth", "loc": "lr", "range": range(31, 39)},
					{"type": "Primary Teeth", "loc": "ul", "range": range(55, 50, -1)},
					{"type": "Primary Teeth", "loc": "ur", "range": range(61, 66)},
					{"type": "Primary Teeth", "loc": "ll", "range": range(85, 80, -1)},
					{"type": "Primary Teeth", "loc": "lr", "range": range(71, 76)}
				]
				for section in teeth_map:				
					for pos in section['range']:
						self.append('dental_detail', {
							'teeth_type': section['type'],
							'position': pos,
							'location': section['loc']
						})
		valid_checker = [
			frappe.db.get_single_value ('MCU Settings', 'physical_examination'), 
			frappe.db.get_single_value ('MCU Settings', 'cardiologist')]
		if any(item.item in valid_checker for item in self.examination_item):
			all_packages = pa_doc.custom_mcu_exam_items + pa_doc.custom_additional_mcu_items
			for package in all_packages:
				treadmill = frappe.db.get_single_value ('MCU Settings', 'treadmill')
				if treadmill:
					if package.examination_item == 'CARD-00002':
						setup_questionnaire_table(self, package)
		remark = []
		for item in self.examination_item:
			rt = frappe.db.get_value('Doctor Examination Template', item.template, 'remark_template')
			if rt:
				remark.append(rt)
		self.remark = '\n'.join(remark)

	def on_submit(self):
		finish_exam(self.service_unit, self.status, self.doctype, self.name)
		exam_result = frappe.db.exists('Doctor Examination Result', {'exam': self.name}, 'name')
		self.db_set('submitted_date', frappe.utils.now_datetime())
		if exam_result:
			self.db_set('exam_result', exam_result)
	
	def on_update(self):
		old = self.get_doc_before_save()
		if self.status == 'Checked In' and self.docstatus == 0 and old.status == 'Started':
			self.db_set('checked_in_time', frappe.utils.now_datetime())
	
	def on_update_after_submit(self):
		set_pa_notes(self.appointment, self.exam_note)
		old_doc = self.get_doc_before_save()
		if self.grade != old_doc.grade:
			if hasattr(self, 'appointment') and self.appointment:
				doctor_results = frappe.get_all(
					'Doctor Result',
					filters={"appointment": self.appointment, "docstatus": ["!=", 2]},
					fields=["name", "docstatus"]
				)
				if doctor_results:
					if doctor_results[0].docstatus==1:
						frappe.throw(f'Doctor Result {doctor_results[0].name} is already submitted.')
					elif doctor_results[0].docstatus==0:
						dental_item = frappe.db.get_single_value('MCU Settings', 'dental_examination')
						doctor_result = frappe.get_doc("Doctor Result", doctor_results[0].name)
						for row in doctor_result.doctor_grade:
							if row.hidden_item == dental_item:
								row.grade = self.grade
								doctor_result.save(ignore_permissions=True)
								frappe.msgprint(f"Updated dental grade in Doctor Result {doctor_result.name}")
								break

def setup_questionnaire_table(self, item):
	is_internal = frappe.db.get_value('Questionnaire Template', item.item_name, 'internal_questionnaire')
	template = frappe.db.get_value('Questionnaire Template', item.item_name, 'template_name')
	if is_internal:
		status = frappe.db.get_value(
			'Questionnaire', 
			{'patient_appointment': self.appointment, 'template': template},
			'status')
		name = frappe.db.get_value(
			'Questionnaire', 
			{'patient_appointment': self.appointment, 'template': template},
			'name')
		if status and name:
			self.append('questionnaire', {
				'template': template,
				'status': status,
				'questionnaire': name
			})
		else:
			self.append('questionnaire', {
				'template': template,
				'status': 'Started'
			})
