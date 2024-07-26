import frappe, json, ast

@frappe.whitelist()
def get_bundle_items_to_copy(bundle_id):
  response = frappe.db.sql(f"""SELECT item_code FROM `tabProduct Bundle Item` WHERE parent = '{bundle_id}'""", as_dict=True, pluck='item_code')
  return response

@frappe.whitelist()
def create_bundle_from_quotation(items, name, party_name, quotation_to):
  params = convert_to_list(items)
  
  # Create Item
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
  item_doc.insert()
  
  # Fetch bundle positions for all items
  items_with_positions = []
  for item in params:
    position = frappe.db.get_value("Item", item, "custom_bundle_position")
    bundle_position = int(position) if position else 0
    items_with_positions.append((item, bundle_position))
  
  # Sort items based on bundle_position
  items_with_positions.sort(key=lambda x: x[1])
  
  # Create Product Bundle
  pb_doc = frappe.new_doc("Product Bundle")
  pb_doc.name = item_doc.name
  pb_doc.new_item_code = item_doc.name
  pb_doc.description = name
  if quotation_to == "Lead":
    pb_doc.custom_lead = party_name
  elif quotation_to == "Customer":
    pb_doc.custom_customer = party_name
  
  pb_doc.items = []
  for item, _ in items_with_positions:
    description = frappe.db.get_value("Item", item, "description")
    pb_doc.append("items", {
      'parent': item_doc.name,
      'uom': 'Unit',
      'qty': 1,
      'description': description,
      'item_code': item
    })
  
  pb_doc.insert()
  return pb_doc.name

def convert_to_list(input_data):
  if isinstance(input_data, str):
    try:
      # Attempt to convert the string to a list
      result = ast.literal_eval(input_data)
      if isinstance(result, list) and all(isinstance(item, str) for item in result):
        return result
      else:
        raise ValueError("String does not contain a list of strings.")
    except (ValueError, SyntaxError):
      raise ValueError("Invalid input: The string could not be converted to a list of strings.")
  elif isinstance(input_data, list) and all(isinstance(item, str) for item in input_data):
    # Input is already a list of strings
    return input_data
  else:
    raise ValueError("Invalid input: Expected a list of strings or a string representation of a list of strings.")
