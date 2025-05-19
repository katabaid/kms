import frappe, json

# region set_status_from_questionnaire helper
def update_questionnaire_status(questionnaire_name, new_status, reason=None):
  questionnaire = frappe.get_doc('Questionnaire', questionnaire_name)
  questionnaire.status = new_status
  questionnaire.save(ignore_permissions=True)
  return questionnaire

def get_dispatcher_by_appointment(appointment_name):
  dispatcher_names = frappe.db.get_all(
    'Dispatcher',
    filters={'patient_appointment': appointment_name},
    pluck='name'
  )
  if dispatcher_names:
    return frappe.get_doc('Dispatcher', dispatcher_names[0])
  return None

def get_service_units_from_item_code(item_code, branch_name):
  item_doc = frappe.get_doc('Item', item_code)
  service_units = []
  for room in item_doc.custom_room:
    if room.branch == branch_name:
      service_units.append(room.service_unit)
  return service_units

def update_dispatcher_notes(dispatcher, service_units, doctype, docname, reason):
  current_time = frappe.utils.now()
  for assignment in dispatcher.assignment_table:
    if assignment.healthcare_service_unit in service_units:
      note_entry = f'<{current_time}>{doctype} {docname}: {reason}'
      if assignment.notes:
        assignment.notes = assignment.notes + '\n' + note_entry
      else:
        assignment.notes = note_entry
  dispatcher.save(ignore_permissions=True)
# endregion

@frappe.whitelist()
def set_status_from_questionnaire(name, status, doctype, docname, reason):
  questionnaire = update_questionnaire_status(name, status, reason)
  
  dispatcher = get_dispatcher_by_appointment(questionnaire.patient_appointment)
  if dispatcher:
    branch = frappe.db.get_value('Patient Appointment', questionnaire.patient_appointment, 'custom_branch')
    item_code = frappe.db.get_value('Questionnaire Template', questionnaire.template, 'item_code')
    service_units = get_service_units_from_item_code(item_code, branch)
    if service_units:
      update_dispatcher_notes(dispatcher, service_units, doctype, docname, reason)

# region update_exam_header_status helper
def _get_related_service_units(hsu, exam_id):
  related_rooms = frappe.db.get_all(
    "Item Group Service Unit",
    filters={
      "parenttype": "Item",
      "parent": [
        "in", 
        frappe.get_all(
          'MCU Appointment', 
          filters={'parent': exam_id, 'parenttype': 'Patient Appointment', 'examination_item': [
            "in",
            frappe.db.get_all(
              "Item Group Service Unit",
              filters={"parenttype": "Item", "service_unit": hsu},
              pluck="parent",
            ),             
          ]},
          pluck='examination_item')
      ]
    },
    pluck="service_unit",
  )
  return related_rooms

def _validate_room_capacity_on_check_in(hsu, doctype):
  allowed, capacity = frappe.db.get_value(
    'Healthcare Service Unit', hsu, ['allow_appointments', 'service_unit_capacity'])
  if not allowed or not capacity:
    frappe.throw(f'{hsu} cannot be used for patient assignment.')
  status = 'custom_status' if doctype == 'Sample Collection' else 'status'
  service_unit = 'custom_service_unit' if doctype == 'Sample Collection' else 'service_unit'
  queue = frappe.db.count(doctype, {status: 'Checked In', 'docstatus': 0, service_unit: hsu})
  if queue >= capacity:
    frappe.throw(f'{hsu} cannot accept more patients. Submit checked in document in order to receive more patient.')

def _update_dispatcher_status(id, room, status, reason):
  doc = frappe.get_doc('Dispatcher', id)
  doc.db_set({'status': status, 'room': room})
  if status == 'Removed':
    doc.add_comment('Comment', f"Removed from {room} examination room because {reason}.")
  dispatcher_user = frappe.get_all(
    'Dispatcher Settings', 
    filters={'branch': doc.branch, 'enable_date': frappe.utils.today()}, 
    pluck='dispatcher')
  for user in dispatcher_user:
    frappe.publish_realtime(
      event='update_exam_header_status',
      message={
        'room': room,
        'status': status,
        'patient': doc.patient_name,
        'reason': reason
      },
      user=user
    )

def _update_related_rooms_status(params):
  def _update_rooms(
    doctype_name,   filters,        fields,           hsu_field, 
    hsu,            doctype,        docname,          reason, 
    status,         clear_reference,  related_rooms):
    rooms = frappe.get_all(doctype_name, filters=filters, fields=fields)
    for room in rooms:
      note = f'<{frappe.utils.now()}>{status} {doctype} {docname} {reason if reason else ''}'
      existing_notes = room.get('notes', '')
      notes_to_save = existing_notes + '\n' + note if existing_notes else note
      if room.get(hsu_field) == hsu:
        updates = {'status': status, 'notes': notes_to_save, 'reference_doc':  docname}
        if clear_reference:
          updates.update({'reference_doc': ''})
        frappe.db.set_value(doctype_name, room.name, updates)
      elif room.get(hsu_field) in related_rooms:
        frappe.db.set_value(doctype_name, room.name, 'notes', notes_to_save)

  exam_id           = params.get('exam_id')
  hsu               = params.get('hsu')
  doctype           = params.get('doctype')
  docname           = params.get('docname')
  reason            = params.get('reason')
  status            = params.get('status')
  dispatcher_id     = params.get('dispatcher_id')
  queue_pooling_id  = params.get('queue_pooling_id')
  clear_reference   = params.get('clear_reference')

  # if (not all((exam_id, hsu, doctype, docname, status)) or 
  #   (not any((dispatcher_id, queue_pooling_id)) or all ((dispatcher_id, queue_pooling_id)))):
  #   if not all((exam_id, hsu, doctype, docname, status)):
  #     print(1)
  #   if not any((dispatcher_id, queue_pooling_id)) or all ((dispatcher_id, queue_pooling_id)):
  #     print(2)
  #   frappe.throw('Not all parameter requirements are met.')

  related_rooms = _get_related_service_units(hsu, exam_id)
  if dispatcher_id:
    _update_rooms(
      'Dispatcher Room',
      {'parent': dispatcher_id, 'healthcare_service_unit': ['in', related_rooms]},
      ['name', 'notes', 'healthcare_service_unit'],
      'healthcare_service_unit',
      hsu, doctype, docname, reason, status, clear_reference, related_rooms
    )
  elif queue_pooling_id:
    _update_rooms(
      'MCU Queue Pooling',
      {'patient_appointment': exam_id, 'service_unit': ['in', related_rooms]},
      ['name', 'notes', 'service_unit'],
      'service_unit',
      hsu, doctype, docname, reason, status, clear_reference, related_rooms
    )
  # else:
  #   frappe.throw('Internal Error: Neither Dispatcher ID nor MCU Queue Pooling are given to continue.')

def _update_exam_status(doctype, docname, status, cancel):
  """Updates the status of an examination document."""
  exam_doc = frappe.get_doc(doctype, docname)
  if cancel:
    exam_doc.db_set('docstatus', 2)
  status_field = 'custom_status' if doctype == 'Sample Collection' else 'status'
  exam_doc.db_set(status_field, status)
# endregion

@frappe.whitelist()
def update_exam_header_status(hsu, doctype, docname, status, exam_id, options={}):
  # Calling from Examination Room for Check In and Remove
  # initiliaze variables
  if isinstance(options, str):
    options = json.loads(options)
  dispatcher_id = options.get('dispatcher_id')
  queue_pooling_id = options.get('queue_pooling_id')
  reason = options.get('reason')
  cancel = status == 'Removed'
  # validate room capacity
  if status == 'Checked In':
    _validate_room_capacity_on_check_in(hsu, doctype)
  # update dispatcher or queue pooling status
  room_status = 'Wait for Room Assignment' if status == 'Removed' else 'Ongoing Examination'
  if dispatcher_id:
    hsu_param = hsu if status == 'Checked In' else ''
    status_param = 'In Room' if status == 'Checked In' else 'In Queue'
    _update_dispatcher_status(dispatcher_id, hsu_param, status_param, reason)
  # initialize parameters for room status
  set_reference = room_status == 'Ongoing Examination'
  clear_reference = room_status == 'Wait for Room Assignment'
  params = {
    'exam_id': exam_id, 
    'hsu': hsu, 
    'doctype': doctype, 
    'docname': docname, 
    'reason': reason, 
    'status': room_status, 
    'dispatcher_id': dispatcher_id, 
    'queue_pooling_id': queue_pooling_id, 
    'clear_reference': clear_reference}
  # update status to current room and related rooms and its own doctype
  _update_related_rooms_status(params)
  _update_exam_status(doctype, docname, status, cancel)

@frappe.whitelist()
def update_exam_item_status(dispatcher, qp, doctype, docname, hsu, exam_id, exam_item, status, reason=None):
  if not all((exam_id, exam_item, status)):
    frappe.throw('Internal Error: Not all required parameters available.')
  update_sql = """
    UPDATE `tabMCU Appointment` SET `status` = %s WHERE name IN 
    (SELECT name FROM `tabMCU Appointment` tma 
    WHERE (parent = %s or parent= %s)
    AND (examination_item IN (SELECT lab_test_code FROM `tabLab Test Template` tltt WHERE sample = %s) 
    OR examination_item = %s))"""
  update_val = (status, dispatcher, exam_id, exam_item, exam_item)
  try:
    frappe.db.sql(update_sql, update_val)
    related_rooms = _get_related_service_units(hsu, exam_id)
    if dispatcher:
      rooms = frappe.get_all(
        'Dispatcher Room', 
        filters={'parent': dispatcher, 'healthcare_service_unit': ['in', related_rooms]}, 
        fields=['name', 'notes', 'healthcare_service_unit'])
      for room in rooms:
        note = f'<{frappe.utils.now()}>{status} {doctype} {docname} {reason if reason else ''}'
        existing_notes = room.get('notes', '')
        notes_to_save = existing_notes + '\n' + note if existing_notes else note
        frappe.db.set_value('Dispatcher Room', room.name, 'notes', notes_to_save)
    elif qp:
      rooms = frappe.get_all(
        'MCU Queue Pooling', 
        filters={'appointment': exam_id, 'service_unit': ['in', related_rooms]}, 
        fields=['name', 'notes', 'service_unit'])
      for room in rooms:
        note = f'<{frappe.utils.now()}>{status} {doctype} {docname} {reason if reason else ''}'
        existing_notes = room.get('notes', '')
        notes_to_save = existing_notes + '\n' + note if existing_notes else note
        frappe.db.set_value('Dispatcher Room', room.name, 'notes', notes_to_save)
  except Exception as e:
    frappe.throw(f"Database error occurred while updating '{exam_item}' status.")