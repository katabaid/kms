# Copyright (c) 2024, GIS and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import now
from frappe.model.document import Document

class SampleReception(Document):
	def on_submit(self):
		self.collected_by = frappe.session.user
		self.collection_time = now()
		for detail in self.sample_reception_detail:
			scb_doc = frappe.db.get_all('Sample Collection Bulk', filters={'parent': detail.sample_collection, 'sample': self.lab_test_sample}, pluck='name')
			frappe.db.set_value('Sample Collection Bulk', scb_doc[0], 'sample_reception', self.name)
			lab = frappe.db.get_value('Sample Collection', scb_doc[0], 'custom_lab_test')
			ntr_doc = frappe.db.get_all('Normal Test Result', filters={'parent': lab, 'custom_sample': self.lab_test_sample}, pluck='name')
			str_doc = frappe.db.get_all('Selective Test Template', filters={'parent': lab, 'sample': self.lab_test_sample}, pluck='name')
			for ntr in ntr_doc:
				frappe.db.set_value('Normal Test Result', ntr, 'custom_sample_reception', self.name)
			for str in str_doc:
				frappe.db.set_value('Selective Test Template', str, 'sample_reception', self.name)
	def on_cancel(self):
		for detail in self.sample_reception_detail:
			scb_doc = frappe.db.get_all('Sample Collection Bulk', filters={'parent': detail.sample_collection, 'sample': self.lab_test_sample}, pluck='name')
			frappe.db.set_value('Sample Collection Bulk', scb_doc[0], 'sample_reception', '')
			lab = frappe.db.get_value('Sample Collection', scb_doc[0], 'custom_lab_test')
			ntr_doc = frappe.db.get_all('Normal Test Result', filters={'parent': lab, 'custom_sample': self.lab_test_sample}, pluck='name')
			str_doc = frappe.db.get_all('Selective Test Template', filters={'parent': lab, 'sample': self.lab_test_sample}, pluck='name')
			for ntr in ntr_doc:
				frappe.db.set_value('Normal Test Result', ntr, 'custom_sample_reception', '')
			for str in str_doc:
				frappe.db.set_value('Selective Test Template', str, 'sample_reception', '')
