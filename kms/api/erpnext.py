import frappe
from frappe.utils import today, getdate

@frappe.whitelist()
def get_mcu(price_list: str) -> list[dict]:
    """Get MCU items with prices from specified price list.
    Args:
        price_list: Name of the Price List to filter by
    Returns:
        List of items with code, name and price
    """
    return frappe.db.sql("""
        SELECT
            ti.item_code,
            ti.item_name,
            tip.price_list_rate
        FROM
            `tabItem` ti
        INNER JOIN
            `tabItem Price` tip
            ON ti.item_code = tip.item_code
        WHERE
            ti.is_stock_item = 0
            AND ti.is_sales_item = 1
            AND ti.is_purchase_item = 0
            AND ti.custom_mandatory_item_in_package = 1
            AND tip.price_list = %s
        """, (price_list), as_dict=True)

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
def check_eligibility_to_reopen(name: str) -> list[dict]:
    """Check if an appointment can be reopened by verifying related records.
    Args:
        name: Appointment ID to check
    Returns:
        List with single dict containing not_eligible count (0 = eligible)
    """
    return _check_appointment_eligibility(name)

@frappe.whitelist()
def reopen_appointment(name: str) -> None:
  """Reopen appointment by deleting related records if eligible.
  Args:
      name: Appointment ID to reopen
  Raises:
      frappe.ValidationError: If appointment cannot be reopened
  """
  # Check eligibility using shared validation logic
  eligibility = _check_appointment_eligibility(name)
  if eligibility[0]['not_eligible'] != 0:
    frappe.throw('Cannot reopen appointment. Existing examinations found: '
      'Vital Signs, Doctor/Nurse Exams, Sample Collections, or Radiology records.')
  # Delete related records
  deleted_records = False
  # Delete Vital Signs if exists
  vital_signs = frappe.db.get_value('Vital Signs', {'appointment': name}, 'name')
  if vital_signs:
    frappe.delete_doc('Vital Signs', vital_signs, ignore_missing=True, force=True)
    deleted_records = True
  # Delete Dispatcher if exists
  dispatcher = frappe.db.get_value('Dispatcher', {'patient_appointment': name}, 'name')
  if dispatcher:
    frappe.delete_doc('Dispatcher', dispatcher, ignore_missing=True, force=True)
    deleted_records = True
  # Update appointment status if records were deleted
  if deleted_records:
    frappe.db.set_value('Patient Appointment', name, 'status', 'Open')
    frappe.msgprint(f'Appointment {name} reopened successfully')
  else:
    frappe.throw('No related records found to delete - cannot reopen appointment')

def _check_appointment_eligibility(name: str) -> list[dict]:
    """Shared validation function for appointment operations."""
    return frappe.db.sql("""
        WITH appointment_checks AS (
            SELECT 1 AS flag FROM `tabVital Signs`
            WHERE appointment = %(appt)s AND docstatus = 1
            UNION ALL
            SELECT 1 FROM `tabDoctor Examination`
            WHERE appointment = %(appt)s AND docstatus IN (0, 1)
            UNION ALL
            SELECT 1 FROM `tabNurse Examination`
            WHERE appointment = %(appt)s AND docstatus IN (0, 1)
            UNION ALL
            SELECT 1 FROM `tabSample Collection`
            WHERE custom_appointment = %(appt)s AND docstatus IN (0, 1)
            UNION ALL
            SELECT 1 FROM `tabRadiology`
            WHERE appointment = %(appt)s AND docstatus IN (0, 1)
        )
        SELECT IFNULL(SUM(flag), 0) AS not_eligible
        FROM appointment_checks
    """, {"appt": name}, as_dict=True)

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

@frappe.whitelist(allow_guest=True)
def get_appointment_types():
  appointment_types = frappe.get_all("Appointment Type", fields=["name"])

  result = []
  for appt in appointment_types:
    doc = frappe.get_doc("Appointment Type", appt["name"])  # Fetch full doc
    branches = [entry.branch for entry in doc.custom_branch]  # Extract branch names
    result.append({
      "name": doc.name,
      "custom_branch": branches
    })

  return result

@frappe.whitelist()
def set_item_price(item_code, price_list, rate):
  """
  Set or update the latest item price for a given item and price list.
  If there's no valid price within today's range, a new record is created.
  If a valid price exists, its 'valid_to' is set to today, and a new record is created.

  :param item_code: The Item Code (str)
  :param price_list: The Price List (str)
  :param rate: The new price (float)
  :return: Success message or error
  """

  today_date = today()
  buying, selling = frappe.db.get_value("Price List", price_list, ["buying", "selling"])
  item_uom = frappe.db.get_value("Item", item_code, ["stock_uom", "purchase_uom", "sales_uom"], as_dict=True)
  if not item_uom:
    return f"Error: Item '{item_code}' not found."
  if not buying or not selling:
    return f"Error: Price List '{price_list}' missing type."
  elif buying:
    uom = item_uom.get("purchase_uom") or item_uom.get("stock_uom")
  elif selling:
    uom = item_uom.get("purchase_uom") or item_uom.get("stock_uom")
  else:
    return "Error: UOM could not be determined."
  # Check if there's an active price within today's range
  existing_price = frappe.db.get_value(
    "Item Price",
    {
      "item_code": item_code,
      "price_list": price_list,
      "valid_from": ["<=", today_date],
      "valid_to": ["is", "set"],
      "valid_to": [">=", today_date]
    },
    ["name", "valid_from", "valid_to"]
  )

  if existing_price:
    existing_price_name, valid_from, valid_to = existing_price

    # Update the existing record to close its validity
    frappe.db.set_value("Item Price", existing_price_name, "valid_to", today_date)

  # Create a new Item Price record
  new_price = frappe.get_doc({
    "doctype": "Item Price",
    "item_code": item_code,
    "price_list": price_list,
    "uom": uom,
    "price_list_rate": rate,
    "valid_from": today_date,
    "valid_to": None  # Open-ended price
  })
  new_price.insert(ignore_permissions=True)
  frappe.db.commit()

  return f"Item Price updated for {item_code} in {price_list} with rate {rate}"

@frappe.whitelist()
def get_latest_item_price(item_code, price_list):
    """
    Fetch the latest valid price of an item from the Item Price doctype.

    - Considers today's date between valid_from and valid_to (if valid_to exists).
    - Sorts by valid_from in descending order to get the most recent valid price.

    :param item_code: The Item Code
    :param price_list: The Price List (e.g., "Standard Selling", "Standard Buying")
    :return: Latest valid item price or None if not found
    """
    today_date = today()

    price = frappe.db.sql("""
      SELECT price_list_rate
      FROM `tabItem Price`
      WHERE item_code = %s
      AND price_list = %s
      AND valid_from <= %s
      AND (valid_to IS NULL OR valid_to >= %s)
      ORDER BY valid_from DESC
      LIMIT 1
    """, (item_code, price_list, today_date, today_date), as_dict=True)

    return price[0]["price_list_rate"] if price else None
