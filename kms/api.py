import frappe, re
from frappe.utils import today, getdate
import json

@frappe.whitelist()
def get_mcu(price_list):
  mcu = frappe.db.sql(f"""SELECT ti.item_code, ti.item_name, tip.price_list_rate
    FROM `tabItem` ti, `tabItem Price` tip 
    WHERE is_stock_item = 0 
    AND is_sales_item = 1 
    AND is_purchase_item = 0 
    AND custom_mandatory_item_in_package = 1 
    and ti.item_code = tip.item_code 
    and price_list = '{price_list}'""", as_dict=True)
  return mcu 

@frappe.whitelist()
def upsert_item_price(item_code, price_list, customer, price_list_rate):
  if frappe.db.exists(
    {"doctype":"Item Price", "item_code": item_code, "price_list": price_list, "customer": customer}):
    today = frappe.utils.today()
    name = frappe.db.get_value(
      "Item Price",
      {"item_code": item_code, "price_list": price_list, "customer": customer},"name")
    doc = frappe.get_doc("Item Price", name)
    doc.price_list_rate = price_list_rate
    doc.valid_from = today
    doc.save()
    return doc.name
  else:
    today = frappe.utils.today()
    doc = frappe.get_doc({
      "doctype":"Item Price", 
      "item_code": item_code, 
      "uom": "Unit", 
      "price_list": price_list, 
      "selling":"true", 
      "customer": customer, 
      "currency": "IDR", 
      "price_list_rate": price_list_rate, 
      "valid_from": today})
    doc.insert()
    return doc.name

@frappe.whitelist()
def update_quo_status(name):
  doc = frappe.get_doc('Quotation', name)
  doc.status = 'Ordered'
  doc.save()

@frappe.whitelist()
def get_users_by_doctype(doctype):
  # Mapping of doctype to target field
  doctype_to_target = {
    'Radiology Result': 'radiology_result_assignment_role',
    'Lab Test': 'lab_test_assignment_role',
    'Nurse Result': 'nurse_result_assignment_role',
    'Doctor Result': 'doctor_result_assignment_role'
  }
  # Get the target field based on the doctype
  target = doctype_to_target.get(doctype)
  if not target:
    return []
  # Fetch roles based on the target field
  roles = frappe.get_all(
    'MCU Assignment Role', filters={'parentfield': target}, fields=['role'], pluck='role')
  excluded_users = ['Guest', 'Administrator']
  unique_users = {}
  for role in roles:
    # Fetch users with the given role
    users = frappe.get_all(
      "Has Role",
      filters={"role": role, "parenttype": "User", 'parent': ['not in', excluded_users]},
      fields=["parent"],
      distinct=True
    )
    # Fetch user details and append to the user_list
    for user in users:
      if user.parent not in unique_users:
        user_doc = frappe.get_doc("User", user.parent)
        if not user_doc.enabled or user_doc.user_type != 'System User':
          continue
        unique_users[user.parent] = {
          "name": user_doc.name,
          "full_name": user_doc.full_name
        }
  return list(unique_users.values())

@frappe.whitelist()
def create_mr_from_encounter(enc):
  message = []
  encdoc = frappe.get_doc('Patient Encounter', enc)
  drug_prescriptions = encdoc.get("drug_prescription", [])
  def filter_items(internal):
    return [
      item for item in drug_prescriptions
      if item.get('custom_is_internal') == internal and item.get('custom_status') == 'Created'
    ]
  def filter_compound_items(index):
    if encdoc.get(f'custom_compound_type_{index}'):
      drug_prescriptions = encdoc.get(f'custom_compound_medication_{index}')
      if drug_prescriptions:
        items = []
        items.append({
          'drug_code': encdoc.get(f'custom_linked_item_{index}'),
          'drug_name': encdoc.get(f'custom_compound_type_{index}'),
          'custom_compound_qty': encdoc.get(f'custom_qty_{index}'),
          'dosage': encdoc.get(f'custom_dosage_{index}'),
          'period': encdoc.get(f'custom_dosage_instruction_{index}'),
          'dosage_form': encdoc.get(f'custom_additional_instruction_{index}'),
          'indication': encdoc.get(f'custom_indication_{index}'),
          'custom_serving_qty': encdoc.get(f'custom_serving_qty_{index}'),
          'custom_serving_unit_of_measure': encdoc.get(f'custom_serving_unit_of_measure_{index}'),
        })
        for drug in drug_prescriptions:
          if drug.status == 'Created':
            items.append({
              'drug_code': drug.drug_code,
              'drug_name': drug.drug_name,
              'custom_compound_qty': drug.qty,
              'compound_type': drug.compound_type,
            })
        return items
      else:
        return None
    else:
      return None
  mr_internal_items = filter_items(1)
  mr_external_items = filter_items(0)
  compound_items_1 = filter_compound_items(1)
  compound_items_2 = filter_compound_items(2)
  compound_items_3 = filter_compound_items(3)

  pharmacy_warehouse, target_warehouse = frappe.db.get_value(
    'Branch', 
    encdoc.custom_branch, 
    ['custom_default_pharmacy_warehouse', 'custom_default_front_office'])
  def create_or_update_mr(items, internal=True):
    if not items:
      return None
    if internal:
      target_warehouse = frappe.db.get_value(
        'Healthcare Service Unit', encdoc.custom_service_unit, 'warehouse')
    existing_mr = frappe.db.get_all(
      'Material Request', 
      {
        'docstatus': 0, 
        'custom_patient_encounter': enc, 
        'set_warehouse': target_warehouse
      }, 
      'name'
    )
    if existing_mr:
      mr_doc = frappe.get_doc('Material Request', existing_mr[0])
    else:
      mr_doc = frappe.new_doc('Material Request')
      mr_doc.transaction_date = getdate(today())
      mr_doc.material_request_type = 'Medication Prescription'
      mr_doc.schedule_date = getdate(today())
      mr_doc.set_from_warehouse = pharmacy_warehouse
      mr_doc.set_warehouse = target_warehouse
      mr_doc.custom_appointment = encdoc.appointment
      mr_doc.custom_patient = encdoc.patient
      mr_doc.custom_patient_name = encdoc.patient_name
      mr_doc.custom_patient_sex = encdoc.patient_sex
      mr_doc.custom_patient_age = encdoc.patient_age
      mr_doc.custom_patient_encounter = encdoc.name
      mr_doc.custom_healthcare_practitioner = encdoc.practitioner
    for item in items:
      print(item)
      print(type(item))
      stock_uom = frappe.db.get_value('Item', item.get('drug_code'), 'stock_uom')
      if item.get('indication'):
        custom_indication = item.get('indication')
      else:
        custom_indication = frappe.db.get_value('Item', item.get('drug_code'), 'custom_indication')
      if item.get('custom_serving_unit_of_measure'):
        custom_serving_unit_of_measure = item.get('custom_serving_unit_of_measure')
      else:
        custom_serving_unit_of_measure = frappe.db.get_value(
          'Item', item.get('drug_code'), 'custom_serving_unit_of_measure')
      mr_doc.append('items', {
        'item_code': item.get('drug_code'),
        'item_name': item.get('drug_name'),
        'schedule_date': getdate(today()),
        'description': item.get('drug_name'),
        'qty': item.get('custom_compound_qty'),
        'uom': stock_uom,
        'stock_uom': stock_uom, 
        'conversion_factor': 1,
        'from_warehouse': pharmacy_warehouse,
        'warehouse': target_warehouse,
        'custom_dosage': item.get('dosage'),
        'custom_period': item.get('period'),
        'custom_dosage_form': item.get('dosage_form'),
        'custom_indication': custom_indication,
        'custom_serving_qty': item.get('custom_serving_qty') or 1,
        'custom_serving_unit_of_measure': custom_serving_unit_of_measure or stock_uom,
        'custom_compound_type': item.get('compound_type')
      })
    mr_doc.save(ignore_permissions=True)
    message.append(mr_doc.name)
    for item in items:
      if not isinstance(item, dict):
        item.set('custom_material_request', mr_doc.name)
        item.set('custom_status', 'Ordered')
      if encdoc.custom_compound_type_1:
        encdoc.custom_pharmacy_order_1 = mr_doc.name
      if encdoc.custom_compound_type_2:
        encdoc.custom_pharmacy_order_2 = mr_doc.name
      if encdoc.custom_compound_type_3:
        encdoc.custom_pharmacy_order_3 = mr_doc.name
    encdoc.save(ignore_permissions=True)
  create_or_update_mr(mr_internal_items)
  create_or_update_mr(mr_external_items, internal=False)
  create_or_update_mr(compound_items_1)
  create_or_update_mr(compound_items_2)
  create_or_update_mr(compound_items_3)
  if message:
    return f'Pharmacy Order {', '.join(message)} created.'
  else: 
    return 'No Pharmacy Order created.'

@frappe.whitelist()
def check_eligibility_to_reopen(name):
  sql = f"""SELECT IFNULL(SUM(a), 0) not_eligible FROM 
    (SELECT 1 a FROM `tabVital Signs` tvs 
      WHERE tvs.appointment = '{name}' AND tvs.docstatus = 1 UNION 
    SELECT 1 FROM `tabDoctor Examination` tvs 
      WHERE tvs.appointment = '{name}' AND tvs.docstatus in (0,1) UNION
    SELECT 1 FROM `tabNurse Examination` tvs 
      WHERE tvs.appointment = '{name}' AND tvs.docstatus in (0,1) UNION
    SELECT 1 FROM `tabSample Collection` tvs 
      WHERE tvs.custom_appointment = '{name}' AND tvs.docstatus in (0,1) UNION
    SELECT 1 FROM `tabRadiology` tvs 
      WHERE tvs.appointment = '{name}' AND tvs.docstatus in (0,1)) b"""
  return frappe.db.sql(sql, as_dict = True)

@frappe.whitelist()
def reopen_appointment(name):
  sql = f"""SELECT IFNULL(SUM(a), 0) not_eligible FROM 
    (SELECT 1 a FROM `tabVital Signs` tvs 
      WHERE tvs.appointment = '{name}' AND tvs.docstatus = 1 UNION 
    SELECT 1 FROM `tabDoctor Examination` tvs 
      WHERE tvs.appointment = '{name}' AND tvs.docstatus in (0,1) UNION
    SELECT 1 FROM `tabNurse Examination` tvs 
      WHERE tvs.appointment = '{name}' AND tvs.docstatus in (0,1) UNION
    SELECT 1 FROM `tabSample Collection` tvs 
      WHERE tvs.custom_appointment = '{name}' AND tvs.docstatus in (0,1) UNION
    SELECT 1 FROM `tabRadiology` tvs 
      WHERE tvs.appointment = '{name}' AND tvs.docstatus in (0,1)) b"""
  check = frappe.db.sql(sql, as_dict = True)
  if check[0].not_eligible != 0:
    frappe.throw('Cannot reopen appointment. There are already recorded examinations.')
  else:
    vital_signs = frappe.db.get_value('Vital Signs', {'appointment': name}, 'name')
    if vital_signs:
      frappe.delete_doc('Vital Signs', vital_signs, ignore_missing=True, force=True)
    dispatcher = frappe.db.get_value('Dispatcher', {'patient_appointment': name}, 'name')
    if dispatcher:
      frappe.delete_doc('Dispatcher', dispatcher, ignore_missing=True, force=True)
    if vital_signs or dispatcher:
      frappe.db.set_value('Patient Appointment', name, 'status', 'Open')
    else:
      frappe.throw('There are no Vital Signs or Dispatcher record to delete.')

@frappe.whitelist()
def check_out_appointment(name):
  frappe.db.set_value('Patient Appointment', name, 'status', 'Checked Out')
  mcu = frappe.db.get_value('Patient Appointment', name, 'mcu')
  if mcu:
    frappe.call(
      'kms.kms.doctype.dispatcher.dispatcher.new_doctor_result',
      appointment = name)

@frappe.whitelist()
def get_assigned_room(date):
  return frappe.db.get_all('Room Assignment', filters = {'date': date, 'assigned': 1}, pluck='healthcare_service_unit')