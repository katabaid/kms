import frappe

def _update_status_if_match(items, key_field, match_list, valid_statuses, new_status='Rescheduled'):
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
    _update_status_if_match(
      doc.assignment_table,
      "healthcare_service_unit",
      related_room_list,
      ["Wait for Room Assignment", "Additional or Retest Request"]
    )
    _update_status_if_match(
      doc.package,
      "examination_item",
      exam_item_list,
      ["To Retest", "Started"]
    )
    _update_status_if_match(
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
    _update_status_if_match(
      pa_doc.custom_mcu_exam_items,
      "examination_item",
      exam_item_list,
      ["To Retest", "Started"]
    )
    _update_status_if_match(
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

@frappe.whitelist()
def update_mcu_related_statuses(meth, disp=None, room=None, exam=None, doct=None, item=None):
  status_map = {
    "Refuse": "Refused",
    "Reschedule": "Rescheduled",
    "Remove": "Removed",
    "Retest": "To Retest"
  }
  if meth not in status_map:
    frappe.throw(f"Invalid method: {meth}. Allowed values: {', '.join(status_map.keys())}")
  if not _is_valid_combination():
    frappe.throw("Invalid argument combination.")
  exam_doc, disp_doc, appt_doc, error = _get_exam_and_dispatcher_documents(disp, exam, doct)
  if error:
    frappe.throw(f"Failed to load required documents: {str(error)}")
  if not appt_doc:
    frappe.throw(f"Failed to load Patient Appointment document.")
  room_list, item_list, rect_list, error = _get_parameter_lists(appt_doc.name, appt_doc.custom_branch, room, item)
  if error:
    frappe.throw(f"Failed to load parameter lists: {str(error)}")
  if disp_doc:
    try:
      _update_dispatcher_status(meth, disp_doc, room_list, item_list, rect_list, status_map[meth])
      disp_doc.save()
      _update_appointment_status(meth, appt_doc,room_list, item_list, rect_list, status_map[meth])
    except Exception as e:
      frappe.throw(f"Error processing Dispatcher assignment or package: {e}")
  return {'docname': appt_doc.name}
  
def _is_valid_combination(disp, room, exam, doct, item):
  return (
    (disp and room and not item and not exam and not doct) or
    (disp and item and not room and not exam and not doct) or
    (exam and doct and not disp and not room and not item) or
    (exam and doct and item and not disp and not room)
  )

def _get_exam_and_dispatcher_documents(disp, exam, doct):
  try:
    exam_doc = disp_doc = appt_doc = None
    if disp:
      disp_doc = frappe.get_doc('Dispatcher', disp)
      appt_doc = frappe.get_doc('Patient Appointment', disp.patient_appointment)
    elif exam and doct:
      exam_doc = frappe.get_doc(doct, exam)
      if getattr(exam_doc, 'dispatcher', None):
        disp_doc = frappe.get_doc(doct, exam_doc.dispatcher)
        appt_doc = frappe.get_doc('Patient Appointment', exam_doc.appointment)
      elif getattr(exam_doc, 'custom_dispatcher', None):
        disp_doc = frappe.get_doc(doct, exam_doc.custom_dispatcher)
        appt_doc = frappe.get_doc('Patient Appointment', exam_doc.custom_appointment)
    return exam_doc, disp_doc, appt_doc, None
  except Exception as e:
    return None, None, None, e
  
def _get_parameter_lists(parent, branch, room, item):
  try:
    param_sql = """
      SELECT tigsu.service_unit, tigsu.parent, thsu.custom_reception_room
      FROM `tabItem Group Service Unit` tigsu, `tabHealthcare Service Unit` thsu
      WHERE branch = %s AND parent IN ( 
        SELECT examination_item FROM `tabMCU Appointment` WHERE parent = %s
        AND (examination_item IN (
          SELECT parent FROM `tabItem Group Service Unit` 
          WHERE branch = %s AND service_unit = %s
        ) OR examination_item = %s)
      ) AND tigsu.service_unit = thsu.name AND tigsu.branch = thsu.custom_branch
    """
    params = frappe.db.sql(param_sql, (branch, parent, branch, room, item))
    return list({r[0] for r in params}), list({r[1] for r in params}), list({r[2] for r in params}), None
  except Exception as e:
    return None, None, None, e
  
def _update_dispatcher_status(meth, disp_doc, room_list, item_list, rect_list, new_status):
  _update_status_if_match(
    disp_doc.assignment_table,
    "healthcare_service_unit",
    room_list,
    ["Wait for Room Assignment", "Additional or Retest Request"],
    new_status
  )
  if meth != 'Remove':
    _update_status_if_match(
      disp_doc.package,
      "examination_item",
      item_list,
      ["To Retest", "Started"],
      new_status
    )
  _update_status_if_match(
    disp_doc.assignment_table,
    "healthcare_service_unit",
    rect_list,
    ["Wait for Sample"],
    new_status
  )
  if meth in ['Remove', 'Retest']:
    disp_doc.status = 'In Queue'

def _update_appointment_status(meth, appt_doc, room_list, item_list, rect_list, new_status):
  if meth != 'Remove':
    _update_status_if_match(
      appt_doc.custom_mcu_exam_items,
      "healthcare_service_unit",
      item_list,
      ["Wait for Room Assignment", "Additional or Retest Request"],
      new_status
    )
    _update_status_if_match(
      appt_doc.custom_additional_mcu_items,
      "examination_item",
      item_list,
      ["To Retest", "Started"],
      new_status
    )
    if appt_doc.appointment_date != frappe.utils.today():
      appt_doc.appointment_date = frappe.utils.today()