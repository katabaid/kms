# Copyright (c) 2023, GIS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class Radiology(Document):
	def on_submit(self):
		exam_result = frappe.db.exists('Radiology Result', {'exam': self.name}, 'name')
		self.db_set('submitted_date', frappe.utils.now_datetime())
		if exam_result:
			self.db_set('exam_result', exam_result)
	def on_update(self):
		old = self.get_doc_before_save()
		if self.status == 'Checked In' and self.docstatus == 0 and old.status == 'Started':
			self.db_set('checked_in_time', frappe.utils.now_datetime())
