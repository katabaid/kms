# Copyright (c) 2024, GIS and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import today
from frappe.model.document import Document

class RoomAssignment(Document):
   pass

@frappe.whitelist()
def change_room(name, room):
  doc = frappe.get_doc('Room Assignment', name)
  if doc.user is None:
    frappe.throw("User column is empty.")
  if doc.date.strftime('%Y-%m-%d') != today():
    frappe.throw("Room assignment date must be today.")
  user = doc.user
  doc.user = ''
  doc.save()

  if frappe.db.exists("Room Assignment", {"healthcare_service_unit": room, "date": today()}):
    new_doc = frappe.get_doc("Room Assignment", {"healthcare_service_unit": room, "date": today()})
    if new_doc.user:
      frappe.throw("Room already assigned to user.")
    new_doc.user = user
    new_doc.save()
  else:
    new_doc = frappe.new_doc("Room Assignment")
    new_doc.healthcare_service_unit = room
    new_doc.date = today()
    new_doc.user = user
    new_doc.save()
  return new_doc.name
