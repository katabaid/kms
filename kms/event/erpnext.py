import frappe

@frappe.whitelist()
def update_item_price(doc, method=None):
  ################DocType: Item Price################
  if doc.price_list == "Standard Buying":
    custom_hpp_price_list = frappe.db.get_single_value("Selling Settings", "custom_hpp_price_list")
    selling_price_list = frappe.db.get_single_value("Selling Settings", "selling_price_list")
    custom_cogs_multiplying_factor = frappe.db.get_value(
      "Item", 
      doc.item_code, 
      "custom_cogs_multiplying_factor", 
      cache=True) or 1
    custom_cogs_price_list_rate = doc.price_list_rate * custom_cogs_multiplying_factor
    sales_item_price_name = frappe.db.get_value(
      "Item Price", 
      {"item_code": doc.item_code, "price_list": custom_hpp_price_list}, 
      "name")
    
    #Update HPP Price List
    if sales_item_price_name:
      sales_item_price_doc = frappe.get_doc("Item Price", sales_item_price_name)
      if sales_item_price_doc.price_list_rate < custom_cogs_price_list_rate:
        sales_item_price_doc.price_list_rate = custom_cogs_price_list_rate
        sales_item_price_doc.save()
        frappe.msgprint(
          f"Item Price updated for {doc.item_code} in Price List {custom_hpp_price_list}", 
          alert=True)
    else:
      sales_item_price = frappe.get_doc({
        "doctype": "Item Price",
        "price_list": custom_hpp_price_list,
        "item_code": doc.item_code,
        "currency": doc.currency,
        "price_list_rate": custom_cogs_price_list_rate,
        "uom": doc.uom})
      sales_item_price.insert()
      frappe.msgprint(
        f"Item Price added for {doc.item_code} in Price List {custom_hpp_price_list}", 
        alert=True)
    
    #Update exam items related to this raw material in its HPP price list
    values = {'item_code': doc.item_code}
    sales_items = frappe.db.sql("""
      select sum(tcpi.qty*tip.price_list_rate) harga, tltt.item item
      from
        `tabClinical Procedure Item` tcpi,
        `tabLab Test Template` tltt,
        `tabItem Price` tip
      where
        tltt.name in (select parent from `tabClinical Procedure Item` tcpi 
          where tcpi.item_code = %(item_code)s and parenttype = 'Lab Test Template')
        and tcpi.parenttype = 'Lab Test Template'
        and tip.price_list = (select value from tabSingles ts 
          WHERE ts.doctype = 'Selling Settings' and field = 'custom_hpp_price_list')
        and tip.item_code = tcpi.item_code
        and tltt.name = tcpi.parent
      group by 2""", values=values, as_dict=1)
    for sales_item in sales_items:
      exam_item_price_name = frappe.db.get_value(
        "Item Price", 
        {"item_code": sales_item.item, "price_list": custom_hpp_price_list}, 
        "name")
      if exam_item_price_name:
        exam_item_price_doc = frappe.get_doc("Item Price", exam_item_price_name)
        if exam_item_price_doc.price_list_rate < sales_item.harga:
          exam_item_price_doc.price_list_rate = sales_item.harga
          exam_item_price_doc.save()
          frappe.msgprint(
            f"Item Price updated for {sales_item.item} in Price List {custom_hpp_price_list}", 
            alert=True)
      else:
        exam_item_price = frappe.get_doc({
          "doctype": "Item Price", 
          "price_list": custom_hpp_price_list, 
          "item_code": sales_item.item, 
          "currency": doc.currency, 
          "price_list_rate": sales_item.harga, 
          "uom": "Unit"})
        exam_item_price.insert()
        frappe.msgprint(
          f"Item Price added for {sales_item.item} in Price List {custom_hpp_price_list}", 
          alert=True)
      #update related product bundle to this exam item
      values = {'item_code': sales_item.item}
      pb_items = frappe.db.sql(
        """SELECT item_code, rate, parent FROM `tabProduct Bundle Item` tpbi WHERE tpbi.item_code = %(item_code)s""", 
        values=values, 
        as_dict=True)
      for pb_item in pb_items:
        pb_doc = frappe.get_doc('Product Bundle', pb_item.parent)
        total_rate = 0
        for pb_doc_item in pb_doc.items:
          if pb_doc_item.item_code == sales_item.item:
            total_rate = total_rate + sales_item.harga
            if pb_doc_item.rate < sales_item.harga:
              pb_doc_item.rate = sales_item.harga
          else:
            total_rate = total_rate + pb_doc_item.rate
        pb_doc.custom_rate = total_rate + (total_rate * pb_doc.custom_margin / 100)
        pb_doc.save()
        #get hpp price list for product Bundle
        pb_price_name = frappe.db.get_value(
          "Item Price", 
          {"item_code": pb_doc.name, "price_list": custom_hpp_price_list}, 
          "name")
        if pb_price_name:
          pb_price_doc = frappe.get_doc("Item Price", pb_price_name)
          if pb_price_doc.price_list_rate < total_rate:
            pb_price_doc.price_list_rate = total_rate
            pb_price_doc.save()
            frappe.msgprint(
              f"Item Price updated for {pb_doc.name} in Price List {custom_hpp_price_list}", 
              alert=True)
        else:
          pb_price_doc = frappe.get_doc({
            "doctype": "Item Price", 
            "price_list": custom_hpp_price_list, 
            "item_code": pb_doc.name, 
            "currency": doc.currency, 
            "price_list_rate": total_rate, 
            "uom": "Unit"})
          pb_price_doc.insert()
          frappe.msgprint(
            f"Item Price added for {pb_doc.name} in Price List {custom_hpp_price_list}", 
            alert=True)                
        pb_selling_price_name = frappe.db.get_value(
          "Item Price", 
          {"item_code": pb_doc.name, "price_list": selling_price_list}, 
          "name")
        if pb_selling_price_name:
          pbs_price_doc = frappe.get_doc("Item Price", pb_selling_price_name)
          if pbs_price_doc.price_list_rate < total_rate + (total_rate * pb_doc.custom_margin / 100):
            pbs_price_doc.price_list_rate = total_rate + (total_rate * pb_doc.custom_margin / 100)
            pbs_price_doc.save()
            frappe.msgprint(
              f"Item Price updated for {pb_doc.name} in Price List {selling_price_list}", 
              alert=True)
        else:
          pbs_price_doc = frappe.get_doc({
            "doctype": "Item Price", 
            "price_list": selling_price_list, 
            "item_code": pb_doc.name, 
            "currency": doc.currency, 
            "price_list_rate": total_rate + (total_rate * pb_doc.custom_margin / 100), 
            "uom": "Unit"})
          pbs_price_doc.insert()
          frappe.msgprint(
            f"Item Price added for {pb_doc.name} in Price List {selling_price_list}", 
            alert=True)

@frappe.whitelist()
def update_customer_name(doc, method=None):
  ################DocType: Customer################
  if doc.customer_type not in doc.customer_name and (doc.customer_type == 'PT' or doc.customer_type == 'CV'):
    doc.customer_name = doc.customer_type + ' ' + doc.customer_name
    doc.save()

@frappe.whitelist()
def set_has_attachment(doc, method=None):
  if (
    doc.attached_to_doctype and doc.attached_to_name and 
    (
      doc.attached_to_doctype == 'Radiology' or 
      doc.attached_to_doctype == 'Radiology Result' or 
      doc.attached_to_doctype == 'Nurse Result' or 
      doc.attached_to_doctype == 'Nurse Examination')
  ):
    if method == 'after_insert':
      frappe.db.set_value(
        doc.attached_to_doctype, 
        doc.attached_to_name,
        'has_attachment',
        1
      )
    elif method == 'on_trash':
      attachments = frappe.get_all('File', filters={
        'attached_to_doctype': doc.attached_to_doctype,
        'attached_to_name': doc.attached_to_name,
        'name': ['!=', doc.name]
      })
      has_attachment = 1 if attachments else 0
      frappe.db.set_value(
        doc.attached_to_doctype, 
        doc.attached_to_name,
        'has_attachment',
        has_attachment
      )

def on_submit_material_request(doc, method=None):
  ################Doctype: Material Request################
  if doc.material_request_type == 'Medication Prescription':
    if doc.custom_patient_encounter:
      pe = frappe.get_doc('Patient Encounter', doc.custom_patient_encounter)
      if pe.docstatus == 0:
        items_dict = {item.item_code: item for item in doc.items}
        updated_rows = 0
        for dp in pe.drug_prescription:
          if dp.drug_code in items_dict:
            dp.custom_status = 'On Process'
            updated_rows += 1
        if updated_rows > 0:
          pe.save(ignore_permissions=True)
          frappe.msgprint(f"{updated_rows} rows in drug_prescription updated to 'On Process'.")

@frappe.whitelist()
def update_rate_amount_after_amend(doc, method=None):
  ################DocType: Quotation################
  if doc.amended_from:
    for item in doc.items:
      rate = frappe.db.get_value('Product Bundle', item.item_code, 'custom_rate')
      item.rate = rate
      item.amount = item.qty * rate

def item_before_save(doc, method=None):
  ################DocType: Item################
  if doc.is_new():
    doc.item_code = doc.name

def sales_invoice_on_submit(doc, method=None):
  ################DocType: Sales Invoice################
  if doc.patient:
    pa_doc = frappe.get_doc('Patient Appointment', doc.custom_exam_id)
    pa_doc.status = 'Closed'
    pa_doc.save(ignore_permissions=True)