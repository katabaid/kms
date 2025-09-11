# Copyright (c) 2024, GIS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from statistics import mean

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
