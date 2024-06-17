import frappe, json
from frappe.utils import today

@frappe.whitelist()
def refuse_to_test(name, selected, reason):
  if isinstance(selected, str):
    selected = json.loads(selected)
  selected_name_values = [item['name'] for item in selected]
  sample_doc = frappe.get_doc('Sample Collection', name)
  count_row = 0
  count_refused = 0
  count_finished = 0
  # Tandai yang refusd di Sample Collection Bulk
  for sample_type in sample_doc.get('custom_sample_table'):
    count_row += 1
    if sample_type.status == 'Refused':
      count_refused += 1
    if sample_type.status == 'Finished':
      count_finished += 1
    if sample_type.name in selected_name_values:
      sample_type.status = 'Refused'
      count_refused += 1
  refuse_all = count_row == count_refused
  partial_finished = count_row == count_refused + count_finished
  if refuse_all:
    sample_doc.custom_status = 'Refused'
  elif partial_finished:
    sample_doc.custom_status = 'Partially Finished'
  sample_doc.save()
  # Cancel Sample Collection
  if refuse_all or partial_finished:
    frappe.db.set_value('Sample Collection', name, 'docstatus', '2')
  # Todo: Tandai exam item yang terpengaruh
  # Todo: Cancel Lab Test
  # Tandai yang refused di Dispatcher
  if sample_doc.custom_dispatcher:
    if refuse_all or partial_finished:
      dispatcher_doc = frappe.get_doc('Dispatcher', sample_doc.custom_dispatcher)
      dispatcher_doc.status = 'In Queue'
      for hsu in dispatcher_doc.get('assignment_table'):
        if hsu.healthcare_service_unit == sample_doc.custom_service_unit:
          hsu.status = 'Refused to Test'
      dispatcher_doc.save()
  # Notifikasi Dispatcher
    notification_doc = frappe.get_doc({
      'doctype': 'Notification Log',
      'for_user': frappe.db.get_value('Dispatcher Settings', {'branch': sample_doc.custom_branch, 'enable_date': today()}, 'dispatcher'),
      'type': 'Alert',
      'document_type': 'Sample Collection',
      'document_name': name,
      'from_user': frappe.session.user,
      'subject': f"""Patient {sample_doc.patient_name} refused to test with reason: {reason}."""
    })
    notification_doc.insert()
    comment_doc = frappe.get_doc({
      'doctype': 'Comment',
      'comment_type': 'Comment',
      'comment_by': frappe.session.user,
      'reference_doctype': 'Dispatcher',
      'reference_name': sample_doc.custom_dispatcher,
      'content': f"""Patient {sample_doc.patient_name} refused to test with reason: {reason}."""
    })
    comment_doc.insert()
  return 'success'