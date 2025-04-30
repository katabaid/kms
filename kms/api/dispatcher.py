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

@frappe.whitelist()
def reschedule(name, room):
  doc = frappe.get_doc('Dispatcher', name)
  #get room and related, then change its status from Wait for Room Assignment,Additional or Retest Request to Rescheduled
  related_rooms_sql = """
    SELECT service_unit, parent FROM `tabItem Group Service Unit` 
    WHERE branch = %s AND parent IN ( 
      SELECT examination_item FROM `tabMCU Appointment` WHERE parent = %s
      AND examination_item in (
        SELECT parent FROM `tabItem Group Service Unit` WHERE branch = %s
        AND service_unit = %s))
  """
  related_rooms = frappe.db.sql(related_rooms_sql, (doc.branch, name, doc.branch, room))
  related_room_list = list ({r[0] for r in related_rooms})
  exam_item_list = list ({r[1] for r in related_rooms})
  for hsu in doc.assignment_table:
    if hsu.healthcare_service_unit in related_room_list:
      if hsu.status in ['Wait for Room Assignment', 'Additional or Retest Request']:
        hsu.status = 'Rescheduled'
  #get related exam item, then cange its status Started to Rescheduled
  for exam in doc.package:
    if exam.examination_item in exam_item_list:
      if exam.status in ['To Retest', 'Started']:
        exam.status = 'Rescheduled'
  doc.save()
  return {'docname': doc.name}