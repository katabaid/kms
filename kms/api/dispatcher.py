import frappe

@frappe.whitelist()
def update_rescheduled_dispatcher(appointment):
  name = frappe.db.get_value('Dispatcher', 
    {'patient_appointment': appointment, 'status': 'Rescheduled'})
  if name:
    dispatcher = frappe.get_doc('Dispatcher', name)
    dispatcher.status = 'In Queue'
    for room in dispatcher.assignment_table:
      if room.status == 'Rescheduled':
        room.status = 'Wait for Room Assignment'
    for exam in dispatcher.package:
      if exam.status == 'Rescheduled':
        exam.status = 'Started'
    dispatcher.save(ignore_permissions=True)
