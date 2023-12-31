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
def create_product_bundle_from_quotation(items, name, price_list, party_name, quotation_to):
  if isinstance(items, str):
    items = json.loads(items)
  item_name = ''
# Create Item from selected checkboxes
  item_doc = frappe.new_doc("Item")
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
  pb_doc.custom_price_list = price_list
# Calculate rate from items
  total_rate = 0
  rate = 0
  uom=""
  pb_doc.items = []
  for i in items:
    rate = frappe.db.get_value("Item Price", {"item_code": i["item_code"], "price_list": price_list}, "price_list_rate")
    uom = frappe.db.get_value("Item", i["item_code"], "stock_uom")
    msg = i["description"]
    i["uom"] = uom
    if rate is None:
      rate = 0
    i["rate"] = rate
    i["parent"] = item_doc.name
    total_rate = total_rate + rate
    pb_doc.append("items", i)
  pb_doc.custom_rate = total_rate
  pb_doc.custom_margin = 0
  pb_doc.custom_enable = 0
  pb_doc.insert();
  message = frappe.get_doc('Product Bundle', pb_doc.name)
  return message

@frappe.whitelist()
def get_quotation_item(quotation_no):
  items = frappe.db.sql(f"""select
	tqi.idx,
	tig.name item_group,
	concat(tqi.description, ": ", tpb.name) bundle_name,
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
