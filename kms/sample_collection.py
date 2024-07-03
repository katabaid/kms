import frappe, json
from frappe.utils import today

@frappe.whitelist()
def refuse_to_test(name, selected, reason):
  if isinstance(selected, str):
    selected = json.loads(selected)
  selected_name_values = [item['name'] for item in selected]
  sample_doc = frappe.get_doc('Sample Collection', name)
  count_row = 0
  count_refused = 0
  count_finished = 0
  # Tandai yang refusd di Sample Collection Bulk
  for sample_type in sample_doc.get('custom_sample_table'):
    count_row += 1
    if sample_type.status == 'Refused':
      count_refused += 1
    if sample_type.status == 'Finished':
      count_finished += 1
    if sample_type.name in selected_name_values:
      sample_type.status = 'Refused'
      count_refused += 1
  refuse_all = count_row == count_refused
  partial_finished = count_row == count_refused + count_finished
  if refuse_all:
    sample_doc.custom_status = 'Refused'
  elif partial_finished:
    sample_doc.collected_by = frappe.session.user
    sample_doc.collection_time = frappe.utils.now()
    sample_doc.custom_status = 'Partially Finished'
  sample_doc.save()
  # Cancel Sample Collection
  if refuse_all or partial_finished:
    frappe.db.set_value('Sample Collection', name, 'docstatus', '2')
  # Todo: Tandai exam item yang terpengaruh
  # Todo: Cancel Lab Test
  # Tandai yang refused di Dispatcher
  if sample_doc.custom_dispatcher:
    if refuse_all or partial_finished:
      dispatcher_doc = frappe.get_doc('Dispatcher', sample_doc.custom_dispatcher)
      dispatcher_doc.status = 'In Queue'
      for hsu in dispatcher_doc.get('assignment_table'):
        if hsu.healthcare_service_unit == sample_doc.custom_service_unit:
          hsu.status = 'Refused to Test'
      dispatcher_doc.save()
  # Notifikasi Dispatcher
    notification_doc = frappe.get_doc({
      'doctype': 'Notification Log',
      'for_user': frappe.db.get_value('Dispatcher Settings', {'branch': sample_doc.custom_branch, 'enable_date': today()}, 'dispatcher'),
      'type': 'Alert',
      'document_type': 'Sample Collection',
      'document_name': name,
      'from_user': frappe.session.user,
      'subject': f"""Patient {sample_doc.patient_name} refused to test with reason: {reason}."""
    })
    notification_doc.insert()
    comment_doc = frappe.get_doc({
      'doctype': 'Comment',
      'comment_type': 'Comment',
      'comment_by': frappe.session.user,
      'reference_doctype': 'Dispatcher',
      'reference_name': sample_doc.custom_dispatcher,
      'content': f"""Patient {sample_doc.patient_name} refused to test with reason: {reason}."""
    })
    comment_doc.insert()
  return 'success'

@frappe.whitelist()
def remove(name, reason):
  sample_doc = frappe.get_doc('Sample Collection', name)
  sample_doc.custom_status = 'Removed'
  for sample_type in sample_doc.get('custom_sample_table'):
    sample_type.status = 'Removed'
  sample_doc.save()
  frappe.db.set_value('Sample Collection', name, 'docstatus', '2')
  if sample_doc.custom_dispatcher:
    dispatcher_doc = frappe.get_doc('Dispatcher', sample_doc.custom_dispatcher)
    dispatcher_doc.status = 'In Queue'
    dispatcher_doc.room = ''
    for hsu in dispatcher_doc.get('assignment_table'):
      if hsu.healthcare_service_unit == sample_doc.custom_service_unit:
        hsu.status = 'Wait for Room Assignment'
        hsu.reference_doc = None
        hsu.reference_doctype = None
    dispatcher_doc.save()
    notification_doc = frappe.get_doc({
      'doctype': 'Notification Log',
      'for_user': frappe.db.get_value('Dispatcher Settings', {'branch': sample_doc.custom_branch, 'enable_date': today()}, 'dispatcher'),
      'type': 'Alert',
      'document_type': 'Sample Collection',
      'document_name': name,
      'from_user': frappe.session.user,
      'subject': f"""Patient {sample_doc.patient_name} removed from room with reason: {reason}."""
    })
    notification_doc.insert()
    comment_doc = frappe.get_doc({
      'doctype': 'Comment',
      'comment_type': 'Comment',
      'comment_by': frappe.session.user,
      'reference_doctype': 'Dispatcher',
      'reference_name': sample_doc.custom_dispatcher,
      'content': f"""Patient {sample_doc.patient_name} removed from room with reason: {reason}."""
    })
    comment_doc.insert()
  return 'success'

@frappe.whitelist()
def check_in(name):
  sample_doc = frappe.get_doc('Sample Collection', name)
  sample_doc.custom_status = 'Checked In'
  for sample_type in sample_doc.get('custom_sample_table'):
    sample_type.status = 'Checked In'
  sample_doc.save()

  if sample_doc.custom_dispatcher:
    dispatcher_doc = frappe.get_doc('Dispatcher', sample_doc.custom_dispatcher)
    dispatcher_doc.status = 'In Room'
    dispatcher_doc.room = sample_doc.custom_service_unit
    for hsu in dispatcher_doc.get('assignment_table'):
      if hsu.healthcare_service_unit == sample_doc.custom_service_unit:
        hsu.status = 'Ongoing Examination'
    dispatcher_doc.save()
  return 'success'

@frappe.whitelist()
def get_items():
  item_group = frappe.db.sql(f"""
    WITH RECURSIVE ItemHierarchy AS (
    SELECT name, parent_item_group, is_group
    FROM `tabItem Group` tig 
    WHERE parent_item_group = 'Laboratory'
    UNION ALL
    SELECT t.name, t.parent_item_group, t.is_group
    FROM `tabItem Group` t
    INNER JOIN ItemHierarchy ih ON t.parent_item_group = ih.name
    )
    SELECT name, parent_item_group, is_group
    FROM ItemHierarchy""", as_dict=True)
  item = frappe.db.sql(f"""
    SELECT tltt.name, tltt.item, tltt.lab_test_group FROM `tabLab Test Template` tltt
    WHERE EXISTS (SELECT 1 FROM tabItem ti WHERE tltt.item = ti.name) 
    AND EXISTS (SELECT 1 FROM (WITH RECURSIVE ItemHierarchy AS (
        SELECT name, parent_item_group, is_group
        FROM `tabItem Group` tig 
        WHERE parent_item_group = 'Laboratory'
        UNION ALL
        SELECT t.name, t.parent_item_group, t.is_group
        FROM `tabItem Group` t
        INNER JOIN ItemHierarchy ih ON t.parent_item_group = ih.name
    )  SELECT name, parent_item_group, is_group FROM ItemHierarchy) ih WHERE tltt.lab_test_group = ih.name)""", as_dict=True)
  return {'item_group': item_group, 'item': item}

@frappe.whitelist()
def create(doctype, name):
  def get_appointment_doc(doctype, name):
    if doctype == 'Patient Appointment':
      enc_doc = frappe.get_doc('Patient Encounter', name)
      return frappe.get_doc('Patient Appointment', enc_doc.appointment)
    elif doctype == 'Patient Encounter':
      appt = frappe.db.get_value('Dispatcher', name, 'patient_appointment')
      return frappe.get_doc('Patient Encounter', appt)
    else:
      return None

  appt_doc = get_appointment_doc(doctype, name)

  #how to determine service unit if more than 1 per branch is registered in item group (i.e. : usg male/usg female, sample1/sample2)

  sample_doc = frappe.get_doc({
    'doctype': 'Sample Collection',
    'custom_appointment': appt_doc.name,
    'patient': appt_doc.patient,
    'patient_name': appt_doc.patient_name,
    'patient_age': appt_doc.patient_age,
    'patient_sex': appt_doc.patient_sex,
    'company': appt_doc.company,
    'custom_branch': appt_doc.custom_branch,
    'custom_service_unit': lab,
    #'custom_lab_test': lab_doc.name,
    'custom_status': 'Started'
  })
