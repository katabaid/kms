import frappe, re
from frappe.utils import now

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
def update_queue_pooling_status(doc, method=None):
  ################Doctype: Patient Encounter################
  if doc.custom_queue_pooling:
    qp = frappe.get_doc("Queue Pooling", doc.custom_queue_pooling)
    qp.status = "Closed"
    qp.save(ignore_permissions=True)

def patient_encounter_on_update(doc, method=None):
  ################Doctype: Patient Encounter################
  if doc.docstatus == 1:
    frappe.db.set_value("Patient Appointment", doc.appointment, "status", "Ready to Check Out")
  else:
    frappe.db.set_value("Patient Appointment", doc.appointment, "status", doc._appointment_status)

def patient_encounter_before_safe(doc, method=None):
  ################Doctype: Patient Encounter################
  doc._appointment_status = frappe.db.get_value('Patient Appointment', doc.appointment, 'status')


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
    vs = doc.custom_vital_signs
    frappe.db.set_value('Vital Signs', vs, 'encounter', doc.name)

@frappe.whitelist()
def update_queue_pooling_status(doc, method=None):
  ################Doctype: Patient Encounter################
  if doc.custom_queue_pooling:
    qp = frappe.get_doc("Queue Pooling", doc.custom_queue_pooling)
    qp.status = "Closed"
    qp.save(ignore_permissions=True)

@frappe.whitelist()
def validate_child_tables(doc, method=None):
  ################Doctype: Patient Encounter################
  if doc.custom_radiology:
    for radiology in doc.custom_radiology:
      if not radiology.status_time:
        radiology.status_time = now()

def update_questionnaire_status(doc):
  # Prevent recursion by checking doc.flags
  if getattr(doc.flags, "update_called", False):
    return
  doc.flags.update_called = True
  doc.set("custom_completed_questionnaire", [])
  # Step 1: Check Questionnaire Template for matching appointment_type
  if doc.appointment_type:
    #questionnaire_templates = frappe.get_all(
    #  "Questionnaire Template",
    #  filters={
    #    "appointment_type": doc.appointment_type, 
    #    'active': 1, 
    #    'internal_questionnaire': 0, 
    #    'item_code': ["is", "null"]
    #  },
    #  fields=["name", "template_name"],
    #  order_by='priority'
    #)
    questionnaire_templates = frappe.db.sql("""
        SELECT name, template_name FROM `tabQuestionnaire Template`
        WHERE appointment_type = %s 
          AND active = 1 
          AND internal_questionnaire = 0 
          AND item_code IS NULL
        ORDER BY priority
    """, (doc.appointment_type,), as_dict=True)
    
    for questionnaire in questionnaire_templates:
      # Append to custom_completed_questionnaire
      is_completed = 0
      if any(detail.template == questionnaire["template_name"] for detail in doc.custom_questionnaire_detail):
        is_completed = 1
      
      doc.append("custom_completed_questionnaire", {
        "template": questionnaire["template_name"],
        "is_completed": is_completed
      })
  # Step 2: Search within custom_mcu_exam_items and custom_additional_mcu_items for matching examination_item
  completed_questionnaires = []  # List to hold completed questionnaires with template and is_completed
  child_tables = ["custom_mcu_exam_items", "custom_additional_mcu_items"]
  for table in child_tables:
    for row in doc.get(table):
      if row.examination_item:
        templates = frappe.get_all(
          "Questionnaire Template",
          filters={"item_code": row.examination_item, 'active': 1, 'internal_questionnaire': 0},
          fields=["template_name"]
        )
        for template_data in templates:
          is_completed = 0
          is_completed = 1 if any(
            detail.template == template_data["template_name"] 
            for detail in doc.custom_questionnaire_detail
          ) else None
          # Add to the completed_questionnaires list
          completed_questionnaires.append({
            "template": template_data["template_name"],
            "is_completed": is_completed
          })
  # Append the completed_questionnaires to custom_completed_questionnaire if not already added
  for completed in completed_questionnaires:
    if not any(q.template == completed["template"] for q in doc.custom_completed_questionnaire):
      doc.append("custom_completed_questionnaire", completed)

def append_temporary_registration_questionnaire(doc):
  doc.set("custom_questionnaire_detail", [])
  if doc.custom_temporary_registration:
    temp_regis = frappe.get_doc('Temporary Registration', doc.custom_temporary_registration)
    for detail in temp_regis.detail:
      detail_dict = {
        k: v for k, v in detail.as_dict().items() 
        if k not in ('name', 'parent', 'parenttype', 'parentfield', 'idx')
      }
      doc.append('custom_questionnaire_detail', detail_dict)

@frappe.whitelist()
def process_checkin(doc, method=None):
  ################Doctype: Patient Appointment################
  if not doc.status:
    doc.status = 'Open'
  if doc.status == 'Checked In' or doc.status == 'Ready to Check Out':
    validate_with_today_date(doc.appointment_date)
    if getattr(doc.flags, "skip_on_update", False):
      return
    doc.flags.skip_on_update = True
    previous_doc = doc.get_doc_before_save()
    if not previous_doc:
      return
    previous_row_count = len(previous_doc.custom_additional_mcu_items)
    current_row_count = len(doc.custom_additional_mcu_items)
    if current_row_count > previous_row_count:
      update_questionnaire_status(doc)
      doc.appointment_time = frappe.utils.nowtime()
      doc.save()
    if str(doc.appointment_date) == frappe.utils.nowdate():
      if doc.custom_temporary_registration:
        frappe.db.set_value(
          'Temporary Registration', 
          doc.custom_temporary_registration, 
          {'patient_appointment': doc.name, 'status': 'Transferred'})
      dispatcher_user = frappe.db.get_value(
        "Dispatcher Settings", 
        {"branch": doc.custom_branch, 'enable_date': doc.appointment_date}, 
        ['dispatcher'])
      if dispatcher_user and doc.appointment_type == 'MCU':
        exist_docname = frappe.db.get_value(
          'Dispatcher', {'patient_appointment': doc.name}, ['name'])
        if exist_docname: 
          disp_doc = frappe.get_doc('Dispatcher', exist_docname)
          if disp_doc.status == 'Finished':
            disp_doc.status = 'In Queue'
          existing_items = {item.examination_item for item in disp_doc.package}
          for entry in doc.custom_additional_mcu_items:
            if entry.examination_item not in existing_items:
              new_entry = entry.as_dict()
              new_entry.name = None
              disp_doc.append('package', new_entry)
              rooms = frappe.get_all(
                'Item Group Service Unit', 
                filters={'parent': entry.examination_item, 'branch': doc.custom_branch}, 
                fields=['service_unit'])
              room_dict = {room.service_unit: room for room in rooms}
              found = False
              row_counter = 0
              row_founder = 0
              for hsu in disp_doc.assignment_table:
                row_counter += 1
                if hsu.healthcare_service_unit in room_dict:
                  hsu.status = 'Additional or Retest Request'
                  found = True
                else:
                  row_founder += 1
              if not found and row_founder == row_counter:
                for room in rooms:
                  reference_doctype = frappe.db.get_value(
                    'Healthcare Service Unit', room.service_unit, 'custom_default_doctype')
                  new_entry = dict()
                  new_entry['name'] = None
                  new_entry['healthcare_service_unit'] = room.service_unit
                  new_entry['status'] = 'Wait for Room Assignment'
                  new_entry['reference_doctype'] = reference_doctype if reference_doctype else None
                  disp_doc.append('assignment_table', new_entry)
              notification_doc = frappe.new_doc('Notification Log')
              notification_doc.for_user = dispatcher_user
              notification_doc.from_user = frappe.session.user
              notification_doc.document_type = 'Dispatcher'
              notification_doc.document_name = disp_doc.name
              notification_doc.subject = f"""Patient <strong>{doc.patient_name}</strong> has """\
                f"""added additional MCU examination item: {entry.item_name}."""
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
            sort_order = frappe.db.get_value(
              'Item', entry.examination_item, 'custom_bundle_position')
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
            SELECT distinct tigsu.service_unit, 
            thsu.custom_default_doctype, thsu.custom_reception_room
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
            if room.custom_default_doctype == 'Sample Collection':
              if not any(row.get('healthcare_service_unit') == room.custom_default_doctype for row in disp_doc.assignment_table):
                new_entry = dict()
                new_entry['name'] = None
                new_entry['healthcare_service_unit'] = room.custom_reception_room
                new_entry['status'] = 'Wait for Sample'
                disp_doc.append('assignment_table', new_entry)
        disp_doc.save(ignore_permissions=True)
      else:
        vs_doc = frappe.get_doc(dict(
          doctype = 'Vital Signs',
          patient = doc.patient,
          signs_date = frappe.utils.nowdate(),
          signs_time = frappe.utils.nowtime(),
          appointment = doc.name,
          custom_branch = doc.custom_branch,
          custom_patient_sex = doc.patient_sex,
          custom_patient_age = doc.patient_age,
          custom_patient_company = doc.custom_patient_company,
          custom_date_of_birth = doc.custom_patient_date_of_birth,
          vital_signs_note = doc.notes))
        vs_doc.insert(ignore_permissions=True)

@frappe.whitelist()
def after_insert_patient_appointment(doc, method=None):
  append_temporary_registration_questionnaire(doc)
  update_questionnaire_status(doc)
  doc.save()

def process_mcu(doc, appt):
  mcu = [item.examination_item for item in appt.custom_mcu_exam_items]
  added_mcu = [item.examination_item for item in appt.custom_additional_mcu_items]
  items_list = mcu + added_mcu
  items = ', '.join(f'"{item}"' for item in items_list)
  sql = f"""SELECT DISTINCT service_unit, thsu.custom_default_doctype 
    FROM `tabItem Group Service Unit` tigsu, `tabHealthcare Service Unit` thsu 
    WHERE parenttype = 'Item' AND parentfield = 'custom_room' AND parent IN ({items})
    AND branch = '{doc.custom_branch}'  AND tigsu.service_unit = thsu.name"""
  rooms = frappe.db.sql(sql, as_dict = True)
  for room in rooms:
    sql = f"""SELECT DISTINCT parent FROM `tabItem Group Service Unit` tigsu
      WHERE service_unit = '{room.service_unit}'
      AND parenttype = 'Item' AND parentfield = 'custom_room'
      AND parent IN ({items})"""
    exam_items = frappe.db.sql(sql, as_dict = True)
    template_doctype = frappe.db.get_value(
      'MCU Relationship',{'examination': room.custom_default_doctype}, 'template')
    exam_doc = frappe.new_doc(room.custom_default_doctype)
    exam_doc.patient = doc.patient
    exam_doc.patient_name = appt.patient_name
    exam_doc.patient_sex = appt.patient_sex
    exam_doc.patient_age = appt.patient_age
    exam_doc.company = doc.company
    if room.custom_default_doctype == 'Sample Collection':
      exam_doc.custom_branch = doc.custom_branch
      exam_doc.custom_status = 'Started'
      exam_doc.custom_document_date = frappe.utils.nowdate()
      exam_doc.custom_appointment = doc.appointment
      exam_doc.custom_service_unit = room.service_unit
      exam_doc.custom_queue_no = ''
      pb = frappe.db.get_value(
        'Product Bundle', 
        appt.mcu, 
        [
          'custom_number_of_yellow_tubes', 
          'custom_number_of_red_tubes', 
          'custom_number_of_purple_tubes', 
          'custom_number_of_blue_tubes'
        ], 
        as_dict = True)
      exam_doc.custom_yellow_tubes = pb.custom_number_of_yellow_tubes
      exam_doc.custom_red_tubes = pb.custom_number_of_red_tubes
      exam_doc.custom_purple_tubes = pb.custom_number_of_purple_tubes
      exam_doc.custom_blue_tubes = pb.custom_number_of_blue_tubes
    else:  
      exam_doc.branch = doc.custom_branch
      exam_doc.status = 'Started'
      exam_doc.queue_no = ''
      exam_doc.appointment = doc.appointment
      exam_doc.service_unit = room.service_unit
      exam_doc.created_date = frappe.utils.nowdate()
    exam_doc.examination_item = []
    exam_doc.result = []
    exam_doc.non_selective_result = []
    exam_doc.custom_examination_item = []
    exam_doc.custom_sample_table = []
    existing_samples = []
    for exam_item in exam_items:
      template_name = frappe.get_all(
        template_doctype, filters = {'item_code': exam_item.parent},  pluck = 'name')
      template = frappe.get_doc(template_doctype, template_name[0])
      if template:
        if room.custom_default_doctype == 'Sample Collection':
          entries = dict()
          entries['template'] = template.name
          entries['item_code'] = exam_item.parent
          exam_doc.append('custom_examination_item', entries) 
          if template.sample not in existing_samples:
            samples = dict()
            samples['sample'] = template.sample
            exam_doc.append('custom_sample_table', samples)
            existing_samples.append(template.sample)
        else:
          entries = dict()
          entries['template'] = template.name
          entries['status'] = 'Started'
          entries['status_time'] = frappe.utils.now()
          exam_doc.append('examination_item', entries)
          if (room.custom_default_doctype == 'Nurse Examination' 
              or room.custom_default_doctype == 'Doctor Examination'):
            if ((hasattr(template, 'result_in_exam') and template.result_in_exam)
              or room.custom_default_doctype == 'Doctor Examination'):
              for result in template.items:
                entries = dict()
                entries['item_code'] = exam_item.parent
                entries['item_name'] = template.item_name
                entries['result_line'] = result.result_text
                entries['normal_value'] = result.normal_value
                entries['mandatory_value'] = result.mandatory_value
                entries['result_options'] = result.result_select
                exam_doc.append('result', entries)
              for non_selective_result in template.normal_items:
                match = re.compile(r'(\d+) Years?').match(appt.patient_age)
                age = int(match.group(1)) if match else None
                if appt.patient_sex == non_selective_result.sex and non_selective_result >= age:
                  entries = dict()
                  entries['item_code'] = exam_item.parent
                  entries['test_name'] = non_selective_result.heading_text
                  entries['test_event'] = non_selective_result.lab_test_event
                  entries['test_uom'] = non_selective_result.lab_test_uom
                  entries['min_value'] = non_selective_result.min_value
                  entries['max_value'] = non_selective_result.max_value
                  exam_doc.append('non_selective_result', entries)
    exam_doc.insert(ignore_permissions=True)

def process_non_mcu(doc, appt, type):
  frappe.get_doc(dict(
    doctype = 'Queue Pooling',
    appointment = doc.appointment,
    appointment_type = appt.appointment_type,
    patient = doc.patient,
    date = frappe.utils.nowdate(),
    arrival_time = frappe.utils.nowtime(),
    status = 'Queued',
    priority = appt.custom_priority,
    vital_sign = doc.name,
    company = doc.company,
    department = appt.department if type == 'Department' else None,
    service_unit = appt.service_unit if type == 'Service Unit' else None,
    branch = doc.custom_branch,
    note = doc.vital_signs_note)).insert(ignore_permissions=True)

def prescription_duration_autoname(doc, method=None):
  ################Doctype: Prescription Duration################
  doc.name = 'Mix ' + doc.custom_uom + ' ' + str(doc.number)

@frappe.whitelist()
def return_to_queue_pooling(doc, method=None):
  ################Doctype: Vital Signs################
  validate_with_today_date(doc.signs_date)
  appt = frappe.get_doc('Patient Appointment', doc.appointment)
  if appt.appointment_for == 'MCU' and appt.mcu:
    process_mcu(doc, appt)
  else:
    process_non_mcu(doc, appt, appt.appointment_for)
  validate_vs_mandatory_fields(doc, ['temperature', 'pulse', 'bp_systolic', 'bp_diastolic'])

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

def validate_with_today_date(validate_date):
  if str(validate_date) != frappe.utils.today():
    frappe.throw(
      title = 'Error', 
      msg=f"Date {validate_date} must be the same as today's date {frappe.utils.today()}.", 
      exc='ValidationError')
    
def validate_vs_mandatory_fields(doc, fields):
  for field in fields:
    label = doc.meta.get_field(field).label
    if not doc.get(field):
      frappe.throw(title=f"{label} is Missing", msg=f"{label} is mandatory.")