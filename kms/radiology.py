import frappe
from frappe.utils import now

@frappe.whitelist()
def create_exam(name):
  result = []
  enc = frappe.get_doc('Patient Encounter', name)
  sql = f"""SELECT DISTINCT service_unit, parent
    FROM `tabItem Group Service Unit` tigsu 
    WHERE EXISTS (
      SELECT 1 
      FROM `tabRadiology Result Template` trrt 
      WHERE trrt.item_code = tigsu.parent 
      AND EXISTS (
        SELECT 1 
        FROM `tabRadiology Request` trr 
        WHERE trr.parent = '{enc.name}' 
        and trr.template = trrt.name
      )
    )
    AND branch = '{enc.custom_branch}'"""
  rooms = frappe.db.sql(sql, as_dict = True)
  rooms_map = {}
  for row in rooms:
    room = row['service_unit']
    parent = row['parent']
    rooms_map.setdefault(room,[]).append(parent)
  for room, parents in rooms_map.items():
    doc = frappe.get_doc({
      'doctype': 'Radiology',
      'patient': enc.patient,
      'patient_name': enc.patient_name,
      'patient_sex': enc.patient_sex,
      'patient_age': enc.patient_age,
      'date_of_birth': enc.custom_date_of_birth,
      'patient_company': enc.custom_patient_company,
      'appointment': enc.appointment,
      'patient_encounter': name,
      'company': enc.company,
      'branch': enc.custom_branch,
      'service_unit': room,
      'examination_item': []
    })
    result.append({'room': room, 'items': []})
    for parent in parents:
      template = frappe.db.get_value('Radiology Result Template', {'item_code': parent}, 'name')
      doc.append('examination_item', {'template': template, 'status': 'Started', 'status_time': now()})
      result.append('items', {'item': template})
    doc.insert(ignore_permissions=True)