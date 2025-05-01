import frappe

@frappe.whitelist()
def checkin_rescheduled_dispatcher(appointment):
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

def update_status_if_match(items, key_field, match_list, valid_statuses, new_status='Rescheduled'):
  for item in items:
    if getattr(item, key_field) in match_list and item.status in valid_statuses:
      item.status = new_status

@frappe.whitelist()
def reschedule(name, room):
  try:
    doc = frappe.get_doc('Dispatcher', name)
  except Exception as e:
    frappe.throw(f"Failed to load Dispatcher document: {e}")

  try:
    related_rooms_sql = """
      SELECT tigsu.service_unit, tigsu.parent, thsu.custom_reception_room
      FROM `tabItem Group Service Unit` tigsu, `tabHealthcare Service Unit` thsu
      WHERE branch = %s AND parent IN ( 
        SELECT examination_item FROM `tabMCU Appointment` WHERE parent = %s
        AND examination_item IN (
          SELECT parent FROM `tabItem Group Service Unit` 
          WHERE branch = %s AND service_unit = %s
        )
      ) AND tigsu.service_unit = thsu.name AND tigsu.branch = thsu.custom_branch
    """
    related_rooms = frappe.db.sql(related_rooms_sql, (doc.branch, name, doc.branch, room))
    related_room_list = list({r[0] for r in related_rooms})
    exam_item_list = list({r[1] for r in related_rooms})
    reception_list = list({r[2] for r in related_rooms})
  except Exception as e:
    frappe.throw(f"Error querying related rooms: {e}")

  try:
    update_status_if_match(
      doc.assignment_table,
      "healthcare_service_unit",
      related_room_list,
      ["Wait for Room Assignment", "Additional or Retest Request"]
    )
    update_status_if_match(
      doc.package,
      "examination_item",
      exam_item_list,
      ["To Retest", "Started"]
    )
    update_status_if_match(
      doc.assignment_table,
      "healthcare_service_unit",
      reception_list,
      ["Wait for Sample"]
    )
    doc.save()
  except Exception as e:
    frappe.throw(f"Error processing Dispatcher assignment or package: {e}")

  try:
    pa_doc = frappe.get_doc("Patient Appointment", doc.patient_appointment)
    update_status_if_match(
      pa_doc.custom_mcu_exam_items,
      "examination_item",
      exam_item_list,
      ["To Retest", "Started"]
    )
    update_status_if_match(
      pa_doc.custom_additional_mcu_items,
      "examination_item",
      exam_item_list,
      ["To Retest", "Started"]
    )
    if pa_doc.appointment_date != frappe.utils.today():
      pa_doc.appointment_date = frappe.utils.today()
    pa_doc.save(ignore_permissions=True)
  except Exception as e:
    frappe.throw(f"Error updating Patient Appointment: {e}")
  return {"docname": doc.name}
