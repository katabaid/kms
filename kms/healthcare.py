import frappe, json
from frappe.utils import today

@frappe.whitelist()
def create_service(target, source, name, room):
  if target == 'Nurse Examination':
    create_nurse_exam(source, name, room)

def create_nurse_exam(source, name, room):
  if source == 'Dispatcher':
    appt = frappe.db.get_value('Dispatcher', name, 'patient_appointment')
    appt_doc = frappe.get_doc('Patient Appointment', appt) 
    nurse_doc = frappe.get_doc({
      'doctype': 'Nurse Examination',
      'appointment': appt_doc.name,
      'patient': appt_doc.patient,
      'patient_name': appt_doc.patient_name,
      'patient_age': appt_doc.patient_age,
      'patient_sex': appt_doc.patient_sex,
      'company': appt_doc.company,
      'branch': appt_doc.custom_branch,
      'service_unit': room,
      'created_date': today(),
      'expected_result_date': today(),
    })
    nurse_doc.insert()