import frappe

@frappe.whitelist()
def update_item_price(doc, method=None):
  ################DocType: Item Price################
  if doc.price_list == "Standard Buying":
    custom_hpp_price_list = frappe.db.get_single_value("Selling Settings", "custom_hpp_price_list")
    selling_price_list = frappe.db.get_single_value("Selling Settings", "selling_price_list")
    custom_cogs_multiplying_factor = frappe.db.get_value("Item", doc.item_code, "custom_cogs_multiplying_factor", cache=True) or 1
    custom_cogs_price_list_rate = doc.price_list_rate * custom_cogs_multiplying_factor
    sales_item_price_name = frappe.db.get_value("Item Price", {"item_code": doc.item_code, "price_list": custom_hpp_price_list}, "name")
    
    #Update HPP Price List
    if sales_item_price_name:
      sales_item_price_doc = frappe.get_doc("Item Price", sales_item_price_name)
      if sales_item_price_doc.price_list_rate < custom_cogs_price_list_rate:
        sales_item_price_doc.price_list_rate = custom_cogs_price_list_rate
        sales_item_price_doc.save()
        frappe.msgprint(f"Item Price updated for {doc.item_code} in Price List {custom_hpp_price_list}", alert=True)
    else:
      sales_item_price = frappe.get_doc({
        "doctype": "Item Price",
        "price_list": custom_hpp_price_list,
        "item_code": doc.item_code,
        "currency": doc.currency,
        "price_list_rate": custom_cogs_price_list_rate,
        "uom": doc.stock_uom})
      sales_item_price.insert()
      frappe.msgprint(f"Item Price added for {doc.item_code} in Price List {custom_hpp_price_list}", alert=True)
    
    #Update exam items related to this raw material in its HPP price list
    values = {'item_code': doc.item_code}
    sales_items = frappe.db.sql("""select
                      sum(tcpi.qty*tip.price_list_rate) harga, tltt.item item
                    from
                      `tabClinical Procedure Item` tcpi,
                      `tabLab Test Template` tltt,
                      `tabItem Price` tip
                    where
                      tltt.name in (select parent from `tabClinical Procedure Item` tcpi where tcpi.item_code = %(item_code)s and parenttype = 'Lab Test Template')
                      and tcpi.parenttype = 'Lab Test Template'
                      and tip.price_list = (select value from tabSingles ts WHERE ts.doctype = 'Selling Settings' and field = 'custom_hpp_price_list')
                      and tip.item_code = tcpi.item_code
                      and tltt.name = tcpi.parent
                    group by 2""", values=values, as_dict=1)
    for sales_item in sales_items:
      exam_item_price_name = frappe.db.get_value("Item Price", {"item_code": sales_item.item, "price_list": custom_hpp_price_list}, "name")
      if exam_item_price_name:
        exam_item_price_doc = frappe.get_doc("Item Price", exam_item_price_name)
        if exam_item_price_doc.price_list_rate < sales_item.harga:
          exam_item_price_doc.price_list_rate = sales_item.harga
          exam_item_price_doc.save()
          frappe.msgprint(f"Item Price updated for {sales_item.item} in Price List {custom_hpp_price_list}", alert=True)
      else:
        exam_item_price = frappe.get_doc({
          "doctype": "Item Price", 
          "price_list": custom_hpp_price_list, 
          "item_code": sales_item.item, 
          "currency": doc.currency, 
          "price_list_rate": sales_item.harga, 
          "uom": "Unit"})
        exam_item_price.insert()
        frappe.msgprint(f"Item Price added for {sales_item.item} in Price List {custom_hpp_price_list}", alert=True)
      #update related product bundle to this exam item
      values = {'item_code': sales_item.item}
      pb_items = frappe.db.sql("""SELECT item_code, rate, parent FROM `tabProduct Bundle Item` tpbi WHERE tpbi.item_code = %(item_code)s""", values=values, as_dict=True)
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
        pb_price_name = frappe.db.get_value("Item Price", {"item_code": pb_doc.name, "price_list": custom_hpp_price_list}, "name")
        if pb_price_name:
          pb_price_doc = frappe.get_doc("Item Price", pb_price_name)
          if pb_price_doc.price_list_rate < total_rate:
            pb_price_doc.price_list_rate = total_rate
            pb_price_doc.save()
            frappe.msgprint(f"Item Price updated for {pb_doc.name} in Price List {custom_hpp_price_list}", alert=True)
        else:
          pb_price_doc = frappe.get_doc({
            "doctype": "Item Price", 
            "price_list": custom_hpp_price_list, 
            "item_code": pb_doc.name, 
            "currency": doc.currency, 
            "price_list_rate": total_rate, 
            "uom": "Unit"})
          pb_price_doc.insert()
          frappe.msgprint(f"Item Price added for {pb_doc.name} in Price List {custom_hpp_price_list}", alert=True)                
        pb_selling_price_name = frappe.db.get_value("Item Price", {"item_code": pb_doc.name, "price_list": selling_price_list}, "name")
        if pb_selling_price_name:
          pbs_price_doc = frappe.get_doc("Item Price", pb_selling_price_name)
          if pbs_price_doc.price_list_rate < total_rate + (total_rate * pb_doc.custom_margin / 100):
            pbs_price_doc.price_list_rate = total_rate + (total_rate * pb_doc.custom_margin / 100)
            pbs_price_doc.save()
            frappe.msgprint(f"Item Price updated for {pb_doc.name} in Price List {selling_price_list}", alert=True)
        else:
          pbs_price_doc = frappe.get_doc({
            "doctype": "Item Price", 
            "price_list": selling_price_list, 
            "item_code": pb_doc.name, 
            "currency": doc.currency, 
            "price_list_rate": total_rate + (total_rate * pb_doc.custom_margin / 100), 
            "uom": "Unit"})
          pbs_price_doc.insert()
          frappe.msgprint(f"Item Price added for {pb_doc.name} in Price List {selling_price_list}", alert=True)

@frappe.whitelist()
def update_customer_name(doc, method=None):
  ################DocType: Customer################
  if doc.customer_type not in doc.customer_name and (doc.customer_type == 'PT' or doc.customer_type == 'CV'):
    doc.customer_name = doc.customer_type + ' ' + doc.customer_name
    doc.save()

@frappe.whitelist()
def update_healthcare_service_unit_branch(doc, method=None):
  ################Doctype: Healthcare Service Unit################
  if doc.parent_healthcare_service_unit:
    doc.custom_branch = frappe.db.get_value('Healthcare Service Unit', doc.parent_healthcare_service_unit, 'custom_branch')
    doc.save()

@frappe.whitelist()
def warn_lab_test_exceed_max(doc, method=None):
  ################Doctype: Lab Tes################
  for row in doc.get("normal_test_items"):
    if row.result_value:
      if row.result_value > row.custom_max_value:
        frappe.msgprint(f"Result value for {row.lab_test_event} is {row.result_value} which exceeds max value {row.custom_max_value}", alert=True)
      elif row.result_value < row.custom_min_value:
        frappe.msgprint(f"Result value for {row.lab_test_event} is {row.result_value} which is less than min value {row.custom_min_value}", alert=True)

@frappe.whitelist()
def unlink_queue_pooling_before_delete(doc, method=None):
  ################Doctype: Patient Encounter################
  if doc.custom_queue_pooling:
    qp = frappe.get_doc("Queue Pooling", doc.custom_queue_pooling)
    qp.status = "Queued"
    qp.dequeue_time = None
    qp.encounter = None
    qp.healthcare_practitioner = None
    qp.save()

@frappe.whitelist()
def process_queue_pooling_and_dental(doc, method=None):
  ################Doctype: Patient Encounter################
  if doc.custom_queue_pooling:
    qp = frappe.get_doc("Queue Pooling", doc.custom_queue_pooling)
    qp.status = "Ongoing"
    qp.dequeue_time = frappe.utils.nowtime()
    qp.encounter = doc.name
    qp.healthcare_practitioner = doc.practitioner
    qp.save()
  if doc.medical_department=='Dental':
    prepared_data = [
      {'teeth_type': 'Permanent Teeth', 'location': 'ul', 'position': 18},
      {'teeth_type': 'Permanent Teeth', 'location': 'ul', 'position': 17},
      {'teeth_type': 'Permanent Teeth', 'location': 'ul', 'position': 16},
      {'teeth_type': 'Permanent Teeth', 'location': 'ul', 'position': 15},
      {'teeth_type': 'Permanent Teeth', 'location': 'ul', 'position': 14},
      {'teeth_type': 'Permanent Teeth', 'location': 'ul', 'position': 13},
      {'teeth_type': 'Permanent Teeth', 'location': 'ul', 'position': 12},
      {'teeth_type': 'Permanent Teeth', 'location': 'ul', 'position': 11},
      {'teeth_type': 'Permanent Teeth', 'position': 21, 'location': 'ur'},
      {'teeth_type': 'Permanent Teeth', 'position': 22, 'location': 'ur'},
      {'teeth_type': 'Permanent Teeth', 'position': 23, 'location': 'ur'},
      {'teeth_type': 'Permanent Teeth', 'position': 24, 'location': 'ur'},
      {'teeth_type': 'Permanent Teeth', 'position': 25, 'location': 'ur'},
      {'teeth_type': 'Permanent Teeth', 'position': 26, 'location': 'ur'},
      {'teeth_type': 'Permanent Teeth', 'position': 27, 'location': 'ur'},
      {'teeth_type': 'Permanent Teeth', 'position': 28, 'location': 'ur'},
      {'teeth_type': 'Permanent Teeth', 'position': 48, 'location': 'll'},
      {'teeth_type': 'Permanent Teeth', 'position': 47, 'location': 'll'},
      {'teeth_type': 'Permanent Teeth', 'position': 46, 'location': 'll'},
      {'teeth_type': 'Permanent Teeth', 'position': 45, 'location': 'll'},
      {'teeth_type': 'Permanent Teeth', 'position': 44, 'location': 'll'},
      {'teeth_type': 'Permanent Teeth', 'position': 43, 'location': 'll'},
      {'teeth_type': 'Permanent Teeth', 'position': 42, 'location': 'll'},
      {'teeth_type': 'Permanent Teeth', 'position': 41, 'location': 'll'},
      {'teeth_type': 'Permanent Teeth', 'position': 31, 'location': 'lr'},
      {'teeth_type': 'Permanent Teeth', 'position': 32, 'location': 'lr'},
      {'teeth_type': 'Permanent Teeth', 'position': 33, 'location': 'lr'},
      {'teeth_type': 'Permanent Teeth', 'position': 34, 'location': 'lr'},
      {'teeth_type': 'Permanent Teeth', 'position': 35, 'location': 'lr'},
      {'teeth_type': 'Permanent Teeth', 'position': 36, 'location': 'lr'},
      {'teeth_type': 'Permanent Teeth', 'position': 37, 'location': 'lr'},
      {'teeth_type': 'Permanent Teeth', 'position': 38, 'location': 'lr'},
      {'teeth_type': 'Primary Teeth', 'position': 55, 'location': 'ul'},
      {'teeth_type': 'Primary Teeth', 'position': 54, 'location': 'ul'},
      {'teeth_type': 'Primary Teeth', 'position': 53, 'location': 'ul'},
      {'teeth_type': 'Primary Teeth', 'position': 52, 'location': 'ul'},
      {'teeth_type': 'Primary Teeth', 'position': 51, 'location': 'ul'},
      {'teeth_type': 'Primary Teeth', 'position': 61, 'location': 'ur'},
      {'teeth_type': 'Primary Teeth', 'position': 62, 'location': 'ur'},
      {'teeth_type': 'Primary Teeth', 'position': 63, 'location': 'ur'},
      {'teeth_type': 'Primary Teeth', 'position': 64, 'location': 'ur'},
      {'teeth_type': 'Primary Teeth', 'position': 65, 'location': 'ur'},
      {'teeth_type': 'Primary Teeth', 'position': 85, 'location': 'll'},
      {'teeth_type': 'Primary Teeth', 'position': 84, 'location': 'll'},
      {'teeth_type': 'Primary Teeth', 'position': 83, 'location': 'll'},
      {'teeth_type': 'Primary Teeth', 'position': 82, 'location': 'll'},
      {'teeth_type': 'Primary Teeth', 'position': 81, 'location': 'll'},
      {'teeth_type': 'Primary Teeth', 'position': 71, 'location': 'lr'},
      {'teeth_type': 'Primary Teeth', 'position': 72, 'location': 'lr'},
      {'teeth_type': 'Primary Teeth', 'position': 73, 'location': 'lr'},
      {'teeth_type': 'Primary Teeth', 'position': 74, 'location': 'lr'},
      {'teeth_type': 'Primary Teeth', 'position': 75, 'location': 'lr'},
    ]
    for data in prepared_data:
      child = doc.append('custom_dental_detail', {})
      child.teeth_type = data['teeth_type']
      child.position = data['position']
      child.location = data['location']
    doc.save()

@frappe.whitelist()
def process_checkin(doc, method=None):
  ################Doctype: Patient Appointment################
  if doc.status == 'Checked In':
    if doc.appointment_date == frappe.utils.nowdate():
      if frappe.db.exists("Dispatcher Settings", {"branch": doc.custom_branch, 'enable_date': doc.appointment_date}) and doc.appointment_type == 'MCU':
        disp_doc = frappe.get_doc({
          'doctype': 'Dispatcher',
          'patient_appointment': doc.name,
          'date': frappe.utils.today(),
          'status': 'In Queue'
        })
        for entry in doc.custom_mcu_exam_items:
          new_entry = entry.as_dict()
          new_entry.name = None
          disp_doc.append('package', new_entry)
        values = {'appt': doc.name, 'branch': doc.custom_branch}
        rooms = frappe.db.sql("""select distinct tigsu.service_unit 
          from `tabMCU Appointment` tma, `tabItem Group Service Unit` tigsu
          where tma.parent = %(appt)s
          and tma.parenttype = 'Patient Appointment'
          and tma.examination_item = tigsu.parent
          and tigsu.branch = %(branch)s
          and tigsu.parenttype = 'Item'""", values=values, as_dict=1)
        for room in rooms:
          new_entry = dict()
          new_entry['name'] = None
          new_entry['healthcare_service_unit'] = room.service_unit
          new_entry['status'] = 'Wait for Room Assignment'
          disp_doc.append('assignment_table', new_entry)
        disp_doc.save()
      else:
        vs_doc = frappe.get_doc(dict(
          doctype = 'Vital Signs',
          patient = doc.patient,
          signs_date = frappe.utils.nowdate(),
          signs_time = frappe.utils.nowtime(),
          appointment = doc.name,
          custom_branch = frappe.db.get_value('Healthcare Service Unit', doc.service_unit, 'custom_branch'),
          vital_signs_note = doc.notes)).insert();
        vs_doc.save();
    else:
      frappe.throw("Appointment date must be the same as today's date.")

@frappe.whitelist()
def return_to_queue_pooling(doc, method=None):
  ################Doctype: Vital Signs################
  if doc.signs_date == frappe.utils.nowdate():
    frappe.get_doc(dict(
      doctype = 'Queue Pooling',
      vital_sign = doc.name,
      patient = doc.patient,
      date = frappe.utils.nowdate(),
      status = 'Queued',
      appointment = doc.appointment,
      company = doc.company,
      branch = doc.custom_branch,
      service_unit = frappe.db.get_value('Patient Appoinment', doc.appointment, 'service_unit'),
      note = doc.vital_signs_note)).insert();

@frappe.whitelist()
def update_rate_amount_after_amend(doc, method=None):
  ################DocType: Quotation################
  if doc.amended_from:
    for item in doc.items:
      rate = frappe.db.get_value('Product Bundle', item.item_code, 'custom_rate')
      item.rate = rate
      item.amount = item.qty * rate

@frappe.whitelist()
def reset_status_after_amend(doc, method=None):
  ################DocType: Sample Collection################
  if doc.amended_from:
    doc.custom_status = 'Started'
    doc.collected_by = ''
    doc.collected_time = ''
    for item in doc.custom_sample_table:
      item.status = 'Started'
    doc.save()
