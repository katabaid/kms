# Copyright (c) 2024, GIS and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document
import frappe

class DispatcherTool(Document):
	pass

@frappe.whitelist()
def get_room(exam_id):
	room_list = frappe.db.sql(f"""select distinct tigsu.service_unit as su from `tabItem Group Service Unit` tigsu, `tabMCU Appointment` tma, `tabPatient Appointment` tpa
		WHERE tma.parent = '{exam_id}'
		and tma.parenttype = 'Patient Appointment'
		and tma.parent = tpa.name 
		and tigsu.parent = tma.item_group
		and tigsu.branch = tpa.custom_branch """, as_dict=True)
	rooms = []
	for room in room_list:
		rooms.append(frappe._dict({'room': room.su}))
	rooms = [dict(t) for t in {tuple(d.items()) for d in rooms}]	
	return rooms