import frappe, json
from frappe.utils import today

@frappe.whitelist()
def create_service(target, source, name, room):
  if target == 'Nurse Examination':
    result = create_nurse_exam(source, name, room)
  elif target == 'Radiology':
    result = create_radiology_exam(source, name, room)
  else:
    frappe.throw(f"Unsupported target: {target}")
  if result:
    return result
  else:
    frappe.throw("Failed to create service.")

def create_nurse_exam(source, name, room):
  if source == 'Dispatcher':
    appt = frappe.db.get_value('Dispatcher', name, 'patient_appointment')
    appt_doc = frappe.get_doc('Patient Appointment', appt) 
    nurse_doc = frappe.get_doc({
      'doctype': 'Nurse Examination',
      'appointment': appt_doc.name,
      'patient': appt_doc.patient,
      'patient_name': appt_doc.patient_name,
      'company': appt_doc.company,
      'branch': appt_doc.custom_branch,
      'dispatcher': name,
      'service_unit': room,
      'created_date': today(),
      'expected_result_date': today(),
      'status': 'Started'
    })
    exam_items = frappe.db.sql(f"""SELECT tnet.name, tnet.item_code 
      from `tabMCU Appointment` tma, `tabItem Group Service Unit` tigsu, `tabNurse Examination Template` tnet
      where tma.parenttype = 'Dispatcher'
      and tma.parentfield = 'package'
      and tma.parent = '{name}'
      AND tnet.item_code = tma.examination_item
      and tigsu.parenttype = 'Item Group'
      and tigsu.parentfield = 'custom_units'
      and tigsu.parent = tma.item_group
      and tigsu.branch = '{appt_doc.custom_branch}'
      and tigsu.service_unit = '{room}'""", as_dict=True)
    if exam_items:
      for exam_item in exam_items:
        nurse_doc.append('examination_item', {'template': exam_item.name})
        net_doc = frappe.get_doc('Nurse Examination Template', exam_item.name)

        selectives = net_doc.get('items')
        if selectives:
          for selective in selectives:
            nurse_doc.append('result', {'result_line': selective.result_text, 'normal_value': selective.normal_value, 'result_check': selective.normal_value, 'item_code': exam_item.item_code, 'result_options': selective.result_select})
        non_selectives = net_doc.get('normal_items')
        if non_selectives:
          for non_selective in non_selectives:
            nurse_doc.append('non_selective_result', {'test_name': non_selective.heading_text, 'test_event': non_selective.lab_test_event, 'test_uom': non_selective.lab_test_uom, 'min_value': non_selective.min_value, 'max_value': non_selective.max_value})
      nurse_doc.insert()
      return {'docname': nurse_doc.name}
    else:
      frappe.throw("No Template found.")
  else:
    frappe.throw(f"Unsupported source: {source}")
def create_radiology_exam(source, name, room):
  if source == 'Dispatcher':
    appt = frappe.db.get_value('Dispatcher', name, 'patient_appointment')
    appt_doc = frappe.get_doc('Patient Appointment', appt) 
    radiology_doc = frappe.get_doc({
      'doctype': 'Radiology',
      'appointment': appt_doc.name,
      'patient': appt_doc.patient,
      'patient_name': appt_doc.patient_name,
      'company': appt_doc.company,
      'branch': appt_doc.custom_branch,
      'dispatcher': name,
      'service_unit': room,
      'created_date': today(),
      'expected_result_date': today(),
      'status': 'Started'
    })
    exam_items = frappe.db.sql(f"""SELECT trrt.name, trrt.item_code 
      from `tabMCU Appointment` tma, `tabItem Group Service Unit` tigsu, `tabRadiology Result Template` trrt
      where tma.parenttype = 'Dispatcher'
      and tma.parentfield = 'package'
      and tma.parent = '{name}'
      and tigsu.parenttype = 'Item Group'
      and tigsu.parentfield = 'custom_units'
      and tigsu.parent = tma.item_group
      and tigsu.branch = '{appt_doc.custom_branch}'
      and tigsu.service_unit = '{room}'
      and trrt.item_code = tma.examination_item""", as_dict=True)
    if exam_items:
      for exam_item in exam_items:
        radiology_doc.append('examination_item', {'template': exam_item.name})
        rrt_doc = frappe.get_doc('Radiology Result Template', exam_item.name)
        selectives = rrt_doc.get('items')
        if selectives:
          for selective in selectives:
            radiology_doc.append('result', {'result_line': selective.result_text, 'normal_value': selective.normal_value, 'result_check': selective.normal_value, 'item_code': exam_item.item_code, 'result_options': selective.result_select})
      radiology_doc.insert()
      return {'docname': radiology_doc.name}
    else:
      frappe.throw("No Template found.")
  else:
    frappe.throw(f"Unsupported source: {source}")