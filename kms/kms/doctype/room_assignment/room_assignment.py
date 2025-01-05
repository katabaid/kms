# Copyright (c) 2024, GIS and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import today, now
from frappe.model.document import Document

class RoomAssignment(Document):
  def before_insert(self):
    if frappe.db.exists(
      "Room Assignment", 
      {"user": frappe.session.user, "date": today(), "assigned": 1}
    ):
      frappe.throw(f"""You already sign for room: {self.healthcare_service_unit}. Please use Change Room button to move to this room.""")
    self.date = today()
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
  doc.save(ignore_permissions=True)
  #remove_user_permission()

  new_doc = frappe.new_doc("Room Assignment")
  new_doc.healthcare_service_unit = room
  new_doc.date = today()
  new_doc.user = frappe.session.user
  new_doc.time_sign_in = now()
  new_doc.assigned = 1
  new_doc.save(ignore_permissions=True)
  set_session_default(room)

  return new_doc.name

@frappe.whitelist()
def get_room_list(dept, room):
  if not dept:
    return []
  rooms = frappe.db.get_all(
    'Healthcare Service Unit',
    filters = {
      'is_group': 0,
      'custom_department': dept,
      'name': ['!=', room]
    },
    pluck = 'name')
  return rooms

def set_session_default(room):
  frappe.defaults.set_user_default('healthcare_service_unit', room)
  frappe.defaults.set_user_default(
    'branch', frappe.db.get_value('Healthcare Service Unit', room, 'custom_branch'))

def set_user_permisssion(room):
  up_name = frappe.get_all(
    'User Permission',
    filters = {
      'allow': 'Healthcare Service Unit',
      'user': frappe.session.user,
    },
    pluck = 'name',
    limit = 1
  )
  if up_name:
    doc = frappe.get_doc('User Permission', up_name[0])
    if doc.for_value != room:
      doc.for_value = room
      doc.save(ignore_permissions=True)
  else:
    doc = frappe.get_doc({
      'doctype': 'User Permission',
      'user': frappe.session.user,
      'allow': 'Healthcare Service Unit',
      'for_value': room,
      'apply_to_all_doctypes': 1,
      'is_default': 1
      })
    doc.insert(ignore_permissions=True)

def remove_user_permission():
  name = frappe.db.get_all('User Permission', 
    filters = [['user', '=', frappe.session.user], ['allow', '=', 'Healthcare Service Unit']],
    pluck = 'name')
  for up in name:
    frappe.db.delete('User Permission', {'name': up})
