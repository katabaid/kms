import frappe
from frappe.utils import now

@frappe.whitelist()
def remove_room_assignment(login_manager):
  if bool(set(frappe.get_all('MCU Assignment Role', {'parentfield': 'room_assignment_role'}, pluck = 'role')) & set(frappe.get_roles())):
    room_assignments = frappe.get_all("Room Assignment", filters={"user": frappe.session.user})
    if room_assignments:
      for ra in room_assignments:
        doc = frappe.get_doc('Room Assignment', ra.name)
        doc.time_sign_out = now()
        doc.assigned = 0
        doc.save()

def redirect_after_login(login_manager):
  if bool(set(frappe.get_all('MCU Assignment Role', {'parentfield': 'room_assignment_role'}, pluck = 'role')) & set(frappe.get_roles())):
    frappe.local.response['home_page'] = '/app/room-assignment/new-room-assignment'