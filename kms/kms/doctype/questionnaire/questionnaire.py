# Copyright (c) 2024, GIS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class Questionnaire(Document):
	def after_insert(self):
		if self.patient_appointment:
			self._update_patient_appointment()
			self._update_examinations('Doctor Examination', 'Completed')
			self._update_examinations('Nurse Examination', 'Completed')

	def before_insert(self):
		self.status = 'Completed' if self.patient_appointment else 'Draft'
		self._update_question_labels()

	def before_save(self):
		if not self.is_new():
			if self.has_value_changed('status'):
				self._update_examinations('Doctor Examination', self.status)
				self._update_examinations('Nurse Examination', self.status)
				if self.status == 'Rejected':
					self._update_dispatcher()

	def _update_patient_appointment(self):
		"""Update the Patient Appointment with questionnaire details."""
		pa_doc = frappe.get_doc("Patient Appointment", self.patient_appointment)
		for detail in self.detail:
			detail_dict = self._get_clean_detail_dict(detail)
			pa_doc.append('custom_questionnaire_detail', detail_dict)
		for pa_q in pa_doc.custom_completed_questionnaire:
			if pa_q.template == self.template:
				pa_q.questionnaire = self.name
				pa_q.status = 'Completed'
		try:
			pa_doc.save(ignore_permissions=True)
		except Exception as e:
			frappe.msgprint(f"Error saving Patient Appointment: {e}")

	def _get_clean_detail_dict(self, detail):
		"""Return a dictionary of detail fields excluding metadata."""
		exclude_fields = {'name', 'parent', 'parenttype', 'parentfield', 'idx'}
		return {k: v for k, v in detail.as_dict().items() if k not in exclude_fields}

	def _update_examinations(self, examination_type, status):
		"""Update the status of the questionnaire in the given examination type."""
		filters = {
			'appointment': self.patient_appointment,
			'docstatus': ['in', ['0', '1']]
		}
		examination_names = frappe.get_all(examination_type, filters=filters, pluck='name')
		for exam_name in examination_names:
			exam_doc = frappe.get_doc(examination_type, exam_name)
			if exam_doc.questionnaire:
				self._update_questionnaire_status(exam_doc, status)

	def _update_questionnaire_status(self, exam_doc, status):
		"""Update the status of the questionnaire in the examination document."""
		for row in exam_doc.questionnaire:
			if row.template == self.template:
				row.status = status
				row.questionnaire = self.name
				exam_doc.save(ignore_permissions=True)
				break

	def _update_question_labels(self):
		"""Update the question labels in the questionnaire details."""
		for row in self.detail:
			if row.template and row.question:
				row.question = self._get_question_label(row.template, row.question)

	def _get_question_label(self, template, question):
		"""Fetch the label for a given question from the template."""
		labels = frappe.get_all(
			'Questionnaire Template Detail', 
			filters={'parent': template, 'name': question}, 
			pluck='label')
		return labels[0] if labels else question
	
	def _update_dispatcher(self):
		branch = frappe.db.get_value('Patient Appointment', self.patient_appointment, 'custom_branch')
		item = frappe.db.get_value('Questionnaire Template', self.template, 'item_code')
		item_doc = frappe.get_doc('Item', item)
		service_unit = []
		for room in item_doc.custom_room:
			if room.branch == branch:
				service_unit.append(room.service_unit)
		if service_unit:
			d = frappe.db.get_all('Dispatcher', filters={'patient_appointment': self.patient_appointment}, pluck='name')
			if d:
				disp = frappe.get_doc('Dispatcher', d[0])
				for su in disp.assignment_table:
					if(su.healthcare_service_unit in service_unit):
						if(su.status in ['Wait for Room Assignment', 'Rescheduled']):
							su.status = 'Ineligible for Testing'
				disp.save(ignore_permissions=True)
