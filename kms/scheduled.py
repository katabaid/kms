import frappe

def set_cancelled_open_appointment():
  appointment = frappe.db.get_list('Patient Appointment', filters={'status': 'Open'}, fields=['name', 'appointment_date'])
  for q in appointment:
      if q['appointment_date']<frappe.utils.today():
        doc = frappe.get_doc('Patient Appointment', q['name'])
        doc.status = 'Cancelled'
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