# Copyright (c) 2024, GIS and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import today, now
from frappe.model.document import Document

class RoomAssignment(Document):
  def before_insert(self):
    self.user = frappe.session.user
  def validate(self):
    if frappe.db.exists("Room Assignment", {"user": frappe.session.user, "date": today(), "assigned": 1}):
      frappe.throw(f"""You already sign for room: {self.room}. Please use Change Room button to move to this room.""")
    self.user = frappe.session.user
    self.time_sign_in = now()
    self.assigned = 1

@frappe.whitelist()
def change_room(name, room):
  doc = frappe.get_doc('Room Assignment', name)
  if doc.user is None:
    frappe.throw("User column is empty.")
  if doc.date.strftime('%Y-%m-%d') != today():
    frappe.throw("Room assignment date must be today.")
  doc.time_sign_out = now()
  doc.assigned = 0
  doc.save()

  new_doc = frappe.new_doc("Room Assignment")
  new_doc.healthcare_service_unit = room
  new_doc.date = today()
  new_doc.user = frappe.session.user
  new_doc.time_sign_in = now()
  new_doc.assigned = 1
  new_doc.save()
  return new_doc.name
