# Copyright (c) 2024, GIS and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import now
from frappe.model.document import Document

class SampleReception(Document):
	def on_submit(self):
		collection_doc = frappe.get_doc('Sample Collection', self.sample_collection)
		if collection_doc.docstatus != 1:
			frappe.throw(f'Sample Collection {collection_doc.name} must be Submitted.')
		else:
			self.collected_by = frappe.session.user
			self.collection_time = now()
			update_sample_collection(collection_doc, self.lab_test_sample)
			if collection_doc.custom_lab_test:
				update_lab_test(collection_doc.custom_lab_test, self.lab_test_sample, self.name)
			if collection_doc.custom_dispatcher:
				update_dispatcher_status(
					self.name, 
					collection_doc.custom_dispatcher, 
					self.healthcare_service_unit)

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
	count1 = count_samples(sr_no)[0][0]
	if count1 > 0:
		count2 = count_received_samples(sr_no)[0][0]
		if count1 == count2:
			disp_doc = frappe.get_doc('Dispatcher', disp_no)
			for room in disp_doc.assignment_table:
				if room.healthcare_service_unit == sr_room:
					room.status = 'Finished Collection'
			disp_doc.save(ignore_permissions=True)

def count_samples(sr_no):
	sql = f"""
		SELECT COUNT(*) FROM `tabSample Collection Bulk` tscb 
		WHERE EXISTS (
			SELECT 1 FROM `tabSample Collection` tsc 
			WHERE EXISTS (
				SELECT 1 FROM `tabSample Reception` tsr 
				WHERE tsr.appointment = tsc.custom_appointment
				AND tsr.name = '{sr_no}'
				)
			AND tsc.docstatus = 1
			AND tscb.parent = tsc.name
			AND tsc.custom_dispatcher is not NULL 
		)"""
	return frappe.db.sql(sql)

def count_received_samples(sr_no):
	sql = f"""
		SELECT COUNT(*) FROM `tabSample Collection Bulk` tscb 
		WHERE EXISTS (
			SELECT 1 FROM `tabSample Collection` tsc 
			WHERE EXISTS (
				SELECT 1 FROM `tabSample Reception` tsr 
				WHERE tsr.appointment = tsc.custom_appointment
				AND tsr.name = '{sr_no}'
				)
			AND tsc.docstatus = 1
			AND tscb.parent = tsc.name
			AND tsc.custom_dispatcher is not NULL 
		) AND tscb.reception_status = 1"""
	return frappe.db.sql(sql)