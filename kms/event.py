import frappe
from frappe.utils import now

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
        "uom": doc.uom})
      sales_item_price.insert()
      frappe.msgprint(f"Item Price added for {doc.item_code} in Price List {custom_hpp_price_list}", alert=True)
    
    #Update exam items related to this raw material in its HPP price list
    values = {'item_code': doc.item_code}
    sales_items = frappe.db.sql("""
      select sum(tcpi.qty*tip.price_list_rate) harga, tltt.item item
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
  if doc.parent_healthcare_service_unit and doc.is_group==0:
    doc.custom_branch = frappe.db.get_value('Healthcare Service Unit', doc.parent_healthcare_service_unit, 'custom_branch')

@frappe.whitelist()
def warn_lab_test_exceed_max(doc, method=None):
  ################Doctype: Lab Test################
  for row in doc.get("normal_test_items"):
    if row.result_value:
      if float(row.result_value) > float(row.custom_max_value):
        frappe.msgprint(f"Result value for {row.lab_test_event} is {row.result_value} which exceeds max value {row.custom_max_value}", alert=True)
      elif float(row.result_value) < float(row.custom_min_value):
        frappe.msgprint(f"Result value for {row.lab_test_event} is {row.result_value} which is less than min value {row.custom_min_value}", alert=True)

@frappe.whitelist()
def update_doctor_result(doc, method=None):
  ################Doctype: Lab Test################
  doctor_result_name = frappe.db.get_value('Doctor Result', {
    'appointment': doc.custom_appointment,
    'docstatus': 0
  }, 'name')
  for item in doc.normal_test_items:
    item_code, item_group = frappe.db.get_value('Item', {'item_name': item.lab_test_name}, ['item_code', 'item_group'])
    mcu_grade_name = frappe.db.get_value('MCU Exam Grade', {
      'hidden_item': item_code,
      'hidden_item_group': item_group,
      'parent': doctor_result_name,
      'examination': item.lab_test_event
    }, 'name')
    incdec = ''
    incdec_category = ''
    if (item.custom_min_value != 0 or item.custom_max_value != 0) and item.custom_min_value and item.custom_max_value and item.result_value:
      incdec = 'Increase' if item.result_value > item.custom_max_value else ('Decrease' if item.result_value < item.custom_min_value else None)
      if incdec:
        incdec_category = frappe.db.get_value('MCU Category', {
          'item_group': item_group,
          'item': item_code,
          'test_name': item.lab_test_event,
          'selection': incdec
        }, 'description')
    frappe.db.set_value('MCU Exam Grade', mcu_grade_name, {
      'result': item.result_value,
      'incdec': incdec,
      'incdec_category': incdec_category,
      'status': doc.status
    })
  for selective in doc.custom_selective_test_result:
    item_code, item_group = frappe.db.get_value('Item', {'item_name': selective.event}, ['item_code', 'item_group'])
    mcu_grade_name = frappe.db.get_value('MCU Exam Grade', {
      'hidden_item': item_code,
      'hidden_item_group': item_group,
      'parent': doctor_result_name,
      'examination': selective.event
    }, 'name')
    frappe.db.set_value('MCU Exam Grade', mcu_grade_name, {
      'result': item.result,
      'status': doc.status
    })

@frappe.whitelist()
def unlink_queue_pooling_before_delete(doc, method=None):
  ################Doctype: Patient Encounter################
  if doc.custom_queue_pooling:
    qp = frappe.get_doc("Queue Pooling", doc.custom_queue_pooling)
    qp.status = "Queued"
    qp.dequeue_time = None
    qp.encounter = None
    qp.healthcare_practitioner = None
    qp.save(ignore_permissions=True)

@frappe.whitelist()
def process_queue_pooling_and_dental(doc, method=None):
  ################Doctype: Patient Encounter################
  if doc.custom_queue_pooling:
    qp = frappe.get_doc("Queue Pooling", doc.custom_queue_pooling)
    qp.status = "Ongoing"
    qp.dequeue_time = frappe.utils.nowtime()
    qp.encounter = doc.name
    qp.healthcare_practitioner = doc.practitioner
    qp.save(ignore_permissions=True)

@frappe.whitelist()
def process_checkin(doc, method=None):
  ################Doctype: Patient Appointment################
  if doc.status == 'Checked In':
    if doc.appointment_date == frappe.utils.nowdate():
      frappe.db.set_value('Temporary Registration', doc.custom_temporary_registration, {'patient_appointment': doc.name, 'status': 'Transferred'})
      dispatcher_user = frappe.db.get_value("Dispatcher Settings", {"branch": doc.custom_branch, 'enable_date': doc.appointment_date}, ['dispatcher'])
      if dispatcher_user and doc.appointment_type == 'MCU':
        exist_docname = frappe.db.get_value('Dispatcher', {'patient_appointment': doc.name}, ['name'])
        if exist_docname: 
          disp_doc = frappe.get_doc('Dispatcher', exist_docname)
          existing_items = {item.examination_item for item in disp_doc.package}
          for entry in doc.custom_additional_mcu_items:
            if entry.examination_item not in existing_items:
              new_entry = entry.as_dict()
              new_entry.name = None
              disp_doc.append('package', new_entry)
              rooms = frappe.get_all('Item Group Service Unit', filters={'parent': entry.examination_item, 'branch': doc.custom_branch}, fields=['service_unit'])
              room_dict = {room.service_unit: room for room in rooms}
              for hsu in disp_doc.assignment_table:
                if hsu.healthcare_service_unit in room_dict:
                  hsu.status = 'Additional or Retest Request'
              notification_doc = frappe.new_doc('Notification Log')
              notification_doc.for_user = dispatcher_user
              notification_doc.from_user = frappe.session.user
              notification_doc.document_type = 'Dispatcher'
              notification_doc.document_name = disp_doc.name
              notification_doc.subject = f"""Patient <strong>{doc.patient_name}</strong> has added additional MCU examination item: {entry.item_name}."""
              notification_doc.insert(ignore_permissions=True)
        else:
          disp_doc = frappe.get_doc({
            'doctype': 'Dispatcher',
            'patient_appointment': doc.name,
            'date': frappe.utils.today(),
            'status': 'In Queue'
          })
          item_with_sort_order = []
          for entry in doc.custom_mcu_exam_items:
            sort_order = frappe.db.get_value('Item', entry.examination_item, 'custom_bundle_position')
            item_with_sort_order.append({
              'item_code': entry.examination_item,
              'item_name': entry.item_name,
              'item_group': entry.item_group,
              'healthcare_service_unit': entry.healthcare_service_unit,
              'status': entry.status,
              'sort_order': sort_order
            })
          sorted_items = sorted(item_with_sort_order, key=lambda x: x['sort_order'])
          for item in sorted_items:
            new_entry = dict()
            new_entry['examination_item'] = item['item_code']
            new_entry['item_name'] = item['item_name']
            new_entry['item_group'] = item['item_group']
            new_entry['healthcare_service_unit'] = item['healthcare_service_unit']
            new_entry['status'] = item['status']
            disp_doc.append('package', new_entry)
          rooms = frappe.db.sql(f"""
            SELECT distinct tigsu.service_unit, thsu.custom_default_doctype
            FROM `tabItem Group Service Unit` tigsu, `tabHealthcare Service Unit` thsu 
            WHERE tigsu.branch = '{doc.custom_branch}'
            AND tigsu.parenttype = 'Item'
            AND tigsu.service_unit = thsu.name 
            AND EXISTS (
            SELECT 1 FROM `tabMCU Appointment` tma
            WHERE tma.parenttype = 'Patient Appointment'
            AND tma.parent = '{doc.name}'
            AND tma.examination_item = tigsu.parent)
            ORDER BY thsu.custom_room, thsu.custom_default_doctype""", as_dict=1)
          for room in rooms:
            new_entry = dict()
            new_entry['name'] = None
            new_entry['healthcare_service_unit'] = room.service_unit
            new_entry['status'] = 'Wait for Room Assignment'
            new_entry['reference_doctype'] = room.custom_default_doctype
            disp_doc.append('assignment_table', new_entry)
        disp_doc.save(ignore_permissions=True)
      else:
        vs_doc = frappe.get_doc(dict(
          doctype = 'Vital Signs',
          patient = doc.patient,
          signs_date = frappe.utils.nowdate(),
          signs_time = frappe.utils.nowtime(),
          appointment = doc.name,
          custom_branch = frappe.db.get_value('Healthcare Service Unit', doc.service_unit, 'custom_branch'),
          vital_signs_note = doc.notes))
        vs_doc.insert(ignore_permissions=True)
    else:
      frappe.throw(title = 'Error', msg="Appointment date must be the same as today's date.", exc='ValidationError')

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
      note = doc.vital_signs_note)).insert(ignore_permissions=True);

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

def set_collector(doc, method=None):
  if not doc.collected_by:
    doc.collected_by = frappe.session.user
  if not doc.collected_time:
    doc.collected_time = frappe.utils.now()

  exam_result = frappe.db.exists('Lab Test', {'custom_sample_collection': doc.name}, 'name')
  if exam_result:
    doc.custom_lab_test = exam_result
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
      sample_reception_doc.save()
      #saved = True
      sample.sample_reception = sample_reception_doc.name
      sample.status_time = now()
  #if saved:
    #doc.save()