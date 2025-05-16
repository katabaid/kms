import frappe, re

def patient_appointment_after_insert(doc, method=None):
  ################Doctype: Patient Appointment################
  append_temporary_registration_questionnaire(doc)
  update_questionnaire_status(doc)
  doc.save()

def patient_appointment_on_update(doc, method=None):
  ################Doctype: Patient Appointment################
  if not doc.status:
    doc.status = 'Open'
  if doc.status == 'Checked In' or doc.status == 'Ready to Check Out':
    validate_with_today_date(doc.appointment_date)
    # prevent recursive call for updating questionnaire
    if getattr(doc.flags, "skip_on_update", False):
      return
    doc.flags.skip_on_update = True
    previous_doc = doc.get_doc_before_save()
    if not previous_doc:
      return
    previous_row_count = len(previous_doc.custom_additional_mcu_items)
    current_row_count = len(doc.custom_additional_mcu_items)
    if current_row_count > previous_row_count:
      update_questionnaire_status(doc)
      doc.appointment_time = frappe.utils.nowtime()
      doc.save()
    # END prevent recursive call for updating questionnaire
    if str(doc.appointment_date) == frappe.utils.nowdate():
      if doc.custom_temporary_registration:
        frappe.db.set_value(
          'Temporary Registration', 
          doc.custom_temporary_registration, 
          {'patient_appointment': doc.name, 'status': 'Transferred'})
      dispatcher_user = frappe.db.get_value(
        "Dispatcher Settings", 
        {"branch": doc.custom_branch, 'enable_date': doc.appointment_date}, 
        ['dispatcher'])
      if doc.appointment_type == 'MCU':
        additional = [row for row in doc.custom_additional_mcu_items if row.status == 'To be Added']
        if additional:
          if dispatcher_user:
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
          signs_date = frappe.utils.nowdate(),
          signs_time = frappe.utils.nowtime(),
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
      filters={'parent': entry.examination_item, 'branch': doc.custom_branch}, 
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
        new_entry['healthcare_service_unit'] = room.service_unit
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
    'date': frappe.utils.today(),
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
    ORDER BY thsu.custom_room, thsu.custom_default_doctype""", (branch, doc.exam_id), as_dict=1)
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
    'appointment': appointment.name,
    'appointment_type': appointment.appointment_type,
    'patient': appointment.patient,
    'company': appointment.company,
    'priority': appointment.custom_priority,
    'branch': appointment.custom_branch,
    'date': frappe.utils.today(),
    'arrival_time': frappe.utils.nowtime(),
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
    qp.dequeue_time = frappe.utils.nowtime()
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
        radiology.status_time = frappe.utils.now()

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

def validate_with_today_date(validate_date):
  if str(validate_date) != frappe.utils.today():
    frappe.throw(
      title = 'Error', 
      msg=f"Date {validate_date} must be the same as today's date {frappe.utils.today()}.", 
      exc='ValidationError')
    
def validate_vs_mandatory_fields(doc, fields):
  for field in fields:
    label = doc.meta.get_field(field).label
    if not doc.get(field):
      frappe.throw(title=f"{label} is Missing", msg=f"{label} is mandatory.")

#def process_mcu(doc, appt):
#  mcu = [item.examination_item for item in appt.custom_mcu_exam_items]
#  added_mcu = [item.examination_item for item in appt.custom_additional_mcu_items]
#  items_list = mcu + added_mcu
#  items = ', '.join(f'"{item}"' for item in items_list)
#  sql = f"""SELECT DISTINCT service_unit, thsu.custom_default_doctype 
#    FROM `tabItem Group Service Unit` tigsu, `tabHealthcare Service Unit` thsu 
#    WHERE parenttype = 'Item' AND parentfield = 'custom_room' AND parent IN ({items})
#    AND branch = '{doc.custom_branch}'  AND tigsu.service_unit = thsu.name"""
#  rooms = frappe.db.sql(sql, as_dict = True)
#  for room in rooms:
#    sql = f"""SELECT DISTINCT parent FROM `tabItem Group Service Unit` tigsu
#      WHERE service_unit = '{room.service_unit}'
#      AND parenttype = 'Item' AND parentfield = 'custom_room'
#      AND parent IN ({items})"""
#    exam_items = frappe.db.sql(sql, as_dict = True)
#    template_doctype = frappe.db.get_value(
#      'MCU Relationship',{'examination': room.custom_default_doctype}, 'template')
#    exam_doc = frappe.new_doc(room.custom_default_doctype)
#    exam_doc.patient = doc.patient
#    exam_doc.patient_name = appt.patient_name
#    exam_doc.patient_sex = appt.patient_sex
#    exam_doc.patient_age = appt.patient_age
#    exam_doc.company = doc.company
#    if room.custom_default_doctype == 'Sample Collection':
#      exam_doc.custom_branch = doc.custom_branch
#      exam_doc.custom_status = 'Started'
#      exam_doc.custom_document_date = frappe.utils.nowdate()
#      exam_doc.custom_appointment = doc.appointment
#      exam_doc.custom_service_unit = room.service_unit
#      exam_doc.custom_queue_no = ''
#      pb = frappe.db.get_value(
#        'Product Bundle', 
#        appt.mcu, 
#        [
#          'custom_number_of_yellow_tubes', 
#          'custom_number_of_red_tubes', 
#          'custom_number_of_purple_tubes', 
#          'custom_number_of_blue_tubes'
#        ], 
#        as_dict = True)
#      exam_doc.custom_yellow_tubes = pb.custom_number_of_yellow_tubes
#      exam_doc.custom_red_tubes = pb.custom_number_of_red_tubes
#      exam_doc.custom_purple_tubes = pb.custom_number_of_purple_tubes
#      exam_doc.custom_blue_tubes = pb.custom_number_of_blue_tubes
#    else:  
#      exam_doc.branch = doc.custom_branch
#      exam_doc.status = 'Started'
#      exam_doc.queue_no = ''
#      exam_doc.appointment = doc.appointment
#      exam_doc.service_unit = room.service_unit
#      exam_doc.created_date = frappe.utils.nowdate()
#    exam_doc.examination_item = []
#    exam_doc.result = []
#    exam_doc.non_selective_result = []
#    exam_doc.custom_examination_item = []
#    exam_doc.custom_sample_table = []
#    existing_samples = []
#    for exam_item in exam_items:
#      template_name = frappe.get_all(
#        template_doctype, filters = {'item_code': exam_item.parent},  pluck = 'name')
#      if template_name:
#        template = frappe.get_doc(template_doctype, template_name[0])
#        if template:
#          if room.custom_default_doctype == 'Sample Collection':
#            entries = dict()
#            entries['template'] = template.name
#            entries['item_code'] = exam_item.parent
#            exam_doc.append('custom_examination_item', entries) 
#            if template.sample not in existing_samples:
#              samples = dict()
#              samples['sample'] = template.sample
#              exam_doc.append('custom_sample_table', samples)
#              existing_samples.append(template.sample)
#          else:
#            entries = dict()
#            entries['template'] = template.name
#            entries['status'] = 'Started'
#            entries['status_time'] = frappe.utils.now()
#            exam_doc.append('examination_item', entries)
#            if (room.custom_default_doctype == 'Nurse Examination' 
#                or room.custom_default_doctype == 'Doctor Examination'):
#              if ((hasattr(template, 'result_in_exam') and template.result_in_exam)
#                or room.custom_default_doctype == 'Doctor Examination'):
#                for result in template.items:
#                  entries = dict()
#                  entries['item_code'] = exam_item.parent
#                  entries['item_name'] = template.item_name
#                  entries['result_line'] = result.result_text
#                  entries['normal_value'] = result.normal_value
#                  entries['mandatory_value'] = result.mandatory_value
#                  entries['result_options'] = result.result_select
#                  exam_doc.append('result', entries)
#                for non_selective_result in template.normal_items:
#                  match = re.compile(r'(\d+) Years?').match(appt.patient_age)
#                  age = int(match.group(1)) if match else None
#                  if appt.patient_sex == non_selective_result.sex and non_selective_result >= age:
#                    entries = dict()
#                    entries['item_code'] = exam_item.parent
#                    entries['test_name'] = non_selective_result.heading_text
#                    entries['test_event'] = non_selective_result.lab_test_event
#                    entries['test_uom'] = non_selective_result.lab_test_uom
#                    entries['min_value'] = non_selective_result.min_value
#                    entries['max_value'] = non_selective_result.max_value
#                    exam_doc.append('non_selective_result', entries)
#    exam_doc.insert(ignore_permissions=True)

def process_non_mcu(doc, appt, type):
  frappe.get_doc(dict(
    doctype = 'Queue Pooling',
    appointment = doc.appointment,
    appointment_type = appt.appointment_type,
    patient = doc.patient,
    date = frappe.utils.nowdate(),
    arrival_time = frappe.utils.nowtime(),
    status = 'Queued',
    priority = appt.custom_priority,
    vital_sign = doc.name,
    company = doc.company,
    department = appt.department if type == 'Department' else None,
    service_unit = appt.service_unit if type == 'Service Unit' else None,
    branch = doc.custom_branch,
    note = doc.vital_signs_note)).insert(ignore_permissions=True)

def update_questionnaire_status(doc):
  # Prevent recursion by checking doc.flags
  if getattr(doc.flags, "update_called", False):
    return
  doc.flags.update_called = True
  doc.set("custom_completed_questionnaire", [])
  if doc.appointment_type:
    questionnaire_templates = frappe.db.sql("""
        SELECT name, template_name FROM `tabQuestionnaire Template`
        WHERE appointment_type = %s 
          AND active = 1 
          AND internal_questionnaire = 0 
          AND item_code IS NULL
        ORDER BY priority
    """, (doc.appointment_type,), as_dict=True)
    
    for questionnaire in questionnaire_templates:
      # Append to custom_completed_questionnaire
      is_completed = 0
      if any(
        detail.template == questionnaire["template_name"] 
        for detail in doc.custom_questionnaire_detail):
        is_completed = 1
      
      doc.append("custom_completed_questionnaire", {
        "template": questionnaire["template_name"],
        "is_completed": is_completed
      })
  completed_questionnaires = []
  child_tables = ["custom_mcu_exam_items", "custom_additional_mcu_items"]
  for table in child_tables:
    for row in doc.get(table):
      if row.examination_item:
        templates = frappe.get_all(
          "Questionnaire Template",
          filters={"item_code": row.examination_item, 'active': 1, 'internal_questionnaire': 0},
          fields=["template_name"]
        )
        for template_data in templates:
          is_completed = 0
          is_completed = 1 if any(
            detail.template == template_data["template_name"] 
            for detail in doc.custom_questionnaire_detail
          ) else None
          # Add to the completed_questionnaires list
          completed_questionnaires.append({
            "template": template_data["template_name"],
            "is_completed": is_completed
          })
  for completed in completed_questionnaires:
    if not any(
      q.template == completed["template"] 
      for q in doc.custom_completed_questionnaire):
      doc.append("custom_completed_questionnaire", completed)

def append_temporary_registration_questionnaire(doc):
  doc.set("custom_questionnaire_detail", [])
  if doc.custom_temporary_registration:
    temp_regis = frappe.get_doc('Temporary Registration', doc.custom_temporary_registration)
    for detail in temp_regis.detail:
      detail_dict = {
        k: v for k, v in detail.as_dict().items() 
        if k not in ('name', 'parent', 'parenttype', 'parentfield', 'idx')
      }
      doc.append('custom_questionnaire_detail', detail_dict)
