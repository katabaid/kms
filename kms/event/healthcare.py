import frappe
from kms.healthcare import calculate_patient_age
from frappe.utils import getdate, today, nowdate, nowtime, now

def patient_appointment_after_insert(doc, method=None):
  ################Doctype: Patient Appointment################
  #_clone_temporary_registration_questionnaire(doc.name, doc.custom_temporary_registration)
  if doc.custom_temporary_registration:
    frappe.db.set_value(
      'Temporary Registration', 
      doc.custom_temporary_registration, 
      {'patient_appointment': doc.name, 'status': 'Transferred'})
  _set_completed_questionnaire_status(doc.name)
  if doc.custom_temporary_registration:
    _set_questionnaire_key(doc.name, doc.custom_temporary_registration)
  doc.patient_age = calculate_patient_age(doc.custom_patient_date_of_birth, doc.appointment_date)
#  doc.save()

def patient_appointment_on_update(doc, method=None):
  ################Doctype: Patient Appointment################
  if not doc.status:
    doc.status = 'Open'
  if doc.status == 'Checked In' or doc.status == 'Ready to Check Out':
    validate_with_today_date(doc.appointment_date)
    if str(doc.appointment_date) == nowdate():
      if doc.appointment_type == 'MCU':
        dispatcher_user = frappe.db.get_value(
          "Dispatcher Settings", 
          {"branch": doc.custom_branch, 'enable_date': doc.appointment_date}, 
          ['dispatcher'])
        if not doc.custom_queue_no:
          _set_mcu_queue_no(doc.name)
        # Update Completed Questionnaire when there's additional mcu item
        previous_doc = doc.get_doc_before_save()
        if not previous_doc:
          return
        previous_row_count = len(previous_doc.custom_additional_mcu_items)
        current_row_count = len(doc.custom_additional_mcu_items)
        if current_row_count > previous_row_count:
          _set_completed_questionnaire_status(doc.name)
        additional = [row for row in doc.custom_additional_mcu_items if row.status == 'To be Added']
        if additional:
          exist_docname = frappe.db.get_value(
            'Dispatcher', {'patient_appointment': doc.name}, ['name'])
          if exist_docname:
            _add_dispatcher_additional_mcu_item(
              exist_docname, additional, dispatcher_user)
          else:
            _add_queue_pooling_additional_mcu_item(doc.name, doc.custom_branch, additional)
        else:
          if dispatcher_user:
            _create_dispatcher(doc.name, doc.custom_branch, doc.custom_mcu_exam_items)
          else:
            _create_mcu_queue_pooling(doc.name, doc.custom_branch)
      else:
        vs_doc = frappe.get_doc(dict(
          doctype = 'Vital Signs',
          patient = doc.patient,
          signs_date = nowdate(),
          signs_time = nowtime(),
          appointment = doc.name,
          custom_branch = doc.custom_branch,
          custom_patient_sex = doc.patient_sex,
          custom_patient_age = doc.patient_age,
          custom_patient_company = doc.custom_patient_company,
          custom_date_of_birth = doc.custom_patient_date_of_birth,
          vital_signs_note = doc.notes))
        vs_doc.insert(ignore_permissions=True)

def _add_dispatcher_additional_mcu_item(dispatcher, additional_table, dispatcher_user):
  doc = frappe.get_doc('Dispatcher', dispatcher)
  if doc.status == 'Finished':
    doc.status = 'In Queue'
  for entry in additional_table:
    # add new line to package
    new_entry = entry.as_dict()
    new_entry.name = None
    new_entry.parentfield = 'package'
    new_entry.parenttype = 'Dispatcher'
    new_entry.parent = doc.name
    doc.append('package', new_entry)
    # find related room to added item
    rooms = frappe.get_all(
      'Item Group Service Unit', 
      filters={'parent': entry.examination_item, 'branch': doc.branch}, 
      pluck='service_unit'
    )
    found = False
    row_counter = row_founder = 0
    for hsu in doc.assignment_table:
      row_counter += 1
    # update if there are already room 
      if hsu.healthcare_service_unit in rooms:
        hsu.status = 'Additional or Retest Request'
        found = True
      else:
        row_founder += 1
    # add if room previously not there
    if not found and row_founder == row_counter:
      for room in rooms:
        reference_doctype = frappe.db.get_value(
          'Healthcare Service Unit', room, 'custom_default_doctype')
        new_entry = dict()
        new_entry['name'] = None
        new_entry['healthcare_service_unit'] = room
        new_entry['status'] = 'Wait for Room Assignment'
        new_entry['reference_doctype'] = reference_doctype if reference_doctype else None
        doc.append('assignment_table', new_entry)
    # create notification for dispatcher user
    notification_doc = frappe.new_doc('Notification Log')
    notification_doc.for_user = dispatcher_user
    notification_doc.from_user = frappe.session.user
    notification_doc.document_type = 'Dispatcher'
    notification_doc.document_name = doc.name
    notification_doc.subject = f"""Patient <strong>{doc.patient_name}</strong> has """\
      f"""added additional MCU examination item: {entry.item_name}."""
    notification_doc.insert(ignore_permissions=True)
  doc.save(ignore_permissions=True)

def _create_dispatcher(exam_id, branch, item_table):
  doc = frappe.get_doc({
    'doctype': 'Dispatcher',
    'patient_appointment': exam_id,
    'date': today(),
    'status': 'In Queue'
  })
  item_with_sort_order = []
  for entry in item_table:
    sort_order = frappe.db.get_value(
      'Item', entry.examination_item, 'custom_bundle_position')
    item_with_sort_order.append({
      'item_code': entry.examination_item,
      'item_name': entry.item_name,
      'item_group': entry.item_group,
      'healthcare_service_unit': entry.healthcare_service_unit,
      'status': entry.status,
      'sort_order': sort_order
    })
  sorted_items = sorted(item_with_sort_order, key=lambda x: x['sort_order'])
  for item in sorted_items:
    new_entry = dict()
    new_entry['examination_item'] = item['item_code']
    new_entry['item_name'] = item['item_name']
    new_entry['item_group'] = item['item_group']
    new_entry['healthcare_service_unit'] = item['healthcare_service_unit']
    new_entry['status'] = item['status']
    doc.append('package', new_entry)
  rooms = frappe.db.sql("""
    SELECT distinct tigsu.service_unit, 
    thsu.custom_default_doctype, thsu.custom_reception_room
    FROM `tabItem Group Service Unit` tigsu, `tabHealthcare Service Unit` thsu 
    WHERE tigsu.branch = %s
    AND tigsu.parenttype = 'Item'
    AND tigsu.service_unit = thsu.name 
    AND EXISTS (
      SELECT 1 FROM `tabMCU Appointment` tma
      WHERE tma.parenttype = 'Patient Appointment'
      AND tma.parent = %s
      AND tma.examination_item = tigsu.parent)
    ORDER BY thsu.custom_room, thsu.custom_default_doctype""", (branch, doc.patient_appointment), as_dict=1)
  for room in rooms:
    new_entry = dict()
    new_entry['name'] = None
    new_entry['healthcare_service_unit'] = room.service_unit
    new_entry['status'] = 'Wait for Room Assignment'
    new_entry['reference_doctype'] = room.custom_default_doctype
    doc.append('assignment_table', new_entry)
    if room.custom_default_doctype == 'Sample Collection':
      if not any(
        row.get('healthcare_service_unit') == room.custom_default_doctype 
        for row in doc.assignment_table):
        new_entry = dict()
        new_entry['name'] = None
        new_entry['healthcare_service_unit'] = room.custom_reception_room
        new_entry['status'] = 'Wait for Sample'
        doc.append('assignment_table', new_entry)
  doc.save(ignore_permissions=True)

def _create_queue_pooling_record(appointment, service_unit, status, reference_doctype=None):
  doc_data = {
    'doctype': 'MCU Queue Pooling',
    'patient_appointment': appointment.name,
    'appointment_type': appointment.appointment_type,
    'patient': appointment.patient,
    'company': appointment.company,
    'priority': appointment.custom_priority,
    'branch': appointment.custom_branch,
    'date': today(),
    'arrival_time': nowtime(),
    'service_unit': service_unit,
    'status': status
  }
  if reference_doctype:
    doc_data['reference_doctype'] = reference_doctype
  doc = frappe.get_doc(doc_data)
  doc.save(ignore_permissions=True)

def _create_mcu_queue_pooling(exam_id, branch):
  rooms = frappe.db.sql("""
    SELECT distinct tigsu.service_unit, 
    thsu.custom_default_doctype, thsu.custom_reception_room
    FROM `tabItem Group Service Unit` tigsu, `tabHealthcare Service Unit` thsu 
    WHERE tigsu.branch = %s
    AND tigsu.parenttype = 'Item'
    AND tigsu.service_unit = thsu.name 
    AND EXISTS (
      SELECT 1 FROM `tabMCU Appointment` tma
      WHERE tma.parenttype = 'Patient Appointment'
      AND tma.parent = %s
      AND tma.examination_item = tigsu.parent)
    ORDER BY thsu.custom_room, thsu.custom_default_doctype""", (branch, exam_id), as_dict=1)
  pa = frappe.get_doc('Patient Appointment', exam_id)
  for room in rooms:
    _create_queue_pooling_record(
      pa, room.service_unit, 'Wait for Room Assignment', room.custom_default_doctype)
    if room.custom_default_doctype == 'Sample Collection':
      _create_queue_pooling_record(
        pa, room.custom_reception_room, 'Wait for Sample')

def _add_queue_pooling_additional_mcu_item(exam_id, branch, additional):
  items = list(set(item.get('examination_item') for item in additional))
  rooms = frappe.db.get_all(
    'Item Group Service Unit',
    filters={'parent': ['in', items], 'branch': branch},
    pluck='service_unit'
  )
  for room in rooms:
    qp = frappe.db.get_value(
      'MCU Queue Pooling', {'appointment': exam_id, 'service_unit': room}, 'name')
    if qp:
      frappe.db.set_value('MCU Queue Pooling', qp, 'status', 'Additional or Retest Request')
    else:
      doctype = frappe.db.get_value('Healthcare Service Unit', room, 'custom_default_doctype')
      pa = frappe.get_doc('Patient Appointment', exam_id)
      _create_queue_pooling_record(pa, room, 'Additional or Retest Request', doctype)

def patient_encounter_on_trash(doc, method=None):
  ################Doctype: Patient Encounter################
  if doc.custom_queue_pooling:
    qp = frappe.get_doc("Queue Pooling", doc.custom_queue_pooling)
    qp.status = "Queued"
    qp.dequeue_time = None
    qp.encounter = None
    qp.healthcare_practitioner = None
    qp.save(ignore_permissions=True)

def patient_encounter_after_insert(doc, method=None):
  ################Doctype: Patient Encounter################
  if doc.custom_queue_pooling:
    qp = frappe.get_doc("Queue Pooling", doc.custom_queue_pooling)
    qp.status = "Ongoing"
    qp.dequeue_time = nowtime()
    qp.encounter = doc.name
    qp.healthcare_practitioner = doc.practitioner
    qp.save(ignore_permissions=True)
    vs = doc.custom_vital_signs
    frappe.db.set_value('Vital Signs', vs, 'encounter', doc.name)

def patient_encounter_on_submit(doc, method=None):
  ################Doctype: Patient Encounter################
  if doc.custom_queue_pooling:
    qp = frappe.get_doc("Queue Pooling", doc.custom_queue_pooling)
    qp.status = "Closed"
    qp.save(ignore_permissions=True)

def patient_encounter_validate(doc, method=None):
  ################Doctype: Patient Encounter################
  if doc.custom_radiology:
    for radiology in doc.custom_radiology:
      if not radiology.status_time:
        radiology.status_time = now()

def patient_encounter_on_update(doc, method=None):
  ################Doctype: Patient Encounter################
  if doc.docstatus == 1:
    frappe.db.set_value("Patient Appointment", doc.appointment, "status", "Ready to Check Out")
  else:
    frappe.db.set_value("Patient Appointment", doc.appointment, "status", doc._appointment_status)

def patient_encounter_before_safe(doc, method=None):
  ################Doctype: Patient Encounter################
  doc._appointment_status = frappe.db.get_value('Patient Appointment', doc.appointment, 'status')

def prescription_duration_autoname(doc, method=None):
  ################Doctype: Prescription Duration################
  doc.name = 'Mix ' + doc.custom_uom + ' ' + str(doc.number)

def vital_signs_before_submit(doc, method=None):
  ################Doctype: Vital Signs################
  validate_with_today_date(doc.signs_date)
  appt = frappe.get_doc('Patient Appointment', doc.appointment)
  process_non_mcu(doc, appt, appt.appointment_for)
  validate_vs_mandatory_fields(doc, ['temperature', 'pulse', 'bp_systolic', 'bp_diastolic'])

def patient_before_save(doc, method=None):
  ################Doctype: Patient################
  doc.custom_age = calculate_patient_age(getdate(doc.dob), getdate(today()))

def validate_with_today_date(validate_date):
  if str(validate_date) != today():
    frappe.throw(
      title = 'Error', 
      msg=f"Date {validate_date} must be the same as today's date {today()}.", 
      exc='ValidationError')
    
def validate_vs_mandatory_fields(doc, fields):
  for field in fields:
    label = doc.meta.get_field(field).label
    if not doc.get(field):
      frappe.throw(title=f"{label} is Missing", msg=f"{label} is mandatory.")

def process_non_mcu(doc, appt, type):
  frappe.get_doc(dict(
    doctype = 'Queue Pooling',
    appointment = doc.appointment,
    appointment_type = appt.appointment_type,
    patient = doc.patient,
    date = nowdate(),
    arrival_time = nowtime(),
    status = 'Queued',
    priority = appt.custom_priority,
    vital_sign = doc.name,
    company = doc.company,
    department = appt.department if type == 'Department' else None,
    service_unit = appt.service_unit if type == 'Service Unit' else None,
    branch = doc.custom_branch,
    note = doc.vital_signs_note)).insert(ignore_permissions=True)

#def _clone_temporary_registration_questionnaire(name, temp_reg):
#  if temp_reg:
#    details = frappe.get_all(
#      'Questionnaire Detail', fields=["*"], ignore_permissions=True, order_by='idx asc',
#      filters={"parent": temp_reg})
#    for detail in details:
#      detail_dict = {k: v for k, v in detail.items() if k not in ("name", "parent", "parenttype", "parentfield", "idx")}
#      detail_dict.update({
#        'parent': name,
#        'parenttype': 'Patient Appointment',
#        'parentfield': 'custom_questionnaire_detail',
#        'doctype': 'Questionnaire Detail'})
#      frappe.db.insert(detail_dict, commit=False)
#    frappe.db.commit()

def _set_completed_questionnaire_status(name):
  sql = """SELECT name, (SELECT IF(count(*)>0,1,0) FROM `tabQuestionnaire Detail` tqd 
    WHERE tqd.parent = %(name)s AND tqd.template = tqt.name) completed
    FROM `tabQuestionnaire Template` tqt
    WHERE (EXISTS (SELECT 1 FROM `tabPatient Appointment` tpa WHERE tpa.name = %(name)s 
      AND tpa.appointment_type = tqt.appointment_type)
    OR EXISTS (SELECT 1 FROM `tabMCU Appointment` tma WHERE tma.parent = %(name)s 
      AND tma.examination_item = tqt.item_code))
    AND active = 1 AND (internal_questionnaire = 0 OR internal_questionnaire IS NULL)"""
  templates = frappe.db.sql(sql, {'name': name}, as_dict=True)
  if templates:
    frappe.db.delete('Questionnaire Completed', {'parent': name})
    for template in templates:
      doc = frappe.get_doc({
        'doctype': 'Questionnaire Completed',
        'parent': name,
        'parentfield': 'custom_completed_questionnaire',
        'parenttype': 'Patient Appointment',
        'template': template.name,
        'is_completed': template.completed,
        'status': 'Completed' if template.completed else 'Started'
      })
      doc.db_insert()

def _set_mcu_queue_no(name):
  custom_queue_no = frappe.db.get_all(
    'Patient Appointment', 
    filters={
      'company': 'Kyoai Medical Services',
      'custom_branch': 'Jakarta Main Clinic', 
      'appointment_date': today(),
      'appointment_type': 'MCU'
    },
    fields=['max(custom_queue_no)+1 as maks'],
    pluck='maks'
  )[0]
  frappe.db.set_value('Patient Appointment', name, 'custom_queue_no', custom_queue_no)

def _set_questionnaire_key(name, temp_reg):
  q_list = frappe.db.get_all('Questionnaire', filters={'temporary_registration': temp_reg}, pluck='name')
  for q in q_list:
    frappe.db.set_value('Questionnaire', q, 'patient_appointment', name)
