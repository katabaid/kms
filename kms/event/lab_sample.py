import frappe
from frappe.utils import now

#region WHITELISTED METHODS
@frappe.whitelist()
def get_items():
  item_group = frappe.db.sql("""
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
  item = frappe.db.sql("""
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
def create_sc(name, appointment):
  appt_doc = frappe.get_doc('Patient Appointment', appointment)
  sample_collections = frappe.db.get_all('Sample Collection',
    filters = {'custom_appointment': appointment, 'docstatus': 0},
    pluck = 'name')
  #how to determine service unit if more than 1 per branch is registered in item group (i.e. : usg male/usg female, sample1/sample2)
  sus = frappe.db.sql("""
    SELECT DISTINCT tigsu.service_unit
    FROM `tabItem Group Service Unit` tigsu, `tabLab Prescription` tlp 
    WHERE tlp.parent = %s
    AND tlp.custom_exam_item = tigsu.parent
    AND branch = %s
    AND custom_sample_collection IS NULL""", (name, appt_doc.custom_branch), as_dict=True)
  resp = []
  if sus:
    for su in sus:
      sample_doc = None
      if sample_collections:
        for sample_collection in sample_collections:
          existing_doc = frappe.get_doc('Sample Collection', sample_collection)
          if existing_doc.custom_service_unit == su.service_unit:
            sample_doc = existing_doc
            break
      if not sample_doc:  
        sample_doc = frappe.get_doc({
          'doctype': 'Sample Collection',
          'custom_appointment': appt_doc.name,
          'patient': appt_doc.patient,
          'patient_name': appt_doc.patient_name,
          'patient_age': appt_doc.patient_age,
          'patient_sex': appt_doc.patient_sex,
          'company': appt_doc.company,
          'custom_branch': appt_doc.custom_branch,
          'custom_service_unit': su.service_unit,
          'custom_status': 'Started',
          'custom_document_date': frappe.utils.now(),
          'custom_encounter': name
        })
      samples = frappe.db.sql("""
      SELECT distinct tltt.sample
      FROM `tabItem Group Service Unit` tigsu, `tabLab Prescription` tlp, `tabLab Test Template` tltt 
      WHERE tlp.parent = %s
      AND tlp.custom_exam_item = tigsu.parent
      AND branch = %s
      and tigsu.service_unit = %s
      AND tltt.name = tlp.lab_test_name
      AND tltt.sample IS NOT NULL
      AND custom_sample_collection IS NULL""", 
      (name, appt_doc.custom_branch, su.service_unit), as_dict=True)
      existing_samples = {row.sample for row in sample_doc.get('custom_sample_table', [])}
      for sample in samples:
        if sample.sample not in existing_samples:
          sample_doc.append('custom_sample_table', {
            'sample': sample.sample,
          })
      enc_doc = frappe.get_doc('Patient Encounter', name)
      for lab in enc_doc.lab_test_prescription:
        entries = dict()
        if not lab.custom_sample_collection: 
          entries['template'] = lab.lab_test_code
          entries['item_code'] = lab.custom_exam_item
          sample_doc.append('custom_examination_item', entries)
      sample_doc.save(ignore_permissions=True)
      resp.append(sample_doc.name)
      lab_test_prescription = enc_doc.get('lab_test_prescription', [])
      lt = [item for item in lab_test_prescription
        if item.get('custom_sample_collection') is None
      ]
      for item in lt:
        item.set('custom_sample_collection', sample_doc.name)
      enc_doc.save(ignore_permissions=True)
  else:
    frappe.throw('Lab Test already prescribed.')
  return f'Sample Collection {', '.join(resp)} created.'
#endregion
#region SAMPLE COLLECTION HOOKS
def sample_before_insert(doc, method=None):
  doc.custom_barcode_label = doc.custom_appointment
  mcu = frappe.db.get_value('Patient Appointment', doc.custom_appointment, 'mcu')
  if mcu:
    pb = frappe.get_doc('Product Bundle', mcu)
    doc.custom_yellow_tubes = pb.custom_number_of_yellow_tubes
    doc.custom_red_tubes = pb.custom_number_of_red_tubes
    doc.custom_purple_tubes = pb.custom_number_of_purple_tubes
    doc.custom_blue_tubes = pb.custom_number_of_blue_tubes
  
def sample_after_submit(doc, method=None):
  if doc.amended_from:
    doc.custom_status = 'Started'
    doc.collected_by = ''
    doc.collected_time = ''
    for item in doc.custom_sample_table:
      item.status = 'Started'
    doc.save()

def sample_before_submit(doc, method=None):
  if not doc.collected_by:
    doc.collected_by = frappe.session.user
  if not doc.collected_time:
    doc.collected_time = frappe.utils.now()

  exam_result = frappe.db.exists('Lab Test', {'custom_sample_collection': doc.name}, 'name')
  if exam_result:
    doc.custom_lab_test = exam_result
  room = frappe.db.get_value('Healthcare Service Unit', doc.custom_service_unit, 'custom_reception_room')
  if not room:
    frappe.throw('Set the Sample Reception Room for this Sample Collection first.')
  for sample in doc.custom_sample_table:
    if sample.status == 'Finished':
      sample_reception_doc = frappe.new_doc('Sample Reception')
      sample_reception_doc.patient = doc.patient
      sample_reception_doc.age = doc.patient_age
      sample_reception_doc.sample_collection = doc.name
      sample_reception_doc.lab_test_sample = sample.sample
      sample_reception_doc.sex = doc.patient_sex
      sample_reception_doc.appointment = doc.custom_appointment
      sample_reception_doc.name1 = doc.patient_name
      sample_reception_doc.healthcare_service_unit = room
      sample_reception_doc.save(ignore_permissions=True)
      #saved = True
      sample.sample_reception = sample_reception_doc.name
      sample.status_time = now()
      sample.reception_status = sample_reception_doc.docstatus
    if sample.status == 'Rescheduled' or sample.status == 'Refused':
      sample.reception_status = 1
#endregion
#region LAB TEST HOOKS
def lab_on_submit(doc, method=None):
  doctor_result_name = frappe.db.get_value('Doctor Result', {
    'appointment': doc.custom_appointment,
    'docstatus': 0
  }, 'name')
  encounter = frappe.db.get_value(
    'Sample Collection', doc.custom_sample_collection, 'custom_encounter')
  if doctor_result_name:
    for item in doc.normal_test_items:
      item_code = frappe.db.get_value(
        'Item', {'item_name': item.lab_test_name}, 'item_code')
      item_group = frappe.db.get_value(
        'Item', {'item_name': item.lab_test_name}, 'item_group')
      mcu_grade_name = frappe.db.get_value('MCU Exam Grade', {
        'hidden_item': item_code,
        'hidden_item_group': item_group,
        'parent': doctor_result_name,
        'examination': item.lab_test_event,
        'is_item': 0
      }, 'name')
      incdec = ''
      incdec_category = ''
      grade_name = description = ''
      if all([
        item.custom_max_value != 0 and 
        (item.custom_min_value == 0 or item.custom_min_value) and 
        item.custom_max_value and 
        item.result_value and 
        is_numeric(item.custom_min_value) and 
        is_numeric(item.custom_max_value) and 
        is_numeric(float(item.result_value))
      ]):
        if float(item.result_value) > item.custom_max_value:
          incdec = 'Increase'
        elif float(item.result_value) < item.custom_min_value:
          incdec = 'Decrease'
        elif float(item.result_value) >= item.custom_min_value and float(item.result_value) <= item.custom_max_value:
          grade_name = frappe.db.get_value(
            'MCU Grade',
            {'item_group': item_group, 'item_code': item_code, 'test_name': item.lab_test_event, 'grade': 'A'},
            'name'
          )
          description = frappe.db.get_value(
            'MCU Grade',
            grade_name,
            'description'
          )
        else:
          None
        if incdec:
          incdec_category = frappe.db.get_value('MCU Category', {
            'item_group': item_group,
            'item': item_code,
            'test_name': item.lab_test_event,
            'selection': incdec
          }, 'description')
      frappe.db.set_value('MCU Exam Grade', mcu_grade_name, {
        'result': item.result_value,
        'incdec': incdec,
        'incdec_category': incdec_category,
        'status': doc.status,
        'grade': grade_name,
        'description': description
      })
    for selective in doc.custom_selective_test_result:
      item_group = frappe.db.get_value(
        'Item', selective.item, 'item_group')
      mcu_grade_name = frappe.db.get_value('MCU Exam Grade', {
        'hidden_item': selective.item,
        'hidden_item_group': item_group,
        'parent': doctor_result_name,
        'examination': selective.event
      }, 'name')
      incdec = ''
      incdec_category = ''
      if selective.normal_value and selective.normal_value != selective.result:
        incdec = selective.result
        incdec_category = frappe.db.get_value('MCU Category', {
            'item_group': item_group,
            'item': selective.item,
            'test_name': selective.event,
            'selection': incdec
          }, 'description')
      frappe.db.set_value('MCU Exam Grade', mcu_grade_name, {
        'result': selective.result,
        'incdec': incdec,
        'incdec_category': incdec_category,
        'status': doc.status,
        'std_value': selective.normal_value
      })
  elif encounter:
    for item in doc.normal_test_items:
      lab_prescription_name = frappe.db.get_value('Lab Prescription', {
        'lab_test_name': item.lab_test_name,
        'docstatus': 0,
        'parent': encounter,
        'parentfield': 'lab_test_prescription',
        'parenttype': 'Patient Encounter',
        'custom_lab_test': None
      })
      frappe.db.set_value('Lab Prescription', lab_prescription_name, 'custom_lab_test', doc.name)
    for selective in doc.custom_selective_test_result:
      lab_prescription_name = frappe.db.get_value('Lab Prescription', {
        'lab_test_name': selective.event,
        'docstatus': 0,
        'parent': encounter,
        'parentfield': 'lab_test_prescription',
        'parenttype': 'Patient Encounter',
        'custom_lab_test': None
      })
      frappe.db.set_value('Lab Prescription', lab_prescription_name, 'custom_lab_test', doc.name)

def lab_before_submit(doc, method=None):
  counter1 = counter2 = counter3 = counter4 = 0
  for normal in doc.normal_test_items:
    counter1 +=1
    if normal.result_value:
      counter2 += 1
  for selective in doc.custom_selective_test_result:
    counter3 += 1
    if selective.result:
      counter4 += 1
  if counter1 != counter2 or counter3 != counter4:
    frappe.throw('All results must have value before submitting.')

def lab_before_save(doc, method=None):
  #Check jika ada calculated di template
  distinct_values = {child.lab_test_name for child in doc.normal_test_items}
  for template in distinct_values:
    ltt = frappe.get_doc('Lab Test Template', template)
    if ltt.custom_calculated_exam:
      result_table = doc.normal_test_items
      for formula in ltt.custom_calculated_exam:
        result = evaluate_formula(result_table, formula.formula)
        if result:
          for item in doc.normal_test_items:
            if (item.lab_test_name == template and 
              item.lab_test_event == formula.test_label):
              item.result_value = result
              break
#endregion
#region CHILD METHODS
def is_numeric(value):
  return isinstance(value, (int, float, complex)) and not isinstance(value, bool)

def evaluate_formula(table, formula_string):
  import re
  # Extract all placeholders from the formula string
  placeholders = re.findall(r'\{\{(.*?)\}\}', formula_string)
  # Create a mapping of placeholder names to values
  placeholder_values = {}
  missing_placeholders = []
  # Iterate through the child table to find matching labels
  for child in table:
    if child.lab_test_event in placeholders and child.result_value:# is not None:
      placeholder_values[child.lab_test_event] = child.result_value
  # Check if all placeholders have corresponding values
  for placeholder in placeholders:
    if placeholder not in placeholder_values:
      missing_placeholders.append(placeholder)
  # If there are missing placeholders, raise an error or return message
  if missing_placeholders:
    return None
  # Replace all placeholders with their corresponding values
  result_formula = formula_string
  for placeholder, value in placeholder_values.items():
    if isinstance(value, str):
      value = value.replace(',', '.')
    try:
      # Convert to float for calculation
      numeric_value = float(value)
      result_formula = result_formula.replace(f"{{{{{placeholder}}}}}", str(numeric_value))
    except (ValueError, TypeError):
      frappe.throw(f"Non-numeric value found for {placeholder}: {value}")
      return None
  # Evaluate the formula
  try:
    result = round(eval(result_formula), 1)
    return result
  except Exception as e:
    frappe.throw(f"Error evaluating formula: {str(e)}")
    return None
#endregion