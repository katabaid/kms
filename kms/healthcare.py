import frappe, json
from frappe.utils import today

@frappe.whitelist()
def get_mcu_settings(is_item=False):
  base_fields = ['phallen_test', 'physical_examination', 'rectal_test', 'ecg',
    'romberg_test', 'tinnel_test', 'visual_field_test', 'dental_examination']
  fields = base_fields if is_item else [f'{f}_name' for f in base_fields]
  return frappe.db.sql(f"""
    SELECT field, value 
    FROM tabSingles
    WHERE doctype = 'MCU Settings'
    AND field IN ({', '.join(['%s']*len(fields))})
    """, tuple(fields), as_dict=True)

@frappe.whitelist()
def get_ecg(exam_id):
  return frappe.db.sql("""
    SELECT parent
    FROM `tabNurse Examination Request` tner
    WHERE parent IN (
      SELECT name FROM `tabNurse Examination` tne 
      WHERE tne.appointment = %s and tne.docstatus IN (0,1))
    AND template = (
      SELECT value FROM tabSingles ts WHERE doctype = 'MCU Settings' and `field` = 'ecg_name')
  """, (exam_id), as_dict=True)

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
    if hsu.healthcare_service_unit != room:
      continue
    if hsu.status != 'Waiting to Enter the Room':
      frappe.throw(f"Cannot remove from room, because server status of room: {room} is {hsu.status}.")
    doc_type = hsu.reference_doctype
    doc_name = hsu.reference_doc
    doc.status = 'In Queue'
    doc.room = ''
    hsu.status = 'Wait for Room Assignment'
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

@frappe.whitelist()
def exam_retest (name, item, item_name):
  disp_doc = get_dispatcher_doc (name)
  rooms = get_rooms_by_item_branch (item, disp_doc.branch)
  for room in rooms:
    temp_hsu_exist, temp_previous_doctype, temp_previous_docname = process_hsu (disp_doc, room.service_unit)
    if temp_hsu_exist:
      if disp_doc.status != 'In Queue':
        disp_doc.statue = 'In Queue'
        disp_doc.room = ''
      previous_doctype = temp_previous_doctype
      previous_docname = temp_previous_docname
      hsu_exist = temp_hsu_exist
    result_doctype, template_doctype = get_relationship(room.service_unit)
  sample = ''
  if template_doctype == 'Lab Test Template':
    sample = get_sample_from_template(item_name)
  exam_items = get_affected_exam_items_list (template_doctype, disp_doc, item_name, sample)
  if exam_items:
    for package_item in disp_doc.package:
      if package_item.item_name in [item for item in exam_items]:
        package_item.status = 'To Retest'
    pa_doc = frappe.get_doc('Patient Appointment', disp_doc.patient_appointment)
    for pa_mcu in pa_doc.custom_mcu_exam_items:
      if pa_mcu.item_name in [item for item in exam_items]:
        pa_mcu.status = 'To Retest'
    for pa_mcu_add in pa_doc.custom_additional_mcu_items:
      if pa_mcu_add.item_name in [item for item in exam_items]:
        pa_mcu_add.status = 'To Retest'
    pa_doc.save(ignore_permissions=True)
  if exam_items and hsu_exist:
    to_cancel_doc = get_cancelled_doc (previous_doctype, previous_docname)
    #if to_cancel_doc.docstatus == 1:
    if previous_doctype == 'Sample Collection':
      for cancel_item in to_cancel_doc.custom_sample_table:
        if cancel_item.sample == sample:
          frappe.db.set_value('Sample Collection Bulk', cancel_item.name, {'status': 'To Retest'})
      frappe.db.set_value(previous_doctype, previous_docname, {'docstatus': 2, 'custom_status': 'To Retest'})
      frappe.db.set_value(result_doctype, {'custom_sample_collection': previous_docname}, {'docstatus': 2})
      frappe.db.set_value('Sample Reception', {'sample_collection': previous_docname}, {'docstatus': 2})
    else:
      for cancel_item in to_cancel_doc.examination_item:
        if cancel_item.template == exam_items[0]:
          frappe.db.set_value(cancel_item.doctype, cancel_item.name, {'status': 'To Retest'})
      frappe.db.set_value(previous_doctype, previous_docname, {'docstatus': 2, 'status': 'To Retest'})
      if getattr(to_cancel_doc, 'exam_result', None):
        to_cancel_res = frappe.get_doc(result_doctype, to_cancel_doc.exam_result)
        frappe.db.set_value(result_doctype, to_cancel_res.name, {'docstatus': 2})
    if disp_doc.status == 'Waiting to Finish':
      disp_doc.status = 'In Queue'
    disp_doc.save(ignore_permissions=True)
    return {'docname': disp_doc.name}

def get_dispatcher_doc (name):
  return frappe.get_doc ('Dispatcher', name)

def get_rooms_by_item_branch (item, branch):
  return frappe.get_all('Item Group Service Unit', filters={'parent': item, 'branch': branch}, fields=['service_unit'])

def process_hsu (doc, room):
  allowed_status = {'Refused','Finished','Rescheduled','Partial Finished'}
  for hsu in doc.assignment_table:
    if hsu.healthcare_service_unit == room:
      if hsu.status in allowed_status:
        if hsu.reference_doc:
          hsu.status = 'Additional or Retest Request'
          return True, hsu.reference_doctype, hsu.reference_doc
        else:
          return False, None, None
      else:
        frappe.throw(f"Cannot make patient retest, because server status of room: {room} is {hsu.status}.")

def get_relationship(room):
  return frappe.get_all(
    'MCU Relationship', 
    filters={
      'examination': 
      frappe.db.get_value(
        'Healthcare Service Unit Type', 
        frappe.db.get_value('Healthcare Service Unit', room, 'service_unit_type'), 
        'custom_default_doctype'
      )
    }, 
    fields=['result', 'template'])[0].values()

def get_sample_from_template (item_name):
  return frappe.db.get_value('Lab Test Template', item_name, 'sample')

def get_affected_exam_items_list (template_doctype, doc, item_name = None, sample = None):
  if template_doctype == 'Lab Test Template':
    return list(set(frappe.get_all('Lab Test Template', filters={'sample':sample}, pluck='name')) & set(list(o.item_name for o in doc.package)))
  else:
    return [item_name]

def get_cancelled_doc (doctype, docname):
  return frappe.get_doc(doctype, docname)

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
  rel = frappe.get_all('MCU Relationship', filters={'examination': target}, fields=['result', 'template'])
  if rel:
    template_doctype = rel[0].template
  else:
    frappe.throw(f"Undefined Default Doctype for room: {room}.")
  if (template_doctype != 'Lab Test Template'):
    exam_items = fetch_exam_items(name, room, doc.branch, template_doctype)
    for package_item in doc.package:
      for exam_item in exam_items:
        if package_item.examination_item == exam_item.item_code:
          package_item.status = 'Refused'
          package_exist = True
  else:
    query = """
      SELECT examination_item AS item_code
      FROM `tabMCU Appointment` tma
      INNER JOIN `tabLab Test Template` tnet ON tnet.lab_test_code = tma.examination_item
      INNER JOIN `tabItem Group Service Unit` tigsu ON tigsu.parent = tma.examination_item
      WHERE tma.parenttype = 'Dispatcher'
      AND tma.parentfield = 'package'
      AND tma.parent = %s
      AND tigsu.parenttype = 'Item'
      AND tigsu.parentfield = 'custom_room'
      AND tigsu.branch = %s
      AND tigsu.service_unit = %s"""
    exam_items = frappe.db.sql(query, (name, doc.branch, room), as_dict=True)
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
    SELECT sample, SUM(sample_qty) qty FROM `tabMCU Appointment` tma
    INNER JOIN `tabLab Test Template` tnet ON tnet.lab_test_code = tma.examination_item
    {common_conditions}
    GROUP BY 1"""
  else:
    query = f"""
    SELECT tma.item_name AS name, tma.examination_item AS item_code, status
    FROM `tabMCU Appointment` tma
    INNER JOIN `tab{template_doctype}` tnet ON tnet.item_code = tma.examination_item
    {common_conditions}"""
  return frappe.db.sql(query, (name, branch, room), as_dict=True)

def append_exam_results(doc, exam_items, template_doctype, cancelled_doc = None):
  if template_doctype == 'Lab Test Template':
    sql = """
      SELECT examination_item, tma.item_name
      FROM `tabMCU Appointment` tma, tabItem ti
      WHERE tma.parent = %s
      AND EXISTS (SELECT 1 FROM `tabLab Test Template` tltt WHERE tltt.item = tma.examination_item)
      AND ti.name = tma.examination_item
      ORDER BY ti.custom_bundle_position
      """
    items = frappe.db.sql(sql, (doc.custom_dispatcher), as_dict=True)
    for item in items:
      doc.append('custom_examination_item', {
        'template': item.item_name,
        'item_code': item.examination_item,
      })
  for exam_item in exam_items:
    if template_doctype == 'Lab Test Template':
      if cancelled_doc:
        for sample in cancelled_doc.custom_sample_table:
          if sample.sample == exam_item.sample:
            doc.append(
              'custom_sample_table', 
              {
                'sample': sample.sample, 
                'quantity': sample.quantity, 
                'status': 'Started' if sample.status == 'To Retest' else sample.status,
                'uom': sample.uom,
                'status_time': sample.status_time if sample.status != 'To Retest' else ''})
      else:
        doc.append('custom_sample_table', {'sample': exam_item.sample, 'quantity': exam_item.qty, 'status': 'Started'})
    else:
      assigned_status = ''
      if cancelled_doc:
        cancelled_item_count = len(cancelled_doc.examination_item) 
        have_status = False
        for index, cancelled_item in enumerate(cancelled_doc.examination_item, start = 1):
          if cancelled_item.template == exam_item.name: 
            if cancelled_item.status == 'To Retest':
              doc.append('examination_item', {'template': exam_item.name, 'status': 'Started'})
              have_status = True
              assigned_status = 'Started'
            elif cancelled_item.status == 'Finished':
              doc.append(
                'examination_item', 
                {'template': exam_item.name, 'status': 'Finished', 'status_time': cancelled_item.status_time}
              )
              have_status = True
              assigned_status = 'Finished'
            else:
              pass
          if index == cancelled_item_count and not have_status:
            doc.append('examination_item', {'template': exam_item.name, 'status': 'Started'})
            assigned_status = 'Started'
      else:
        doc.append('examination_item', {'template': exam_item.name})
      template_doc = frappe.get_doc(template_doctype, exam_item.name)
      if template_doctype == 'Doctor Examination Template' or getattr(template_doc, 'result_in_exam', False):
        append_results (doc, template_doc, exam_item.item_code, cancelled_doc, assigned_status)

def append_results(doc, template_doc, item_code, cancelled_doc=None, assigned_status=None):
  is_cancelled = bool(cancelled_doc and assigned_status)
  is_finished = assigned_status == 'Finished' if is_cancelled else False
  for result_type in ['result', 'non_selective_result']:
    source_key = 'items' if result_type == 'result' else 'normal_items'
    if is_cancelled:
      source = cancelled_doc.get(result_type, [])
      if not is_finished:
        result_source = cancelled_doc.get('result', []) + cancelled_doc.get('non_selective_result', [])
        if not any(item.item_code == item_code for item in result_source):
          source = template_doc.get(source_key, [])
          is_cancelled = False
    else:
      source = template_doc.get(source_key, [])
    for item in source:
      if not is_cancelled or item.item_code == item_code:
        result = {'item_code': item.item_code if is_cancelled else item_code}
        if is_cancelled:
          cancelled_attr = ['item_name', 'result_line', 'result_check', 'test_name', 'test_event', 
          'test_uom', 'min_value', 'max_value', 'normal_value', 'result_options', 'mandatory_value']
          result.update({attr: getattr(item, attr, '') for attr in cancelled_attr})
          if is_finished:
            result['result_value'] = getattr(item, 'result_value', '')
          base_key = result_type.split('_')[0]
          result.update({
            'is_finished': is_finished, 
            f"{base_key}_value": getattr(item, f"{base_key}_value", '') if is_finished else ''})
            #result_type.split('_')[0] + '_value': getattr(item, result_type.split('_')[0] + '_value', '') if is_finished else ''})
        else:
          cancelled_pair = [
            ('result_line', 'result_text'),         ('normal_value', 'normal_value'), 
            ('mandatory_value', 'mandatory_value'), ('result_check', 'normal_value'), 
            ('result_options', 'result_select'),    ('test_name', 'heading_text'), 
            ('test_event', 'lab_test_event'),       ('test_uom', 'lab_test_uom'), 
            ('min_value', 'min_value'),             ('max_value', 'max_value')] 
          #result.update({new_key: getattr(item, old_key) for new_key, old_key in cancelled_pair if hasattr(item, old_key)})
          for new_key, old_key in cancelled_pair:
            if hasattr(item, old_key):
              result[new_key] = getattr(item, old_key)
        doc.append(result_type, result)

def update_dispatcher_room_status(doc, room, doc_type, doc_name):
  doc.room = room
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
      if hsu.healthcare_service_unit == room:
        previous_docname = hsu.reference_doc
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
  doc = frappe.get_doc(doc_fields)
  cancelled_doc = None
  if previous_docname:
    cancelled_doc = frappe.get_doc(doc_type, previous_docname)
    if cancelled_doc.docstatus != 2:
      cancelled_doc.db_set('docstatus', 2)
    if doc_type == 'Sample Collection':
      if cancelled_doc.custom_status == 'To Retest':
        doc.amended_from = cancelled_doc.name
    elif doc_type == 'Doctor Examination':
      doc = frappe.copy_doc(cancelled_doc)
      doc.amended_from = cancelled_doc.name
      doc.created_date = today()
      doc.service_unit = room
      doc.dispatcher = name
      doc.status = 'Started'
      doc.examination_item = []
      doc.result = []
      doc.non_selective_result = []
      doc.dental_detail = []
      doc.other_dental = []
      doc.questionnaire_detail = []
    else:
      if cancelled_doc.status == 'To Retest':
        doc.amended_from = cancelled_doc.name

  exam_items = fetch_exam_items(name, room, appt_doc.custom_branch, template_doctype)
  if not exam_items:
    frappe.throw("No Template found.")
  append_exam_results(doc, exam_items, template_doctype, cancelled_doc)
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