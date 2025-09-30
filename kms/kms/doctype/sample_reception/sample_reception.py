# Copyright (c) 2024, GIS and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import now
from frappe.model.document import Document

class SampleReception(Document):
	def on_submit(self):
		sc = frappe.get_doc('Sample Collection', self.sample_collection)
		if not sc:
			frappe.throw(f'Sample Collection {self.sample_collection} not found.')
		if sc.docstatus != 1:
			frappe.throw(f'Sample Collection {sc.name} must be Submitted.')
		else:
			self.collected_by = frappe.session.user
			self.collection_time = now()
			update_sample_collection(sc, self.lab_test_sample)
			if sc.custom_lab_test:
				update_lab_test(sc.custom_lab_test, self.lab_test_sample, self.name)
			if sc.custom_dispatcher:
				update_dispatcher_status(
					self.name, 
					sc.custom_dispatcher, 
					self.healthcare_service_unit)
			elif sc.custom_queue_pooling:
				update_queue_pooling_status(
					self.name, 
					self.appointment, 
					self.healthcare_service_unit)
			elif sc.custom_encounter:
				pass
			else:
				update_patient_appointment_status(self.appointment)


def update_sample_collection(doc, sample):
	for cs in doc.custom_sample_table:
		if cs.sample == sample:
			cs.reception_status = 1
	doc.save(ignore_permissions=True)
	
def update_lab_test(lab_test, sample, sr_name):
	lab_test = frappe.get_doc('Lab Test', lab_test)
	for custom_selective_test_result in lab_test.custom_selective_test_result:
		if sample == custom_selective_test_result.sample:
			custom_selective_test_result.sample_reception = sr_name
	for normal_test_items in lab_test.normal_test_items:
		if sample == normal_test_items.custom_sample:
			normal_test_items.custom_sample_reception = sr_name				
	lab_test.save(ignore_permissions=True)

def update_dispatcher_status(sr_no, disp_no, sr_room):
	count1 = count_samples(sr_no)
	if count1:
		count2 = count_received_samples(sr_no)
		if count2:
			if count1[0][0] == count2[0][0]:
				disp_doc = frappe.get_doc('Dispatcher', disp_no)
				for room in disp_doc.assignment_table:
					if room.healthcare_service_unit == sr_room:
						room.status = 'Finished Collection'
				disp_doc.save(ignore_permissions=True)

def update_queue_pooling_status(sr_no, exam_id, sr_room):
	count1 = count_samples(sr_no)
	if count1:
		count2 = count_received_samples(sr_no)
		if count2:
			if count1[0][0] == count2[0][0]:
				frappe.db.set_value(
					'MCU Queue Pooling', {'patient_appointment': exam_id, 'service_unit': sr_room}, 
					'status', 'Finished Collection')
				if check_final_room(exam_id):
					frappe.db.set_value('Patient Appointment', exam_id, 'status', 'Ready to Check Out')

def update_patient_appointment_status(exam_id):
	frappe.db.set_value('Patient Appointment', exam_id, 'status', 'Ready to Check Out')

def count_samples(sr_no):
	sql = """
		SELECT COUNT(*) FROM `tabSample Collection Bulk` tscb 
		WHERE EXISTS (
			SELECT 1 FROM `tabSample Collection` tsc 
			WHERE EXISTS (
				SELECT 1 FROM `tabSample Reception` tsr 
				WHERE tsr.appointment = tsc.custom_appointment
				AND tsr.name = %s
				)
			AND tsc.docstatus = 1
			AND tscb.parent = tsc.name
		)"""
	return frappe.db.sql(sql, (sr_no))

def count_received_samples(sr_no):
	sql = """
		SELECT COUNT(*) FROM `tabSample Collection Bulk` tscb 
		WHERE EXISTS (
			SELECT 1 FROM `tabSample Collection` tsc 
			WHERE EXISTS (
				SELECT 1 FROM `tabSample Reception` tsr 
				WHERE tsr.appointment = tsc.custom_appointment
				AND tsr.name = %s
				)
			AND tsc.docstatus = 1
			AND tscb.parent = tsc.name
		) AND tscb.reception_status = 1"""
	return frappe.db.sql(sql, (sr_no))

def check_final_room(exam_id):
	mqp = frappe.db.get_all('MCU Queue Pooling', filters={'patient_appointment': exam_id}, pluck='status')
	total_count = len(mqp)
	final_statuses = ['Finished', 'Refused', 'Rescheduled', 'Partial Finished', 'Ineligible for Testing', 'Finished Collection']
	final_count = sum(1 for status in mqp if status in final_statuses)
	return total_count == final_count