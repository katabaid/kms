import frappe, json

@frappe.whitelist()
def get_bundle_items_to_copy(bundle_id):
  response = frappe.db.sql(f"""SELECT item_code FROM `tabProduct Bundle Item` WHERE parent = '{bundle_id}'""", as_dict=True, pluck='item_code')
  return response

@frappe.whitelist()
def create_bundle_from_quotation(items, name, price_list, party_name, quotation_to):
  #Create Item
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
  
  #Create Product Bundle
  pb_doc = frappe.new_doc("Product Bundle")
  pb_doc.name = item_doc.name
  pb_doc.new_item_code = item_doc.name
  pb_doc.description = name
  if quotation_to == "Lead":
    pb_doc.custom_lead = party_name
  elif quotation_to == "Customer":
    pb_doc.custom_customer = party_name
  
  return item_doc.name
  pass