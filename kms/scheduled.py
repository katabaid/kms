import frappe, json
from frappe.utils import now, get_datetime

def set_cancelled_open_appointment():
  appointment = frappe.db.get_list('Patient Appointment', filters={'status': 'Open'}, fields=['name', 'appointment_date'])
  today = frappe.utils.getdate(frappe.utils.today())
  for q in appointment:
      if q['appointment_date'] < today:
        doc = frappe.get_doc('Patient Appointment', q['name'])
        doc.status = 'Cancelled'
        doc.save()

def set_open_scheduled_appointment():
  appointment = frappe.db.get_list('Patient Appointment', filters={'status': 'Scheduled'}, fields=['name', 'appointment_date'])
  today = frappe.utils.getdate(frappe.utils.today())
  for q in appointment:
      if q['appointment_date'] == today:
        doc = frappe.get_doc('Patient Appointment', q['name'])
        doc.status = 'Open'
        doc.save()

def set_no_show_queue_pooling():
  queue_pooling = frappe.db.get_list('Queue Pooling', filters={'status': 'Scheduled'}, fields=['name', 'date'])
  for q in queue_pooling:
    if q['date']<frappe.utils.today():
      doc = frappe.get_doc('Queue Pooling', q['name'])
      doc.status = 'No Show'
      doc.save()

def set_cancelled_timeout_queue_pooling():
  queue_pooling = frappe.db.get_list('Queue Pooling', filters={'status': 'Queued'}, fields=['name', 'date'])
  for q in queue_pooling:
    if q['date']!=frappe.utils.today():
      doc = frappe.get_doc('Queue Pooling', q['name'])
      doc.status = 'Cancelled'
      doc.cancel_reason = 'Timeout'
      doc.save()

def reset_dispatcher_status():
  d = frappe.db.get_all('Dispatcher', filters={'status': 'Meal Time'}, pluck='name')
  for q in d:
    dispatcher = frappe.get_doc('Dispatcher', q)
    if get_datetime("2025-01-22 14:25:00") <= get_datetime(now()):
      dispatcher.status = "In Queue"
      dispatcher.save(ignore_permissions=True)