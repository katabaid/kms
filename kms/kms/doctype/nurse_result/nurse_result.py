# Copyright (c) 2024, GIS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class NurseResult(Document):
	def before_submit (self):
		for non_selective_result in self.non_selective_result:
			if not non_selective_result.result_value:
				frappe.throw (f"""Result Value {non_selective_result.test_name} {non_selective_result.test_event} is mandatory before submitting the document.""")
		for examination_item in self.examination_item:
			if examination_item.status == 'Started':
				examination_item.status = 'Finished'
