# Copyright (c) 2023, GIS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate, now

class LabTestBatch(Document):
	def after_insert(self):
		template = frappe.get_doc("Lab Test Template", self.test_template)
		self.status = "Draft"
		self.submitted_date = ""
		self.lab_test_name = template.lab_test_name
		self.result_date = now()
		self.department = template.department
		self.lab_test_group = template.lab_test_group
		if template.custom_allow_stock_consumption:
			self.allow_stock_consumption = template.custom_allow_stock_consumption
			if not self.items:
				for item in template.custom_items:
					items = self.append("items")
					items.item_code = item.item_code
					items.qty = item.qty
					items.uom = item.uom
					items.stock_uom = item.stock_uom
					items.batch_no = item.batch_no
		self.save()

	def on_cancel(self):
		self.db_set("status", "Cancelled")
		self.reload()

	def on_submit(self):
		self.db_set("submitted_date", now())
		self.db_set("status", "Completed")
		"""create lab test per sample"""
		samples = frappe.db.get_list("Sample Collection", filters={"custom_lab_test_batch": self.name}, fields=["name", "patient", "patient_sex"])

		for sample in samples:
			doc = frappe.new_doc("Lab Test")
			doc.template = self.test_template
			doc.company = self.company
			doc.custom_lab_test_batch = self.name
			doc.custom_sample_collection = sample.name
			doc.patient = sample.patient
			doc.service_unit = self.service_unit
			doc.patient_sex = sample.patient_sex
			
			doc.insert()

	def before_submit(self):
		sample_num = frappe.db.count("Sample Collection", {'custom_lab_test_batch': self.name})
		if sample_num < 1:
			frappe.throw(
				title="Submit Requirement",
				msg="Please select and link Sample Collection to this batch first."
			)

	@frappe.whitelist()
	def set_lab_test_run_on_samples(self, samples):
		if samples:
			for docname in samples:
				frappe.db.set_value("Sample Collection", docname, 'custom_lab_test_batch', self.name)