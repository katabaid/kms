# Copyright (c) 2024, GIS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class TemporaryRegistration(Document):
	def before_insert(self):
		for row in self.detail:
			if row.template and row.question:
				new_question = frappe.get_all('Questionnaire Template Detail', {'parent': row.template, 'id': row.question}, pluck='label')[0]
				row.question = new_question