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
