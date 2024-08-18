from frappe.desk.doctype.todo.todo import ToDo as OriginalToDo
import frappe
from frappe import _


class CustomToDo(OriginalToDo):
  def validate(self):
    user_roles = frappe.get_roles(frappe.session.user)
    if frappe.session.user != "Administrator" and 'System Manager' not in user_roles:
      if self.allocated_to != frappe.session.user:
        frappe.throw(_("You can only view tasks allocated to yourself."))
    super().validate()
