import frappe
from frappe import _
from datetime import timedelta, datetime
from frappe.model.document import Document

class KmsShiftRequest(Document):
  def on_submit(self):
    if self.status not in ["Approved", "Rejected"]:
      frappe.throw(_("Only Shift Request with status 'Approved' and 'Rejected' can be submitted"))
    if not self.shift_type and not self.custom_swap_with_employee:
      frappe.throw(_("Only Shift Request with new Shift Type or Swap with Employee."))
    elif self.custom_swap_with_employee:
      for date in iterate_dates(datetime.strptime(self.from_date, '%Y-%m-%d'), datetime.strptime(self.to_date, '%Y-%m-%d')):
        if not frappe.db.exists("Shift Assignment", {"employee": self.employee, "status": "Active", "docstatus": 1, 'start_date': date}):
          frappe.throw(_("Shift Assignment not found for Employee: {0} and Date: {1}").format(frappe.bold(self.employee), frappe.bold(date)))
        if not frappe.db.exists("Shift Assignment", {"employee": self.custom_swap_with_employee, "status": "Active", "docstatus": 1, 'start_date': date}):
          frappe.throw(_("Shift Assignment not found for Employee: {0} and Date: {1}").format(frappe.bold(self.custom_swap_with_employee), frappe.bold(date)))
        shift_1 = frappe.db.get_value("Shift Assignment", {"employee": self.employee, "status": "Active", "docstatus": 1, 'start_date': date}, "shift_type")
        shift_2 = frappe.db.get_value("Shift Assignment", {"employee": self.custom_swap_with_employee, "status": "Active", "docstatus": 1, 'start_date': date}, "shift_type")
        self.create_shift_assignment(self.custom_swap_with_employee, date, date, shift_1)
        self.create_shift_assignment(self.employee, date, date, shift_2)
        if date.weekday() == 5:
          to_cancel1 = frappe.db.exists("Shift Assignment", {"employee": self.employee, "status": "Active", "docstatus": 1, 'start_date': date+timedelta(days=7)})
          to_cancel2 = frappe.db.exists("Shift Assignment", {"employee": self.custom_swap_with_employee, "status": "Active", "docstatus": 1, 'start_date': date+timedelta(days=7)})
          self.create_shift_assignment(self.custom_swap_with_employee, date+timedelta(days=7), date+timedelta(days=7), shift_2, to_cancel2)
          self.create_shift_assignment(self.employee, date+timedelta(days=7), date+timedelta(days=7), shift_1, to_cancel1)
    else:
      for date in iterate_dates(datetime.strptime(self.from_date, '%Y-%m-%d'), datetime.strptime(self.to_date, '%Y-%m-%d')):
        if not frappe.db.exists("Shift Assignment", {"employee": self.employee, "status": "Active", "docstatus": 1, 'start_date': date}):
          frappe.throw(_("Shift Assignment not found for Employee: {0} and Date: {1}").format(frappe.bold(self.employee), frappe.bold(date)))
        self.create_shift_assignment(self.employee, date, date, self.shift_type)
      
  def create_shift_assignment(self, employee, from_date, to_date, shift_type, to_cancel=True):
    if to_cancel:
      to_cancel = frappe.get_doc("Shift Assignment", {"employee": employee, "start_date": from_date, "end_date": to_date, "status": "Active", "docstatus": 1})
      to_cancel.cancel()
    assignment_doc = frappe.new_doc("Shift Assignment")
    assignment_doc.company = self.company
    assignment_doc.shift_type = shift_type
    assignment_doc.employee = employee
    assignment_doc.start_date = from_date
    assignment_doc.end_date = to_date
    assignment_doc.shift_request = self.name
    assignment_doc.flags.ignore_permissions = 1
    assignment_doc.insert()
    assignment_doc.submit()

def iterate_dates(start_date, end_date):
  current_date = start_date
  while current_date <= end_date:
      yield current_date
      current_date += timedelta(days=1)