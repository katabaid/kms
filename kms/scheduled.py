import frappe
from frappe.utils import getdate, today, now_datetime, get_datetime
from datetime import timedelta

def set_cancelled_open_appointment():
  appointment = frappe.db.get_list(
    'Patient Appointment', filters={'status': 'Open'}, fields=['name', 'appointment_date'])
  for q in appointment:
    if q['appointment_date'] < getdate(today()):
      frappe.db.set_value('Patient Appointment', q['name'], 'status', 'Cancelled')

def set_open_scheduled_appointment():
  appointment = frappe.db.get_list(
    'Patient Appointment', filters={'status': 'Scheduled'}, fields=['name', 'appointment_date'])
  for q in appointment:
    if q['appointment_date'] == getdate(today()):
      frappe.db.set_value('Patient Appointment', q['name'], 'status', 'Open')

def set_no_show_queue_pooling():
  queue_pooling = frappe.db.get_list(
    'Queue Pooling', filters={'status': 'Scheduled'}, fields=['name', 'date'])
  for q in queue_pooling:
    if q['date'] < getdate(today()):
      frappe.db.set_value('Queue Pooling', q['name'], 'status', 'No Show')

def set_cancelled_timeout_queue_pooling():
  queue_pooling = frappe.db.get_list(
    'Queue Pooling', filters={'status': 'Queued'}, fields=['name', 'date'])
  for q in queue_pooling:
    if q['date'] != getdate(today()):
      frappe.db.set_value('Queue Pooling', q['name'], {
        'status': 'Cancelled', 'cancel_reason': 'Timeout'
      })

def reset_room_assignment():
  frappe.db.sql("UPDATE `tabRoom Assignment` SET assigned = 0, time_sign_out = %s", (now_datetime(),))
  frappe.db.sql("DELETE FROM `tabUser Permission` WHERE allow = 'Healthcare Service Unit'")
  frappe.db.sql("UPDATE FROM `tabDispatcher Room` SET healthcare_practitioner = ''")
  frappe.db.commit()
  #room_assignment = frappe.db.get_list('Room Assignment', filters={'assigned': 1}, pluck='name')
  #for ra in room_assignment:
  #  frappe.db.set_value('Room Assignment', ra, 'assigned', 0)
  #name = frappe.db.get_all('User Permission', pluck = 'user',
  #  filters = {'allow', '=', 'Healthcare Service Unit'})
  #for up in name:
  #  frappe.core.doctype.user_permission.user_permission.clear_user_permissions(
  #    user=up, for_doctype='Healthcare Service Unit')

def reset_meal_status():
  interval = frappe.db.get_single_value('MCU Settings', 'meal_time')
  now = now_datetime()
  def expired(t):
    return get_datetime(t) + timedelta(minutes=interval) < now
  for doctype, filters, field, update in [
    ('Dispatcher', {'status': 'Meal Time'}, 'meal_time', lambda doc: setattr(doc, 'status', 'In Queue')),
    ('MCU Queue Pooling', {'meal_time_block': 1}, 'meal_time', lambda doc: setattr(doc, 'meal_time_block', 0))
  ]:
    for name in frappe.db.get_all(doctype, filters=filters, pluck='name'):
      doc = frappe.get_doc(doctype, name)
      if expired(getattr(doc, field)):
        update(doc)
        doc.save(ignore_permissions=True)

def reset_qp_in_room():
  try:
    affected_rows = frappe.db.sql("""
      UPDATE `tabMCU Queue Pooling` SET in_room = 0, delay_time = NULL
      WHERE delay_time IS NOT NULL AND delay_time <= %s
    """, (now_datetime(),))
    frappe.db.commit()
    frappe.log(f"Reset {affected_rows} rows in MCU Queue Pooling")
  except Exception as e:
    frappe.log_error(f"Failed to reset_qp_in_room: {str(e)}")

def calculate_patient_age():
  try:
    affected_rows = frappe.db.sql("""
      UPDATE tabPatient
      SET custom_age = CONCAT(
          TIMESTAMPDIFF(YEAR, dob, CURDATE()), ' Year(s) ',
          TIMESTAMPDIFF(MONTH, dob, CURDATE()) 
            - TIMESTAMPDIFF(YEAR, dob, CURDATE()) * 12, ' Month(s) ',
          DATEDIFF(
            CURDATE(),
            DATE_ADD(
              DATE_ADD(
                dob,
                INTERVAL TIMESTAMPDIFF(YEAR, dob, CURDATE()) YEAR
              ),
              INTERVAL (
                TIMESTAMPDIFF(MONTH, dob, CURDATE()) 
                - TIMESTAMPDIFF(YEAR, dob, CURDATE()) * 12
              ) MONTH
            )
          ), ' Day(s)'
      );
    """)
    frappe.db.commit()
    frappe.log(f"Reset {affected_rows} rows in MCU Queue Pooling")
  except Exception as e:
    frappe.log_error(f"Failed to update patient age: {str(e)}")