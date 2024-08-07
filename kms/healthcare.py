import frappe
from frappe.utils import today

@frappe.whitelist()
def get_mcu_settings():
  doc_exam_settings = frappe.db.sql("""
    SELECT field, value FROM tabSingles 
    WHERE doctype = 'MCU Settings' 
    AND field IN ('phallen_test_name', 'physical_examination_name', 'rectal_test_name', 'romberg_test_name', 'tinnel_test_name', 'visual_field_test_name')
    """, as_dict=True)
  return doc_exam_settings

@frappe.whitelist()
def get_exam_items(root):
  exam_items_query = """
  SELECT name, item_name, item_group, custom_bundle_position
  FROM tabItem ti
  WHERE EXISTS (
    WITH RECURSIVE ItemHierarchy AS (
      SELECT name, parent_item_group, is_group, custom_bundle_position
      FROM `tabItem Group`
      WHERE parent_item_group = %s
      UNION ALL
      SELECT t.name, t.parent_item_group, t.is_group, t.custom_bundle_position
      FROM `tabItem Group` t
      INNER JOIN ItemHierarchy ih ON t.parent_item_group = ih.name
    )
    SELECT name FROM ItemHierarchy
    WHERE name = ti.item_group AND is_group = 0 AND ti.custom_is_mcu_item = 1
  );
  """
  exam_group_query = """
  WITH RECURSIVE Hierarchy AS (
    SELECT name, parent_item_group, custom_bundle_position, is_group, 0 AS level
    FROM `tabItem Group`
    WHERE name = %s
    UNION ALL
    SELECT t.name, t.parent_item_group, t.custom_bundle_position, t.is_group, h.level + 1 AS level
    FROM `tabItem Group` t
    INNER JOIN Hierarchy h ON t.parent_item_group = h.name
  )
  SELECT name, parent_item_group, custom_bundle_position, is_group
  FROM Hierarchy
  WHERE name != %s
  ORDER BY level, custom_bundle_position;
  """
  exam_items = frappe.db.sql(exam_items_query, (root,), as_dict=True)
  exam_group = frappe.db.sql(exam_group_query, (root, root), as_dict=True)  
  return {'exam_items': exam_items, 'exam_group': exam_group}

@frappe.whitelist()
def create_service(name, room):
  service_unit_type = frappe.db.get_value('Healthcare Service Unit', room, 'service_unit_type')
  target = frappe.db.get_value('Healthcare Service Unit Type', service_unit_type, 'custom_default_doctype')
  target_map = {
    'Nurse Examination': create_nurse_exam,
    'Doctor Examination': create_doctor_exam,
    'Radiology': create_radiology_exam,
    'Sample Collection': create_sample_collection
  }
  if target in target_map:
    result = target_map[target](name, room)
    if result:
      return result
    else:
      frappe.throw("Failed to create service.")
  else:
    frappe.throw(f"Unsupported target: {target}")


@frappe.whitelist()
def remove_from_room(name, room):
  doc = frappe.get_doc('Dispatcher', name)
  for hsu in doc.assignment_table:
    if hsu.healthcare_service_unit == room:
      if hsu.status == 'Waiting to Enter the Room':
        doc_type = hsu.reference_doctype
        doc_name = hsu.reference_doc
        doc.status = 'In Queue'
        doc.room = ''
        hsu.status = 'Wait for Room Assignment'
        hsu.reference_doctype = ''
        hsu.reference_doc = ''
        doc.save(ignore_permissions=True)
        exam_doc = frappe.get_doc(doc_type, doc_name)
        if doc_type == 'Sample Collection':
          exam_doc.custom_status = 'Removed'
          for sample in exam_doc.custom_sample_table:
            sample.status = 'Started'
        else:
          exam_doc.status = 'Removed'
          for exam_item in exam_doc.examination_item:
            exam_item.status = 'Started'
        exam_doc.save(ignore_permissions=True)
        frappe.db.set_value(doc_type, doc_name, 'docstatus', '2')
        return {'docname': doc_name}
      else:
        frappe.throw(f"Cannot remove from room, because server status of room: {room} is {hsu.status}.")

@frappe.whitelist()
def retest(name, room):
  doc = frappe.get_doc('Dispatcher', name)
  allowed_status = {'Refused','Finished','Rescheduled','Partial Finished'}
  hsu_exist = False
  package_exist = False
  for hsu in doc.assignment_table:
    if hsu.healthcare_service_unit == room:
      if hsu.status in allowed_status:
        hsu.status = 'Wait for Room Assignment'
        hsu.reference_doctype = ''
        hsu.reference_doc = ''
        hsu_exist = True
        if doc.status != 'In Queue':
          doc.status = 'In Queue'
          doc.room = ''
      else:
        frappe.throw(f"Cannot make patient retest, because server status of room: {room} is {hsu.status}.")
  service_unit_type = frappe.db.get_value('Healthcare Service Unit', room, 'service_unit_type')
  target = frappe.db.get_value('Healthcare Service Unit Type', service_unit_type, 'custom_default_doctype')
  match target:
    case 'Nurse Examination':
      template_doctype = 'Nurse Examination Template'
    case 'Doctor Examination':
      template_doctype = 'Doctor Examination Template'
    case 'Radiology':
      template_doctype = 'Radiology Result Template'
    case 'Sample Collection':
      template_doctype = 'Lab Test Template'
    case _:
      frappe.throw(f"Undefined Default Doctype for room: {room}.")
  if (template_doctype != 'Lab Test Template'):
    exam_items = fetch_exam_items(name, room, doc.branch, template_doctype)
    for package_item in doc.package:
      for exam_item in exam_items:
        if package_item.examination_item == exam_item.item_code:
          package_item.status = 'Started'
          package_exist = True
  else:
    query = f"""
      SELECT examination_item AS item_code
      FROM `tabMCU Appointment` tma
      INNER JOIN `tabLab Test Template` tnet ON tnet.lab_test_code = tma.examination_item
      INNER JOIN `tabItem Group Service Unit` tigsu ON tigsu.parent = tma.examination_item
      WHERE tma.parenttype = 'Dispatcher'
      AND tma.parentfield = 'package'
      AND tma.parent = '{name}'
      AND tigsu.parenttype = 'Item'
      AND tigsu.parentfield = 'custom_room'
      AND tigsu.branch = '{doc.branch}'
      AND tigsu.service_unit = '{room}'
      """
    exam_items = frappe.db.sql(query, as_dict=True)
    for package_item in doc.package:
      for exam_item in exam_items:
        if package_item.examination_item == exam_item.item_code:
          package_item.status = 'Started'
          package_exist = True
  if hsu_exist and package_exist:
    doc.save(ignore_permissions=True)
    return {'docname': doc.name}

@frappe.whitelist()
def refuse_to_test(name, room):
  doc = frappe.get_doc('Dispatcher', name)
  hsu_exist = False
  package_exist = False
  for hsu in doc.assignment_table:
    if hsu.healthcare_service_unit == room:
      if hsu.status == 'Wait for Room Assignment':
        hsu.status = 'Refused'
        hsu_exist = True
      else:
        frappe.throw(f"Cannot make patient refuse to test, because server status of room: {room} is {hsu.status}.")
  service_unit_type = frappe.db.get_value('Healthcare Service Unit', room, 'service_unit_type')
  target = frappe.db.get_value('Healthcare Service Unit Type', service_unit_type, 'custom_default_doctype')
  match target:
    case 'Nurse Examination':
      template_doctype = 'Nurse Examination Template'
    case 'Doctor Examination':
      template_doctype = 'Doctor Examination Template'
    case 'Radiology':
      template_doctype = 'Radiology Result Template'
    case 'Sample Collection':
      template_doctype = 'Lab Test Template'
    case _:
      frappe.throw(f"Undefined Default Doctype for room: {room}.")
  if (template_doctype != 'Lab Test Template'):
    exam_items = fetch_exam_items(name, room, doc.branch, template_doctype)
    for package_item in doc.package:
      for exam_item in exam_items:
        if package_item.examination_item == exam_item.item_code:
          package_item.status = 'Refused'
          package_exist = True
  else:
    query = f"""
      SELECT examination_item AS item_code
      FROM `tabMCU Appointment` tma
      INNER JOIN `tabLab Test Template` tnet ON tnet.lab_test_code = tma.examination_item
      INNER JOIN `tabItem Group Service Unit` tigsu ON tigsu.parent = tma.examination_item
      WHERE tma.parenttype = 'Dispatcher'
      AND tma.parentfield = 'package'
      AND tma.parent = '{name}'
      AND tigsu.parenttype = 'Item'
      AND tigsu.parentfield = 'custom_room'
      AND tigsu.branch = '{doc.branch}'
      AND tigsu.service_unit = '{room}'
      """
    exam_items = frappe.db.sql(query, as_dict=True)
    for package_item in doc.package:
      for exam_item in exam_items:
        if package_item.examination_item == exam_item.item_code:
          package_item.status = 'Refused'
          package_exist = True
  if hsu_exist and package_exist:
    doc.save(ignore_permissions=True)
    return {'docname': doc.name}

def fetch_exam_items(name, room, branch, template_doctype):
  common_conditions = """INNER JOIN `tabItem Group Service Unit` tigsu ON tigsu.parent = tma.examination_item
    WHERE tma.parenttype = 'Dispatcher'
    AND tma.parentfield = 'package'
    AND tma.parent = %s
    AND tigsu.parenttype = 'Item'
    AND tigsu.parentfield = 'custom_room'
    AND tigsu.branch = %s
    AND tigsu.service_unit = %s"""

  if template_doctype == 'Lab Test Template':
    query = f"""
    SELECT sample, SUM(sample_qty) qty
    FROM `tab{template_doctype}` tltt
    WHERE EXISTS (
      SELECT 1
      FROM `tabMCU Appointment` tma
      INNER JOIN `tab{template_doctype}` tnet ON tnet.lab_test_code = tma.examination_item
      {common_conditions}
      AND tnet.name = tltt.name)
    """
  else:
    query = f"""
    SELECT tma.item_name AS name, tma.examination_item AS item_code
    FROM `tabMCU Appointment` tma
    INNER JOIN `tab{template_doctype}` tnet ON tnet.item_code = tma.examination_item
    {common_conditions}
    """
  return frappe.db.sql(query, (name, branch, room), as_dict=True)

def append_exam_results(doc, exam_items, template_doctype):
  for exam_item in exam_items:
    if template_doctype == 'Lab Test Template':
      doc.append('custom_sample_table', {'sample': exam_item.sample, 'quantity': exam_item.qty, 'status':'Started'})
    else:
      doc.append('examination_item', {'template': exam_item.name})
      template_doc = frappe.get_doc(template_doctype, exam_item.name)
      match template_doctype:
        case 'Nurse Examination Template':
          if template_doc.result_in_exam:
            selectives = template_doc.get('items')
            if selectives:
              for selective in selectives:
                doc.append('result', {
                  'result_line': selective.result_text,
                  'normal_value': selective.normal_value,
                  'result_check': selective.normal_value,
                  'item_code': exam_item.item_code,
                  'result_options': selective.result_select
                })
            non_selectives = template_doc.get('normal_items')
            if non_selectives:
              for non_selective in non_selectives:
                doc.append('non_selective_result', {
                  'test_name': non_selective.heading_text,
                  'test_event': non_selective.lab_test_event,
                  'test_uom': non_selective.lab_test_uom,
                  'min_value': non_selective.min_value,
                  'max_value': non_selective.max_value
                })
        case 'Doctor Examination Template':
          selectives = template_doc.get('items')
          if selectives:
            for selective in selectives:
              doc.append('result', {
                'result_line': selective.result_text,
                'normal_value': selective.normal_value,
                'result_check': selective.normal_value,
                'item_code': exam_item.item_code,
                'result_options': selective.result_select
              })
          non_selectives = template_doc.get('normal_items')
          if non_selectives:
            for non_selective in non_selectives:
              doc.append('non_selective_result', {
                'test_name': non_selective.heading_text,
                'test_event': non_selective.lab_test_event,
                'test_uom': non_selective.lab_test_uom,
                'min_value': non_selective.min_value,
                'max_value': non_selective.max_value
              })

def update_dispatcher_room_status(doc, room, doc_type, doc_name):
  for hsu in doc.assignment_table:
    if hsu.healthcare_service_unit == room:
      hsu.status = 'Waiting to Enter the Room'
      hsu.reference_doctype = doc_type
      hsu.reference_doc = doc_name
      doc.save(ignore_permissions=True)

def create_exam(name, room, doc_type, template_doctype):
  disp_doc = frappe.get_doc('Dispatcher', name)
  if disp_doc.status == 'In Room':
    frappe.throw(f"""Patient {disp_doc.patient} is already in a queue for {disp_doc.room} room.""")
  else:
    for hsu in disp_doc.assignment_table:
      if hsu.status in ['Waiting to Enter the Room', 'Ongoing Examination']:
        frappe.throw(f"""Patient {disp_doc.patient} is already in a queue for {hsu.healthcare_service_unit} room.""")
  appt_doc = frappe.get_doc('Patient Appointment', disp_doc.patient_appointment)
  doc_fields = {
    'doctype': doc_type,
    'custom_appointment' if doc_type == 'Sample Collection' else 'appointment': appt_doc.name,
    'patient': appt_doc.patient,
    'patient_name': appt_doc.patient_name,
    'patient_age': appt_doc.patient_age,
    'patient_sex': appt_doc.patient_sex,
    'company': appt_doc.company,
    'custom_branch' if doc_type == 'Sample Collection' else 'branch': appt_doc.custom_branch,
    'custom_dispatcher' if doc_type == 'Sample Collection' else 'dispatcher': name,
    'custom_service_unit' if doc_type == 'Sample Collection' else 'service_unit': room,
    'custom_document_date' if doc_type == 'Sample Collection' else 'created_date': today(),
    'custom_status' if doc_type == 'Sample Collection' else 'status': 'Started'
  }
  if doc_type != 'Sample Collection':
    doc_fields['expected_result_date'] = today()
  doc = frappe.get_doc(doc_fields)
  exam_items = fetch_exam_items(name, room, appt_doc.custom_branch, template_doctype)
  if not exam_items:
    frappe.throw("No Template found.")
  append_exam_results(doc, exam_items, template_doctype)
  doc.insert(ignore_permissions=True)
  update_dispatcher_room_status(disp_doc, room, doc_type, doc.name)
  return {'docname': doc.name}

def create_nurse_exam(name, room):
  return create_exam(name, room, 'Nurse Examination', 'Nurse Examination Template')

def create_doctor_exam(name, room):
  return create_exam(name, room, 'Doctor Examination', 'Doctor Examination Template')

def create_radiology_exam(name, room):
  return create_exam(name, room, 'Radiology', 'Radiology Result Template')

def create_sample_collection(name, room):
  return create_exam(name, room, 'Sample Collection', 'Lab Test Template')