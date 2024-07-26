import frappe
from frappe.utils import today

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
def create_service(target, source, name, room):
  target_map = {
    'Nurse Examination': create_nurse_exam,
    'Doctor Examination': create_doctor_exam,
    'Radiology': create_radiology_exam
  }
  
  if target in target_map:
    result = target_map[target](source, name, room)
    if result:
      return result
    else:
      frappe.throw("Failed to create service.")
  else:
    frappe.throw(f"Unsupported target: {target}")

def fetch_exam_items(name, room, branch, template_doctype):
  exam_items_query = f"""
  SELECT tnet.name, tnet.item_code 
  FROM `tabMCU Appointment` tma
  INNER JOIN `tabItem Group Service Unit` tigsu ON tigsu.parent = tma.examination_item
  INNER JOIN `{template_doctype}` tnet ON tnet.item_code = tma.examination_item
  WHERE tma.parenttype = 'Dispatcher'
    AND tma.parentfield = 'package'
    AND tma.parent = %s
    AND tigsu.parenttype = 'Item'
    AND tigsu.parentfield = 'custom_room'
    AND tigsu.branch = %s
    AND tigsu.service_unit = %s
  """
  return frappe.db.sql(exam_items_query, (name, branch, room), as_dict=True)

def append_exam_results(doc, exam_items, template_doctype):
  for exam_item in exam_items:
    doc.append('examination_item', {'template': exam_item.name})
    template_doc = frappe.get_doc(template_doctype, exam_item.name)
    
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

def create_exam(source, name, room, doc_type, template_doctype):
  if source != 'Dispatcher':
    frappe.throw(f"Unsupported source: {source}")

  appt = frappe.db.get_value('Dispatcher', name, 'patient_appointment')
  appt_doc = frappe.get_doc('Patient Appointment', appt)
  
  doc = frappe.get_doc({
    'doctype': doc_type,
    'appointment': appt_doc.name,
    'patient': appt_doc.patient,
    'patient_name': appt_doc.patient_name,
    'company': appt_doc.company,
    'branch': appt_doc.custom_branch,
    'dispatcher': name,
    'service_unit': room,
    'created_date': today(),
    'expected_result_date': today(),
    'status': 'Started'
  })
  
  exam_items = fetch_exam_items(name, room, appt_doc.custom_branch, template_doctype)
  
  if not exam_items:
    frappe.throw("No Template found.")
  
  append_exam_results(doc, exam_items, template_doctype)
  doc.insert()
  
  return {'docname': doc.name}

def create_nurse_exam(source, name, room):
  return create_exam(source, name, room, 'Nurse Examination', 'Nurse Examination Template')

def create_doctor_exam(source, name, room):
  return create_exam(source, name, room, 'Doctor Examination', 'Doctor Examination Template')

def create_radiology_exam(source, name, room):
  return create_exam(source, name, room, 'Radiology', 'Radiology Result Template')
