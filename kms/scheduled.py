import frappe
from frappe.utils import now_datetime, get_datetime
from datetime import timedelta

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

def reset_room_assignment():
  room_assignment = frappe.db.get_list('Room Assignment', filters={'assigned': 1}, pluck='name')
  for ra in room_assignment:
    frappe.db.set_value('Room Assignment', ra, 'assigned', 0)
  name = frappe.db.get_all('User Permission', 
    filters = {'allow', '=', 'Healthcare Service Unit'},
    pluck = 'name')
  for up in name:
    frappe.db.delete('User Permission', {'name': up})


def reset_meal_status():
  interval = frappe.db.get_single_value('MCU Settings', 'meal_time')
  now = now_datetime()
  def expired(t):
    return get_datetime(t) + timedelta(minutes=interval) < now
  for doctype, filters, field, update in [
    ('Dispatcher', {'status': 'Meal Time'}, 'meal_time', lambda doc: setattr(doc, 'status', 'In Queue')),
    ('MCU Queue Pooling', {'is_meal_time': 1}, 'meal_time', lambda doc: setattr(doc, 'is_meal_time', 0))
  ]:
    for name in frappe.db.get_all(doctype, filters=filters, pluck='name'):
      doc = frappe.get_doc(doctype, name)
      if expired(getattr(doc, field)):
        update(doc)
        doc.save(ignore_permissions=True)

def reset_qp_in_room():
  try:
    affected_rows = frappe.db.sql("""
      UPDATE `tabMCU Queue Pooling`
      SET in_room = 0, delay_time = NULL
      WHERE delay_time IS NOT NULL AND delay_time <= %s
    """, (frappe.utils.now_datetime(),))
    frappe.db.commit()
    frappe.log(f"Reset {affected_rows} rows in MCU Queue Pooling")
  except Exception as e:
    frappe.log_error(f"Failed to reset_qp_in_room: {str(e)}")