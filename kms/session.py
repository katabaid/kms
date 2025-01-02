import frappe
from frappe.utils import now


@frappe.whitelist()
def remove_room_assignment(login_manager):
  if bool(
    set(
      frappe.get_all(
        "MCU Assignment Role",
        {"parentfield": "room_assignment_role"},
        pluck="role",
      )
    )
    & set(frappe.get_roles())
  ):
    room_assignments = frappe.get_all(
      "Room Assignment", filters={"user": frappe.session.user}
    )
    if room_assignments:
      for ra in room_assignments:
        frappe.db.set_value("Room Assignment", ra.name,{
          'time_sign_out': now(),
          'assigned': 0
        })
        remove_user_permission(ra.healthcare_service_unit)
    frappe.publish_realtime(
      event="clear_local_storage",
      message={"user": frappe.session.user},
      user = frappe.session.user
    )


@frappe.whitelist()
def add_medical_department(login_manager):
  if bool(
    set(
      frappe.get_all(
        "MCU Assignment Role",
        {"parentfield": "room_assignment_role"},
        pluck="role",
      )
    )
    & set(frappe.get_roles())
  ):
    medical_department = frappe.db.get_value('Healthcare Practitioner',
      {'user_id': frappe.session.user}, 'department')
    if medical_department:
      frappe.defaults.set_user_default('medical_department', medical_department)

def remove_user_permission(room):
  name = frappe.db.get_all('User Permission', 
    filters = [['user', '=', frappe.session.user], ['allow', '=', 'Healthcare Service Unit']],
    pluck = 'name')
  for up in name:
    frappe.db.delete('User Permission', {'name': up})
