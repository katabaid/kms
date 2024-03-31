import frappe
import json

@frappe.whitelist()
def get_mcu(price_list):
  mcu = frappe.db.sql(f"""SELECT ti.item_code, ti.item_name, tip.price_list_rate FROM `tabItem` ti, `tabItem Price` tip WHERE is_stock_item = 0 AND is_sales_item = 1 AND is_purchase_item = 0 AND custom_mandatory_item_in_package = 1 and ti.item_code = tip.item_code and price_list = '{price_list}'""", as_dict=True)
  return mcu 

@frappe.whitelist()
def upsert_item_price(item_code, price_list, customer, price_list_rate):
  if frappe.db.exists({"doctype":"Item Price", "item_code": item_code, "price_list": price_list, "customer": customer}):
    today = frappe.utils.today()
    name = frappe.db.get_value("Item Price",{"item_code": item_code, "price_list": price_list, "customer": customer},"name")
    doc = frappe.get_doc("Item Price", name)
    doc.price_list_rate = price_list_rate
    doc.valid_from = today
    doc.save()
    return doc.name
  else:
    today = frappe.utils.today()
    doc = frappe.get_doc({"doctype":"Item Price", "item_code": item_code, "uom": "Unit", "price_list": price_list, "selling":"true", "customer": customer, "currency": "IDR", "price_list_rate": price_list_rate, "valid_from": today})
    doc.insert()
    return doc.name

@frappe.whitelist()
def update_quo_status(name):
  frappe.db.sql(
    "update `tabQuotation` set status = 'Ordered' where name = %s",
    (name),
  )

@frappe.whitelist()
def get_item_codes_for_bundle():
  items = frappe.db.get_all("Item", fields=["name", "item_name", "item_group"], filters={"custom_product_bundle": "1", "disabled": "0"}, order_by="item_group")
  return items

@frappe.whitelist()
def create_product_bundle_from_quotation(items, name, price_list, party_name, quotation_to, price, margin):
  if isinstance(items, str):
    items = json.loads(items)
  item_name = ''
# Create Item from selected checkboxes
  item_doc = frappe.new_doc("Item")
  item_doc.naming_series = "Q.{custom_abbreviation}..{custom_product_bundle_customer}..{custom_product_bundle_lead}.-.###"
  item_doc.item_name = name
  item_doc.item_group = "Exam Course"
  item_doc.stock_uom = "Unit"
  item_doc.is_stock_item = False
  item_doc.include_item_in_manufacturing = False
  item_doc.is_purchase_item = False
  item_doc.is_sales_item = True
  if quotation_to == "Lead":
    item_doc.custom_product_bundle_lead = party_name
  elif quotation_to == "Customer":
    item_doc.custom_product_bundle_customer = party_name
  item_doc.insert();
# Create Product Bundle from created Item
  pb_doc = frappe.new_doc("Product Bundle")
  pb_doc.name = item_doc.name
  pb_doc.new_item_code = item_doc.name
  pb_doc.description = name
  if quotation_to == "Lead":
    pb_doc.custom_lead = party_name
  elif quotation_to == "Customer":
    pb_doc.custom_customer = party_name
  if price_list=='':
    price_list = 'Standard Selling'
  pb_doc.custom_price_list = price_list
# Calculate rate from items
  total_rate = 0
  rate = 0
  uom=""
  pb_doc.items = []
  for i in items:
    rate = frappe.db.get_value("Item Price", {"item_code": i["item_code"], "price_list": price_list}, "price_list_rate")
    uom = frappe.db.get_value("Item", i["item_code"], "stock_uom")
    description = frappe.db.get_value("Item", i["item_code"], "description")
    i["description"] = description
    i["uom"] = uom
    if rate is None:
      rate = 0
    i["rate"] = rate
    i["parent"] = item_doc.name
    
    total_rate = total_rate + rate
    pb_doc.append("items", i)
  pb_doc.custom_rate = price
  pb_doc.custom_margin = margin
  pb_doc.custom_enable = 0
  pb_doc.insert();
  message = frappe.get_doc('Product Bundle', pb_doc.name)
  return message

@frappe.whitelist()
def get_quotation_item(quotation_no):
  items = frappe.db.sql(f"""select
	tqi.idx,
	tig.name item_group,
	concat(tqi.item_name, ": ", tpb.name) bundle_name,
	tpb.name,
	tpbi.item_code,
	concat(tpbi.description, ": ", tpbi.item_code) item_name,
	tip.price_list_rate item_rate,
	tqi.qty quotation_qty,
	tqi.rate quotation_rate,
	nvl((
	SELECT
		price_list_rate
	FROM
		`tabItem Price` tip2
	WHERE
		tip2.item_code = tpbi.item_code
		AND EXISTS (
		SELECT
			1
		FROM
			`tabSingles` ts2
		WHERE
			ts2.doctype = 'Product Bundle Settings'
			AND ts2.field = 'default_cogs'
			AND ts2.value = tip2.price_list )),
	0) item_cogs
from
	`tabItem Group` tig,
	`tabQuotation Item` tqi,
	`tabQuotation` tq,
	`tabProduct Bundle` tpb,
	`tabProduct Bundle Item` tpbi,
	`tabItem` ti,
	`tabItem Price` tip
WHERE
	tqi.item_code = tpb.name
	and tq.name = tqi.parent
	and tq.name = '{quotation_no}'
	AND tpb.name = tpbi.parent
	and tpbi.item_code = ti.name
	and ti.item_group = tig.name
	and tip.item_code = tpbi.item_code
	and tip.price_list = tq.selling_price_list
	and EXISTS (
	SELECT
		1
	from
		`tabSingles` ts
	where
		ts.doctype = 'Product Bundle Settings'
		and ts.field = 'default_item_group'
		and ts.value = tqi.item_group)
order by
	tqi.idx,
	tig.name,
	tpbi.item_code""", as_dict=True)
  return items

@frappe.whitelist()
def start_procedure(args):
  if isinstance(args, str):
    args = json.loads(args)
  args = frappe._dict(args)
  allow_start = set_actual_qty(args)

  if allow_start:
    #validate_nursing_tasks(self)

    #self.db_set("status", "In Progress")
    return "success"

  return "insufficient stock"
def set_actual_qty(args):
  allow_negative_stock = frappe.db.get_single_value("Stock Settings", "allow_negative_stock")

  allow_start = True
  warehouse = args.get("custom_warehouse")
  for d in args.get("custom_consumables"):
    d["actual_qty"] = get_stock_qty(d["item_code"], warehouse)
    # validate qty
    if not allow_negative_stock and d["actual_qty"] < d["qty"]:

      allow_start = False
      break

  return allow_start
  

from erpnext.stock.stock_ledger import get_previous_sle
from frappe.utils import nowdate, nowtime

def get_stock_qty(item_code, warehouse):
	return (
		get_previous_sle(
			{
				"item_code": item_code,
				"warehouse": warehouse,
				"posting_date": nowdate(),
				"posting_time": nowtime(),
			}
		).get("qty_after_transaction")
		or 0
	)

@frappe.whitelist()
def get_items_to_create_bundle():
  items = frappe.db.sql(f"""
    select
      (select SUBSTRING_INDEX(concat(concat_ws('|', (select parent_item_group from `tabItem Group` where name = tig.parent_item_group and parent_item_group not in ('All Item Groups', 'Examination')), parent_item_group, name), '|'), '|', 1) from `tabItem Group` tig where name = ti.item_group) as lv1,
      (select SUBSTRING_INDEX(SUBSTRING_INDEX(concat(concat_ws('|', (select parent_item_group from `tabItem Group` where name = tig.parent_item_group and parent_item_group not in ('All Item Groups', 'Examination')), parent_item_group, name), '|'), '|', 2), '|', -1) from `tabItem Group` tig where name = ti.item_group) as lv2,
      (select SUBSTRING_INDEX(SUBSTRING_INDEX(concat(concat_ws('|', (select parent_item_group from `tabItem Group` where name = tig.parent_item_group and parent_item_group not in ('All Item Groups', 'Examination')), parent_item_group, name), '|'), '|', 3), '|', -1) from `tabItem Group` tig where name = ti.item_group) as lv3,
      name, item_name,
      (select price_list_rate from `tabItem Price` tip where tip.price_list = 'Standard Selling' and tip.item_code = ti.item_code and tip.valid_from < curdate() order by tip.valid_from desc limit 1) as rate
    from tabItem as ti
    where ti.custom_product_bundle = 1 and ti.disabled = 0
    order by 1, 2, 3, 4""", as_dict=True)
  return items

@frappe.whitelist()
def get_items_to_create_bundles():
  items = frappe.db.sql(f"""
    (
    select
      3 as idx,
      parent_item_group,
      name,
      is_group
    from
      `tabItem Group` tig
    where
      parent_item_group in (
      select
        name
      from `tabItem Group` tig
      where
        parent_item_group in (
        select
          name
        from
          `tabItem Group` tig
        where
          parent_item_group = 'Examination')))
    union
    (select
    2 as idx,
      parent_item_group,
      name,
      is_group
    from
      `tabItem Group` tig
    where
      parent_item_group in (
      select
        name
      from
        `tabItem Group` tig
      where
        parent_item_group = 'Examination'))
    union
    (select
    1 as idx,
      parent_item_group,
      name,
      is_group
    from
      `tabItem Group` tig
    where
      parent_item_group = 'Examination')
    UNION 
    (select 0, '', 'Examination', 1 from dual)
    order by 1, 2, 4""", as_dict=True)
  return items

import re

def extract_age_from_string(age_string):
    age_pattern = re.compile(r'(\d+) Years?')
    match = age_pattern.match(age_string)
    if match:
        return int(match.group(1))
    else:
        return None
    
@frappe.whitelist()
def create_sample_and_test_from_encounter(enc, selected):
  #if isinstance(selected, str):
  trtrt = json.loads(selected)
  params = ','.join([f"'{s}'" for s in trtrt])
  samples = frappe.db.sql(f"""select sample, sum(sample_qty) qty from `tabLab Test Template` tltt where name in ({params}) group by 1""", as_dict=True)
  enc_doc = frappe.get_doc('Patient Encounter', enc)
  lab = frappe.db.get_value('Branch', enc_doc.custom_branch, 'custom_default_lab')

  lab_doc = frappe.get_doc({
    'doctype': 'Lab Test',
    'custom_appointment': enc_doc.appointment,
    'patient': enc_doc.patient,
    'patient_name': enc_doc.patient_name,
    'patient_age': enc_doc.patient_age,
    'patient_sex': enc_doc.patient_sex,
    'company': enc_doc.company,
    'custom_branch': enc_doc.custom_branch,
    'custom_service_unit': lab,
    'normal_toggle': 1,
    'practitioner': enc_doc.practitioner
  })
  for test in params.replace("'", "").split(','):
    age = extract_age_from_string(enc_doc.patient_age)
    minmax = frappe.db.sql(f"""
      WITH cte AS (
        SELECT
          parent,
          lab_test_event,
          custom_age,
          custom_sex,
          custom_min_value,
          custom_max_value,
          MAX(CASE WHEN custom_age <= {age} THEN custom_age END) OVER (PARTITION BY parent, lab_test_event, custom_sex ORDER BY custom_age DESC) AS max_age
        FROM
          `tabNormal Test Template`
      )
      SELECT
        lab_test_event,
        COALESCE(
          (SELECT custom_min_value FROM cte WHERE parent = '{test}' AND lab_test_event = c.lab_test_event AND custom_sex = '{enc_doc.patient_sex}' AND max_age = {age} order by custom_age desc limit 1),
          (SELECT custom_min_value FROM cte WHERE parent = '{test}' AND lab_test_event = c.lab_test_event AND custom_sex = '{enc_doc.patient_sex}' AND custom_age = (SELECT MAX(max_age) FROM cte WHERE parent = '{test}' AND lab_test_event = c.lab_test_event AND custom_sex = '{enc_doc.patient_sex}' AND max_age < {age}))
        ) AS custom_min_value,
        COALESCE(
          (SELECT custom_max_value FROM cte WHERE parent = '{test}' AND lab_test_event = c.lab_test_event AND custom_sex = '{enc_doc.patient_sex}' AND max_age = {age} order by custom_age desc limit 1),
          (SELECT custom_max_value FROM cte WHERE parent = '{test}' AND lab_test_event = c.lab_test_event AND custom_sex = '{enc_doc.patient_sex}' AND custom_age = (SELECT MAX(max_age) FROM cte WHERE parent = '{test}' AND lab_test_event = c.lab_test_event AND custom_sex = '{enc_doc.patient_sex}' AND max_age < {age}))
        ) AS custom_max_value
      FROM
        cte c
      WHERE
        parent = '{test}'
        AND custom_sex = '{enc_doc.patient_sex}'
      GROUP BY
        lab_test_event;
    """, as_dict=True)
    min_val = 0
    max_val = 0
    for mm in minmax:
      lab_doc.append('normal_test_items', {'lab_test_name': test, 'custom_min_value': mm.custom_min_value, 'custom_max_value': mm.custom_max_value, 'lab_test_event': mm.lab_test_event})
  lab_doc.insert()

  sample_doc = frappe.get_doc({
    'doctype': 'Sample Collection',
    'custom_appointment': enc_doc.appointment,
    'patient': enc_doc.patient,
    'patient_name': enc_doc.patient_name,
    'patient_age': enc_doc.patient_age,
    'patient_sex': enc_doc.patient_sex,
    'company': enc_doc.company,
    'custom_branch': enc_doc.custom_branch,
    'custom_service_unit': lab,
    'custom_lab_test': lab_doc.name
  })
  
  for smpl in samples:
    sample_doc.append('custom_sample_table', {'sample': smpl.sample, 'quantity': smpl.qty})
  print(str(sample_doc))
  sample_doc.insert()

  for item in params.replace("'", "").split(','):
    enc_doc.append ("lab_test_prescription", {'lab_test_code':item, 'lab_test_name': item, 'custom_sample_collection': sample_doc.name, 'custom_lab_test': lab_doc.name})
  enc_doc.save()

  message = {'sample': sample_doc.name, 'lab': lab_doc.name}
  return message

@frappe.whitelist()
def get_items_to_create_lab():
  items = frappe.db.sql(f"""
    select lv2, lv3, name, item_name from (
    select
      (select SUBSTRING_INDEX(concat(concat_ws('|', (select parent_item_group from `tabItem Group` where name = tig.parent_item_group and parent_item_group not in ('All Item Groups', 'Examination')), parent_item_group, name), '|'), '|', 1) from `tabItem Group` tig where name = ti.item_group) as lv1,
      (select SUBSTRING_INDEX(SUBSTRING_INDEX(concat(concat_ws('|', (select parent_item_group from `tabItem Group` where name = tig.parent_item_group and parent_item_group not in ('All Item Groups', 'Examination')), parent_item_group, name), '|'), '|', 2), '|', -1) from `tabItem Group` tig where name = ti.item_group) as lv2,
      (select SUBSTRING_INDEX(SUBSTRING_INDEX(concat(concat_ws('|', (select parent_item_group from `tabItem Group` where name = tig.parent_item_group and parent_item_group not in ('All Item Groups', 'Examination')), parent_item_group, name), '|'), '|', 3), '|', -1) from `tabItem Group` tig where name = ti.item_group) as lv3,
      ti.name, ltt.name item_name
    from tabItem as ti, `tabLab Test Template` as ltt
    where ti.custom_product_bundle = 1 and ti.disabled = 0
    and ltt.item = ti.name
    and ltt.disabled = 0
    order by 1, 2, 3, 4) a WHERE a.lv1 = 'Laboratory'""", as_dict=True)
  return items

@frappe.whitelist()
def create_mr_from_encounter(enc):
  #frappe.throw(enc_doc)
  encdoc = frappe.get_doc('Patient Encounter', enc)
  
  mr_internal_items = frappe.db.sql(f"""
  select drug_code, drug_name, dosage, period, dosage_form, custom_compound_qty
  from `tabDrug Prescription`
  where parent = '{encdoc.name}' and parenttype = 'Patient Encounter' and custom_material_request is null and custom_is_internal = 1 and docstatus = 0
  """, as_dict=True)
  mr_external_items = frappe.db.sql(f"""
  select drug_code, drug_name, dosage, period, dosage_form, custom_compound_qty
  from `tabDrug Prescription`
  where parent = '{encdoc.name}' and parenttype = 'Patient Encounter' and custom_material_request is null and custom_is_internal = 0 and docstatus = 0
  """, as_dict=True)
  pharmacy_warehouse, front_office = frappe.db.get_value('Branch', encdoc.custom_branch, ['custom_default_pharmacy_warehouse', 'custom_default_front_office'])
  message =[pharmacy_warehouse, front_office]
  if(mr_internal_items):
    warehouse = frappe.db.get_value('Healthcare Service Unit', encdoc.custom_service_unit, 'warehouse')
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
    for item in mr_external_items:
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
    frappe.db.sql(f"""update `tabDrug Prescription` set custom_material_request = '{mr_in_doc.name}' where parent = '{encdoc.name}' and parentfield = 'drug_prescription' and parenttype = 'Patient Encounter' and custom_material_request is null and custom_is_internal = 1 and docstatus = 0""")
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
    frappe.db.sql(f"""update `tabDrug Prescription` set custom_material_request = '{mr_ex_doc.name}' where parent = '{encdoc.name}' and parentfield = 'drug_prescription' and parenttype = 'Patient Encounter' and custom_material_request is null and custom_is_internal = 0 and docstatus = 0""")
    message.append(mr_ex_doc.name)
  else: 
    message.append('Empty external')
  return message

@frappe.whitelist()
def create_attendance_from_checkin(from_date, to_date):
  
  pass