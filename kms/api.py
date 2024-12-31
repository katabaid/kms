import frappe, re
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
  user_list = []
  for role in roles:
    # Fetch users with the given role
    users = frappe.get_all(
      "Has Role",
      filters={"role": role, "parenttype": "User"},
      fields=["parent"],
      distinct=True
    )
    # Fetch user details and append to the user_list
    for user in users:
      user_doc = frappe.get_doc("User", user.parent)
      user_list.append({
        "name": user_doc.name,
        "full_name": user_doc.full_name
      })
  return user_list

@frappe.whitelist()
def create_mr_from_encounter(enc):
  encdoc = frappe.get_doc('Patient Encounter', enc)
  
  mr_internal_items = frappe.db.sql(f"""
    select drug_code, drug_name, dosage, period, dosage_form, custom_compound_qty
    from `tabDrug Prescription`
    where parent = '{encdoc.name}' 
    and parenttype = 'Patient Encounter' 
    and custom_material_request is null 
    and custom_is_internal = 1 
    and docstatus = 0""", as_dict=True)
  mr_external_items = frappe.db.sql(f"""
    select drug_code, drug_name, dosage, period, dosage_form, custom_compound_qty
    from `tabDrug Prescription`
    where parent = '{encdoc.name}' 
    and parenttype = 'Patient Encounter' 
    and custom_material_request is null 
    and custom_is_internal = 0 
    and docstatus = 0""", as_dict=True)
  pharmacy_warehouse, front_office = frappe.db.get_value(
    'Branch', 
    encdoc.custom_branch, 
    ['custom_default_pharmacy_warehouse', 'custom_default_front_office'])
  message =[pharmacy_warehouse, front_office]
  if(mr_internal_items):
    warehouse = frappe.db.get_value(
      'Healthcare Service Unit', encdoc.custom_service_unit, 'warehouse')
    mr_in_doc = frappe.new_doc('Material Request')
    mr_in_doc.transaction_date = frappe.utils.today()
    mr_in_doc.material_request_type= 'Medication Prescription'
    mr_in_doc.schedule_date = frappe.utils.today()
    mr_in_doc.set_from_warehouse = pharmacy_warehouse
    mr_in_doc.set_warehouse = warehouse
    mr_in_doc.custom_appointment = encdoc.appointment,
    mr_in_doc.custom_patient = encdoc.patient
    mr_in_doc.custom_patient_name = encdoc.patient_name
    mr_in_doc.custom_patient_sex = encdoc.patient_sex
    mr_in_doc.custom_patient_age = encdoc.patient_age
    mr_in_doc.custom_patient_encounter = encdoc.name
    mr_in_doc.custom_healthcare_practitioner = encdoc.practitioner
    for item in mr_internal_items:
      stock_uom = frappe.db.get_value('Item', item.drug_code, 'stock_uom')
      mr_in_doc.append('items',{
        'item_code': item.drug_code,
        'item_name': item.drug_name,
        'schedule_date': frappe.utils.today(),
        'description': item.drug_name,
        'qty': item.custom_compound_qty,
        'uom': stock_uom,
        'stock_uom': stock_uom, 
        'conversion_factor': 1,
        'from_warehouse': pharmacy_warehouse,
        'warehouse': warehouse,
        'custom_dosage': item.dosage,
        'custom_period': item.period,
        'custom_dosage_form': item.dosage_form
      })
    mr_in_doc.insert(ignore_permissions=True);
    update_sql = (
      f"""update `tabDrug Prescription` set custom_material_request = '{mr_in_doc.name}'"""
      f"""where parent = '{encdoc.name}' and parentfield = 'drug_prescription'"""
      f"""and parenttype = 'Patient Encounter' and custom_material_request is null""" 
      f"""and custom_is_internal = 1 and docstatus = 0"""
    )
    frappe.db.sql(update_sql)
    message.append(mr_in_doc.name)
  else: 
    message.append('Empty internal')

  if(mr_external_items):
    mr_ex_doc = frappe.new_doc('Material Request')
    mr_ex_doc.transaction_date = frappe.utils.today()
    mr_ex_doc.material_request_type= 'Medication Prescription'
    mr_ex_doc.schedule_date = frappe.utils.today()
    mr_ex_doc.set_from_warehouse = pharmacy_warehouse
    mr_ex_doc.set_warehouse = front_office
    mr_ex_doc.custom_appointment = encdoc.appointment,
    mr_ex_doc.custom_patient = encdoc.patient
    mr_ex_doc.custom_patient_name = encdoc.patient_name
    mr_ex_doc.custom_patient_sex = encdoc.patient_sex
    mr_ex_doc.custom_patient_age = encdoc.patient_age
    mr_ex_doc.custom_patient_encounter = encdoc.name
    mr_ex_doc.custom_healthcare_practitioner = encdoc.practitioner
    for item in mr_external_items:
      stock_uom = frappe.db.get_value('Item', item.drug_code, 'stock_uom')
      mr_ex_doc.append('items',{
        'item_code': item.drug_code,
        'item_name': item.drug_name,
        'schedule_date': frappe.utils.today(),
        'description': item.drug_name,
        'qty': item.custom_compound_qty,
        'uom': stock_uom,
        'stock_uom': stock_uom, 
        'conversion_factor': 1,
        'from_warehouse': pharmacy_warehouse,
        'warehouse': front_office,
        'custom_dosage': item.dosage,
        'custom_period': item.period,
        'custom_dosage_form': item.dosage_form
      })
    mr_ex_doc.insert(ignore_permissions=True);
    update_sql = (
      f"""update `tabDrug Prescription` set custom_material_request = '{mr_ex_doc.name}' """ 
      f"""where parent = '{encdoc.name}' and parentfield = 'drug_prescription' """ 
      f"""and parenttype = 'Patient Encounter' and custom_material_request is null """ 
      f"""and custom_is_internal = 0 and docstatus = 0"""
    )
    frappe.db.sql(update_sql)
    message.append(mr_ex_doc.name)
  else: 
    message.append('Empty external')
  return message