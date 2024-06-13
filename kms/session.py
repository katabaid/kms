import frappe

@frappe.whitelist()
def remove_room_assignment(login_manager):
  if "Healthcare User" in frappe.get_roles(frappe.session.user):
    list = frappe.get_list("Room Assignment", filters={"user": frappe.session.user})
    if list:
      for ra in list:
        doc = frappe.get_doc('Room Assignment', ra.name)
        doc.user = ''
        doc.save()