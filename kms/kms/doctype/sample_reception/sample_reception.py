# Copyright (c) 2024, GIS and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import now
from frappe.model.document import Document

class SampleReception(Document):
	def on_submit(self):
		self.collected_by = frappe.session.user
		self.collection_time = now()
		lab_test_doc = frappe.db.get_value('Sample Collection', self.sample_collection, 'custom_lab_test')
		if lab_test_doc:
			lab_test = frappe.get_doc('Lab Test', lab_test_doc)
			for custom_selective_test_result in lab_test.custom_selective_test_result:
				sample = frappe.db.get_value('Lab Test Template', custom_selective_test_result.event, 'sample')
				if sample and self.lab_test_sample == sample:
					custom_selective_test_result.sample_reception = self.name
			lab_test.save(ignore_permissions=True)