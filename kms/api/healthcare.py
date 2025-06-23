import frappe
from frappe.utils import now

@frappe.whitelist()
def set_mqp_meal_time(exam_id):
  mqps = frappe.db.get_all(
    'MCU Queue Pooling', filters={'patient_appointment': exam_id}, pluck='name')
  for mqp in mqps:
    frappe.db.set_value('MCU Queue Pooling', mqp, {'meal_time': now(), 'meal_time_block': 1})