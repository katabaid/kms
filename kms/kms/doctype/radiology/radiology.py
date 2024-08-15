# Copyright (c) 2023, GIS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class Radiology(Document):
	def on_submit(self):
		exam_result = frappe.db.exists('Radiology Result', {'exam': self.name}, 'name')
		if exam_result:
			self.db_set('exam_result', exam_result)
