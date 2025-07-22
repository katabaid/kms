# Copyright (c) 2025, GIS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class MCUQueuePooling(Document):
	def before_insert(self):
		formatted_date = frappe.utils.getdate(self.date).strftime('%y%m%d')
		self.title = f'{self.patient_appointment}-{formatted_date}-{self.service_unit}'
		self.current_tier = 1

	def before_save(self):
		finished = ['Refused', 'Finished', 'Rescheduled', 'Partial Finished', 'Finished Collection', 
			'Ineligible for Testing']
		if self.is_new() and self.current_tier == 3:
			return
		current_tier = frappe.db.exists('MCU Queue Pooling', 
			{'patient_appointment': self.patient_appointment, 
				'tier': self.current_tier, 
				'status': ['in', finished]}) or 1
		if not current_tier:
			mqps = frappe.db.get_all('MCU Queue Pooling', 
				filters={'patient_appointment': self.patient_appointment, 'name': ['!=', self.name]})
			for mqp in mqps:
				frappe.db.set_value('MCU Queue Pooling', mqp, 'current_tier', int(current_tier) + 1)
			self.current_tier = int(current_tier) + 1
