# Copyright (c) 2024, GIS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class DoctorExamination(Document):
	def before_insert(self):
		if not self.is_dental_record_inserted:
			item_name = frappe.db.get_single_value ('MCU Settings', 'dental_examination_name')
			for exam_item in self.examination_item:
				if exam_item.template == item_name:
					prepared_data = [
						{'teeth_type': 'Permanent Teeth', 'location': 'ul', 'position': 18},
						{'teeth_type': 'Permanent Teeth', 'location': 'ul', 'position': 17},
						{'teeth_type': 'Permanent Teeth', 'location': 'ul', 'position': 16},
						{'teeth_type': 'Permanent Teeth', 'location': 'ul', 'position': 15},
						{'teeth_type': 'Permanent Teeth', 'location': 'ul', 'position': 14},
						{'teeth_type': 'Permanent Teeth', 'location': 'ul', 'position': 13},
						{'teeth_type': 'Permanent Teeth', 'location': 'ul', 'position': 12},
						{'teeth_type': 'Permanent Teeth', 'location': 'ul', 'position': 11},
						{'teeth_type': 'Permanent Teeth', 'position': 21, 'location': 'ur'},
						{'teeth_type': 'Permanent Teeth', 'position': 22, 'location': 'ur'},
						{'teeth_type': 'Permanent Teeth', 'position': 23, 'location': 'ur'},
						{'teeth_type': 'Permanent Teeth', 'position': 24, 'location': 'ur'},
						{'teeth_type': 'Permanent Teeth', 'position': 25, 'location': 'ur'},
						{'teeth_type': 'Permanent Teeth', 'position': 26, 'location': 'ur'},
						{'teeth_type': 'Permanent Teeth', 'position': 27, 'location': 'ur'},
						{'teeth_type': 'Permanent Teeth', 'position': 28, 'location': 'ur'},
						{'teeth_type': 'Permanent Teeth', 'position': 48, 'location': 'll'},
						{'teeth_type': 'Permanent Teeth', 'position': 47, 'location': 'll'},
						{'teeth_type': 'Permanent Teeth', 'position': 46, 'location': 'll'},
						{'teeth_type': 'Permanent Teeth', 'position': 45, 'location': 'll'},
						{'teeth_type': 'Permanent Teeth', 'position': 44, 'location': 'll'},
						{'teeth_type': 'Permanent Teeth', 'position': 43, 'location': 'll'},
						{'teeth_type': 'Permanent Teeth', 'position': 42, 'location': 'll'},
						{'teeth_type': 'Permanent Teeth', 'position': 41, 'location': 'll'},
						{'teeth_type': 'Permanent Teeth', 'position': 31, 'location': 'lr'},
						{'teeth_type': 'Permanent Teeth', 'position': 32, 'location': 'lr'},
						{'teeth_type': 'Permanent Teeth', 'position': 33, 'location': 'lr'},
						{'teeth_type': 'Permanent Teeth', 'position': 34, 'location': 'lr'},
						{'teeth_type': 'Permanent Teeth', 'position': 35, 'location': 'lr'},
						{'teeth_type': 'Permanent Teeth', 'position': 36, 'location': 'lr'},
						{'teeth_type': 'Permanent Teeth', 'position': 37, 'location': 'lr'},
						{'teeth_type': 'Permanent Teeth', 'position': 38, 'location': 'lr'},
						{'teeth_type': 'Primary Teeth', 'position': 55, 'location': 'ul'},
						{'teeth_type': 'Primary Teeth', 'position': 54, 'location': 'ul'},
						{'teeth_type': 'Primary Teeth', 'position': 53, 'location': 'ul'},
						{'teeth_type': 'Primary Teeth', 'position': 52, 'location': 'ul'},
						{'teeth_type': 'Primary Teeth', 'position': 51, 'location': 'ul'},
						{'teeth_type': 'Primary Teeth', 'position': 61, 'location': 'ur'},
						{'teeth_type': 'Primary Teeth', 'position': 62, 'location': 'ur'},
						{'teeth_type': 'Primary Teeth', 'position': 63, 'location': 'ur'},
						{'teeth_type': 'Primary Teeth', 'position': 64, 'location': 'ur'},
						{'teeth_type': 'Primary Teeth', 'position': 65, 'location': 'ur'},
						{'teeth_type': 'Primary Teeth', 'position': 85, 'location': 'll'},
						{'teeth_type': 'Primary Teeth', 'position': 84, 'location': 'll'},
						{'teeth_type': 'Primary Teeth', 'position': 83, 'location': 'll'},
						{'teeth_type': 'Primary Teeth', 'position': 82, 'location': 'll'},
						{'teeth_type': 'Primary Teeth', 'position': 81, 'location': 'll'},
						{'teeth_type': 'Primary Teeth', 'position': 71, 'location': 'lr'},
						{'teeth_type': 'Primary Teeth', 'position': 72, 'location': 'lr'},
						{'teeth_type': 'Primary Teeth', 'position': 73, 'location': 'lr'},
						{'teeth_type': 'Primary Teeth', 'position': 74, 'location': 'lr'},
						{'teeth_type': 'Primary Teeth', 'position': 75, 'location': 'lr'},
					]
					for data in prepared_data:
						self.append('dental_detail', {
							'teeth_type': data['teeth_type'],
							'position': data['position'],
							'location': data['location']
						})
		if self.dispatcher:
			disp_doc = frappe.get_doc('Dispatcher', self.dispatcher)
			for package in disp_doc.package:
				is_internal = frappe.db.get_value('Questionnaire Template', package.item_name, 'internal_questionnaire')
				template = frappe.db.get_value('Questionnaire Template', package.item_name, 'template_name')
				if is_internal:
					status, name = frappe.db.get_value(
						'Questionnaire', 
						{'patient_appointment': self.appointment, 'template': template},
						['status', 'name'])
					if status and name:
						self.append('questionnaire', {
							'template': template,
							'is_completed': True if status == 'Completed' else False,
							'questionnaire': name
						})
					else:
						self.append('questionnaire', {
							'template': template,
							'is_completed': False
						})

	def on_submit(self):
		exam_result = frappe.db.exists('Doctor Examination Result', {'exam': self.name}, 'name')
		self.db_set('submitted_date', frappe.utils.now_datetime())
		if exam_result:
			self.db_set('exam_result', exam_result)
	def on_update(self):
		old = self.get_doc_before_save()
		if self.status == 'Checked In' and self.docstatus == 0 and old.status == 'Started':
			self.db_set('checked_in_time', frappe.utils.now_datetime())