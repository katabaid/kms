import frappe
from frappe.utils import now
from kms.utils import assess_mcu_grade

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
  if doctor_result_name:
    update_doctor_result_grades(doc, doctor_result_name)
    return
  
  encounter = frappe.db.get_value(
    'Sample Collection', doc.custom_sample_collection, 'custom_encounter')
  if not encounter:
    return
  for lab_test_name in get_all_test_names(doc):
    update_lab_prescription(encounter, lab_test_name, doc.name)

def lab_before_submit(doc, method=None):
  if not all_results_filled(doc.normal_test_items, doc.custom_selective_test_result):
    frappe.throw('All results must have value before submitting.')

def lab_before_save(doc, method=None):
  apply_calculated_exam_results(doc.normal_test_items)

def lab_before_update_after_submit(doc, method=None):
  if doc.custom_need_review:
    doctor_result_name, doctor_result_status = frappe.db.get_value('Doctor Result', 
      {'appointment': doc.custom_appointment}, ['name', 'docstatus'])
    if doctor_result_name:
      if doctor_result_status == 0:
        apply_calculated_exam_results(doc.normal_test_items)
        if not all_results_filled(doc.normal_test_items, doc.custom_selective_test_result):
          frappe.throw('All results must have value before submitting.')
        update_doctor_result_grades(doc, doctor_result_name)
      else:
        frappe.throw(f'Doctor Result {doctor_result_name} is already submitted.')
  else:
    frappe.throw('Need Review flag must be active.')

#endregion
#region Lab Test Template
def lab_test_template_before_save(doc, method=None):
  normal_events = {d.lab_test_event for d in doc.normal_test_templates if d.lab_test_event}
  custom_events = {d.event for d in doc.custom_selective if d.event}
  total_distinct_events = len(normal_events.union(custom_events))
  doc.custom_is_single_result = 1 if total_distinct_events == 1 else 0
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

def all_results_filled(normal, selective):
  all_normal = all(item.result_value for item in normal)
  all_selective = all(item.result for item in selective)
  return all_normal and all_selective

def apply_calculated_exam_results(result_table):
  templates = {item.lab_test_name for item in result_table}
  for template_name in templates:
    ltt = frappe.get_doc('Lab Test Template', template_name)
    for formula in ltt.custom_calculated_exam or []:
      result = evaluate_formula(result_table, formula.formula)
      if result:
        match = next((
          item for item in result_table
          if item.lab_test_name == template_name and item.lab_test_event == formula.test_label
        ), None)
        if match:
          match.result_value = result

def update_doctor_result_grades(doc, doctor_result_name):
  for item in doc.normal_test_items:
    template = item.template or item.lab_test_name
    item_group, is_single_result = frappe.db.get_value(
      'Lab Test Template', template,
      ['lab_test_group', 'custom_is_single_result'])
    examination = item.lab_test_name if is_single_result else item.lab_test_event
    filters = {
      'hidden_item': item.custom_item,
      'hidden_item_group': item_group,
      'parent': doctor_result_name,
      'examination': examination,
      'is_item': int(is_single_result)
    }
    mcu_grade_name = frappe.db.get_value('MCU Exam Grade', filters, 'name')
    result_value = float(item.result_value.replace(',', '.')) if isinstance(item.result_value, str) else item.result_value
    grade_name, description, _ = assess_mcu_grade(
      result_value, item_group, item.custom_item,
      min_value=item.custom_min_value, max_value=item.custom_max_value,
      test_name=item.lab_test_event if not is_single_result else None
    )
    incdec = None
    if result_value > item.custom_max_value:
      incdec = 'Increase'
    elif result_value < item.custom_min_value:
      incdec = 'Decrease'
    incdec_category = None
    if incdec:
      incdec_filter = {
        'item_group': item_group,
        'item': item.custom_item,
        'selection': incdec
      }
      if not is_single_result:
        incdec_filter['test_name'] = item.lab_test_event if not is_single_result else None
      incdec_category = frappe.db.get_value('MCU Category', incdec_filter, 'description')
    frappe.db.set_value('MCU Exam Grade', mcu_grade_name, {
      'result': result_value,
      'incdec': incdec,
      'incdec_category': incdec_category,
      'status': doc.status,
      'grade': grade_name,
      'description': description
    })
  for selective in doc.custom_selective_test_result:
    item_group, is_single_result, lab_test_name = frappe.db.get_value(
      'Lab Test Template', {'item': selective.item},
      ['lab_test_group', 'custom_is_single_result', 'lab_test_description'])
    filters = {
      'hidden_item': selective.item,
      'hidden_item_group': item_group,
      'parent': doctor_result_name,
      'examination': selective.event if not is_single_result else lab_test_name,
      'is_item': 0 if not is_single_result else 1
    }
    mcu_grade_name = frappe.db.get_value('MCU Exam Grade', filters, 'name')
    grade_name, description, _ = assess_mcu_grade(
      selective.result, item_group, selective.item,
      normal_value=selective.normal_value,
      test_name=selective.event if not is_single_result else None
    )
    frappe.db.set_value('MCU Exam Grade', mcu_grade_name, {
      'result': selective.result,
      'grade': grade_name,
      'description': description,
      'status': doc.status,
      'std_value': selective.normal_value
    })

def get_all_test_names(doc):
  normal_tests = [item.lab_test_name for item in doc.normal_test_items]
  selective_tests = [item.event for item in doc.custom_selective_test_result]
  return normal_tests + selective_tests

def update_lab_prescription(encounter, lab_test_name, lab_test_doc_name):
  filters = {
    'lab_test_name': lab_test_name,
    'docstatus': 0,
    'parent': encounter,
    'parentfield': 'lab_test_prescription',
    'parenttype': 'Patient Encounter',
    'custom_lab_test': None
  }
  prescription_name = frappe.db.get_value('Lab Prescription', filters)
  if prescription_name:
    frappe.db.set_value('Lab Prescription', prescription_name, 'custom_lab_test', lab_test_doc_name)
#endregion