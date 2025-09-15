# Copyright (c) 2023, GIS and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import now
from frappe.model.document import Document
from kms.utils import set_pa_notes

class Radiology(Document):
	def on_submit(self):
		exam_result = frappe.db.exists('Radiology Result', {'exam': self.name}, 'name')
		self.db_set('submitted_date', frappe.utils.now_datetime())
		if exam_result:
			self.db_set('exam_result', exam_result)
		set_pa_notes(self.appointment, self.exam_notes)

	def before_insert(self):
		pa_doc = frappe.get_doc('Patient Appointment', self.appointment)
		self.exam_notes = pa_doc.notes

	def on_update(self):
		old = self.get_doc_before_save()
		if self.status == 'Checked In' and self.docstatus == 0 and old.status == 'Started':
			self.db_set('checked_in_time', frappe.utils.now_datetime())

@frappe.whitelist()
def create_exam(name):
	result = []
	enc = frappe.get_doc('Patient Encounter', name)
	sql = """SELECT DISTINCT service_unit, parent
    FROM `tabItem Group Service Unit` tigsu 
    WHERE EXISTS (
      SELECT 1 
      FROM `tabRadiology Result Template` trrt 
      WHERE trrt.item_code = tigsu.parent 
      AND EXISTS (
        SELECT 1 
        FROM `tabRadiology Request` trr 
        WHERE trr.parent = %s
        AND trr.template = trrt.name
				AND trr.radiology IS NULL
      )
    )
    AND branch = %s"""
	rooms = frappe.db.sql(sql, (enc.name, enc.custom_branch), as_dict = True)
	rooms_map = {}
	for row in rooms:
		room = row['service_unit']
		parent = row['parent']
		rooms_map.setdefault(room,[]).append(parent)
	for room, parents in rooms_map.items():
		existing_doc = frappe.db.get_all('Radiology',
			filters={'appointment': enc.appointment, 'docstatus': 0, 'service_unit': room},
			pluck='name')
		if existing_doc:
			doc = frappe.get_doc('Radiology', existing_doc[0])
		else:
			doc = frappe.get_doc({
				'doctype': 'Radiology',
				'patient': enc.patient,
				'patient_name': enc.patient_name,
				'patient_sex': enc.patient_sex,
				'patient_age': enc.patient_age,
				'date_of_birth': enc.custom_date_of_birth,
				'patient_company': enc.custom_patient_company,
				'appointment': enc.appointment,
				'patient_encounter': name,
				'company': enc.company,
				'branch': enc.custom_branch,
				'service_unit': room,
				'examination_item': []
			})
		for parent in parents:
			template = frappe.db.get_value('Radiology Result Template', {'item_code': parent}, 'name')
			doc.append('examination_item', {'template': template, 'status': 'Started', 'status_time': now()})
		doc.save(ignore_permissions=True)
		result.append(doc.name)
		update_radiology_requests(enc.name, doc.name, doc.examination_item)
		result_text = ', '.join(result)
	return f'Radiology {result_text} ordered.'

def update_radiology_requests(encounter_name, radiology_name, examination_items):
	# Update Radiology Request records for matching templates
	for item in examination_items:
		template_name = item.get('template')
		# Find the Radiology Request linked to the Patient Encounter and template
		radiology_request = frappe.get_all(
			'Radiology Request',
			filters={'parent': encounter_name, 'template': template_name},
			fields=['name']
		)
		for request in radiology_request:
			frappe.db.set_value('Radiology Request', request['name'], 'radiology', radiology_name)
			frappe.db.set_value('Radiology Request', request['name'], 'status', 'Ordered')
			frappe.db.set_value('Radiology Request', request['name'], 'status_time', now())
