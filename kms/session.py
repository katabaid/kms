import frappe
from frappe.utils import now
from frappe import _

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
def process_login(login_manager):
  if bool(
    set(frappe.get_all(
      "MCU Assignment Role",
      {"parentfield": "room_assignment_role"},
      pluck="role",)
    )
    & set(frappe.get_roles())
  ):
    set_session_default('department', 'medical_department')
    set_session_default('custom_branch', 'branch')
    hsu = frappe.defaults.get_user_default('Healthcare Service Unit')
    if not hsu:
      frappe.db.set_default(
        f"user_defaults:{frappe.session.user}:redirect_after_login",
        '/app/room-assignment/new-room-assignment')

def remove_user_permission(room):
  name = frappe.db.get_all('User Permission', 
    filters = [
      ['user', '=', frappe.session.user], 
      ['allow', '=', 'Healthcare Service Unit']
    ],
    pluck = 'name')
  for up in name:
    frappe.db.delete('User Permission', {'name': up})

def set_session_default(get_column, set_column):
  medical_department = frappe.db.get_value(
    'Healthcare Practitioner', {'user_id': frappe.session.user}, get_column)
  if medical_department:
    frappe.defaults.set_user_default(set_column, medical_department)

@frappe.whitelist()
def get_redirect_url():
  if frappe.session.user == 'Guest':
    return
  redirect_url = frappe.db.get_default(
    f"user_defaults:{frappe.session.user}:redirect_after_login"
  )
  if redirect_url:
      # Clear the stored redirect URL
    frappe.db.set_default(
      f"user_defaults:{frappe.session.user}:redirect_after_login",
      None
    )
    return redirect_url
  return None