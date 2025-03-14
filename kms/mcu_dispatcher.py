import frappe

def update_questionnaire_status(questionnaire_name, new_status, reason=None):
  """Updates the status of a Questionnaire document.

  Args:
    questionnaire_name (str): The name of the Questionnaire document.
    new_status (str): The new status to set for the Questionnaire.
    reason (str, optional): The reason for the status change. Defaults to None.
  """
  questionnaire = frappe.get_doc('Questionnaire', questionnaire_name)
  questionnaire.status = new_status
  questionnaire.save(ignore_permissions=True)
  return questionnaire

def get_dispatcher_by_appointment(appointment_name):
  """Retrieves the Dispatcher document associated with a Patient Appointment.

  Args:
    appointment_name (str): The name of the Patient Appointment document.

  Returns:
    frappe.model.document.Document or None: The Dispatcher document, or None if not found.
  """
  dispatcher_names = frappe.db.get_all(
    'Dispatcher',
    filters={'patient_appointment': appointment_name},
    pluck='name'
  )
  if dispatcher_names:
    return frappe.get_doc('Dispatcher', dispatcher_names[0])
  return None

def get_service_units_from_item_code(item_code, branch_name):
  """Retrieves the associated service units for a Questionnaire Template and Branch.

  Args:
    questionnaire_template_name (str): The name of the Questionnaire Template.
    branch_name (str): The name of the Branch.

  Returns:
    list: A list of service unit names.
  """
  
  item_doc = frappe.get_doc('Item', item_code)
  service_units = []
  for room in item_doc.custom_room:
    if room.branch == branch_name:
      service_units.append(room.service_unit)
  return service_units

def update_dispatcher_notes(dispatcher, service_units, doctype, docname, reason):
  """Updates the notes in the Dispatcher document for specific service units.

  Args:
    dispatcher (frappe.model.document.Document): The Dispatcher document.
    service_units (list): A list of service unit names.
    doctype (str): The doctype related to the note.
    docname (str): The docname related to the note.
    reason (str): The reason to include in the note.
  """
  current_time = frappe.utils.now()
  for assignment in dispatcher.assignment_table:
    if assignment.healthcare_service_unit in service_units:
      note_entry = f'<{current_time}>{doctype} {docname}: {reason}'
      if assignment.notes:
        assignment.notes = assignment.notes + '\n' + note_entry
      else:
        assignment.notes = note_entry
  dispatcher.save(ignore_permissions=True)

def get_dispatcher_related_service_units(hsu, dispatcher_id):
  """
  Retrieves related service units based on shared parent Items in Item Group Service Unit.

  Args:
    hsu (str): The name of the primary Healthcare Service Unit.
    dispatcher_id (str): The name of the Dispatcher document.

  Returns:
    list: A list of related service unit names.
  """

  related_rooms = frappe.db.get_all(
    "Item Group Service Unit",
    filters={
      "parenttype": "Item",
      "service_unit": ["!=", hsu],
      "parent": [
        "in",
        frappe.db.get_all(
            "Item Group Service Unit",
            filters={"parenttype": "Item", "service_unit": hsu},
            pluck="parent",
        ),
      ],
      "parent": [
        "in", 
        frappe.get_all(
          'MCU Appointment', 
          filters={'parent': dispatcher_id, 'parenttype': 'Dispatcher'},
          pluck='examination_item')
      ]
    },
    fields=["service_unit"],
    pluck="service_unit",
  )
  return related_rooms

def _update_dispatcher_assignment_table(
    doc, hsu, doctype, docname, reason, status, set_reference=False, clear_reference=False
):
    """
    Updates the Dispatcher's assignment table based on the provided parameters.

    Args:
        doc (frappe.model.document.Document): The Dispatcher document.
        hsu (str): The Healthcare Service Unit name.
        doctype (str): The doctype related to the update.
        docname (str): The docname related to the update.
        reason (str, optional): The reason for the update.
        status (str): The status to set for the HSU.
        set_reference (bool, optional): Whether to set the reference doc. Defaults to False.
        clear_reference (bool, optional): Whether to clear the reference doc. Defaults to False.
    """
    related_rooms = get_dispatcher_related_service_units(hsu, doc.name)
    for room in doc.assignment_table:
        if room.healthcare_service_unit == hsu:
            room.status = status
            if set_reference:
                room.reference_doctype = doctype
                room.reference_doc = docname
            if clear_reference:
                room.reference_doc = ''
            _add_note_to_room(room, doctype, docname, reason)
        elif room.healthcare_service_unit in related_rooms:
            _add_note_to_room(room, doctype, docname, reason)

def _add_note_to_room(room, doctype, docname, reason):
    """Adds a note to a Dispatcher assignment table row."""
    if reason:
        current_time = frappe.utils.now()
        note_entry = f'<{current_time}>{doctype} {docname}: {reason}'
        if room.notes:
            room.notes = room.notes + '\n' + note_entry
        else:
            room.notes = note_entry

def _update_dispatcher_status(doc, room, status ):
	doc.status = status
	doc.room = room

def _create_comment(doc, text):
  """Adds a comment to the Dispatcher document."""
  doc.add_comment('Comment', text)

def _create_notification(doc, dispatcher_user, subject):
  """Creates a notification for a Dispatcher."""
  notification_doc = frappe.new_doc('Notification Log')
  notification_doc.for_user = dispatcher_user
  notification_doc.from_user = frappe.session.user
  notification_doc.document_type = 'Dispatcher'
  notification_doc.document_name = doc.name
  notification_doc.subject = subject
  notification_doc.insert(ignore_permissions=True)

def _update_exam_status(doctype, docname, status):
	"""Updates the status of an examination document."""
	exam_doc = frappe.get_doc(doctype, docname)
	exam_doc.db_set('docstatus', 2)
	status_field = 'custom_status' if doctype == 'Sample Collection' else 'status'
	exam_doc.db_set(status_field, status)

@frappe.whitelist()
def set_status_from_questionnaire(name, status, doctype, docname, reason):
  """Sets the status of a Questionnaire and updates related Dispatcher notes.

  Args:
    name (str): The name of the Questionnaire document.
    status (str): The new status for the Questionnaire.
    doctype (str): The doctype related to the status change.
    docname (str): The docname related to the status change.
    reason (str): The reason for the status change.
  """
    
  questionnaire = update_questionnaire_status(name, status, reason)
  
  dispatcher = get_dispatcher_by_appointment(questionnaire.patient_appointment)
  if dispatcher:
    branch = frappe.db.get_value('Patient Appointment', questionnaire.patient_appointment, 'custom_branch')
    item_code = frappe.db.get_value('Questionnaire Template', questionnaire.template, 'item_code')
    service_units = get_service_units_from_item_code(item_code, branch)
    if service_units:
      update_dispatcher_notes(dispatcher, service_units, doctype, docname, reason)

@frappe.whitelist()
def checkin_room(dispatcher_id, hsu, doctype, docname, reason='Checked In'):
	"""
	Checks in a patient to a room and updates the Dispatcher document.

	Args:
		dispatcher_id (str): The name of the Dispatcher document.
		hsu (str): The Healthcare Service Unit name.
		doctype (str): The doctype related to the check-in.
		docname (str): The docname related to the check-in.
		reason (str, optional): The reason for the check-in.

	Returns:
		dict: A dictionary containing the status and a message.
	"""
	doc = frappe.get_doc('Dispatcher', dispatcher_id)
	_update_dispatcher_status(doc, hsu, 'In Room')
	if not reason:
		reason = 'Checked In'
	_update_dispatcher_assignment_table(
		doc, hsu, doctype, docname, reason, 'Ongoing Examination', set_reference=True
	)
	doc.save(ignore_permissions=True)
	return {'status': 'success', 'message': 'Checked In.'}

@frappe.whitelist()
def removed_from_room(dispatcher_id, hsu, doctype, docname, reason):
    """
    Removes a patient from a room and updates the Dispatcher document.

    Args:
        dispatcher_id (str): The name of the Dispatcher document.
        hsu (str): The Healthcare Service Unit name.
        doctype (str): The doctype related to the removal.
        docname (str): The docname related to the removal.
        reason (str, optional): The reason for the removal.

    Returns:
        dict: A dictionary containing the status and a message.
    """
    doc = frappe.get_doc('Dispatcher', dispatcher_id)
    _update_dispatcher_status(doc, '', 'In Queue')
    if reason:
       f'Removed from Room {hsu}: {reason}'
    _update_dispatcher_assignment_table(
        doc, hsu, doctype, docname, reason, 'Wait for Room Assignment', clear_reference=True
    )
    _create_comment(doc, f"Removed from {hsu} examination room.")

    dispatcher_user = frappe.db.get_value(
        "Dispatcher Settings",
        {"branch": doc.branch, 'enable_date': doc.date},
        ['dispatcher']
    )
    _create_notification(
        doc,
        dispatcher_user,
        f"Patient <strong>{doc.patient}</strong> removed from {hsu} room."
    )
    _update_exam_status(doctype, docname, 'Removed')
    doc.save(ignore_permissions=True)
    return {'status': 'success', 'message': 'Removed from examination room.'}
