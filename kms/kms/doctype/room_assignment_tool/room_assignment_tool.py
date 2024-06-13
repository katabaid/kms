# Copyright (c) 2024, GIS and contributors
# For license information, please see license.txt

import frappe, json
from frappe.model.document import Document
from frappe.utils import today

class RoomAssignmentTool(Document):
	pass

@frappe.whitelist()
def get_room(branch: str = None) -> dict[str, list]:
	unassigned = []
	assigned = []
	rooms = frappe.db.sql(f"""
		SELECT thsu.name, thsu.service_unit_type, tra.`user`
		FROM `tabHealthcare Service Unit` thsu
		LEFT JOIN `tabRoom Assignment` tra
		ON tra.healthcare_service_unit = thsu.name AND tra.`date` = CURDATE()
		WHERE thsu.is_group = 0 AND thsu.custom_branch = COALESCE ('{branch}' , thsu.custom_branch)""", as_dict=True)
	for room in rooms:
		if room['user']:
			assigned.append(room)
		else:
			unassigned.append(room)
	return {'assigned': assigned, 'unassigned': unassigned}

@frappe.whitelist()
def assign_room(room: str) -> None:
	list = frappe.get_list('Room Assignment', filters={"date": today(), "healthcare_service_unit": room[2:-2]}, fields=['name'])
	if list:
		doc = frappe.get_doc('Room Assignment', list[0].name)
		doc.user = frappe.session.user
		doc.save()
	else:
		doc = frappe.get_doc({
			'doctype': 'Room Assignment',
			'user': frappe.session.user,
			'healthcare_service_unit': room[2:-2],
			'date': today()
		})
		doc.insert()