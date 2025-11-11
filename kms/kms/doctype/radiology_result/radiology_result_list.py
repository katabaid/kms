import frappe, json
from frappe import _

@frappe.whitelist()
def assign_results(doc_type, selected_rows, practitioner, due_date):
	doc_names_list = _parse_selected_rows(selected_rows)
	practitioner_user = _get_practitioner_user(practitioner)
	unchanged_rows, changed_rows, new_docs = 0, 0, 0
	for doc_name in doc_names_list:
		existing_queue = frappe.db.exists("Result Queue", {"doc_name": doc_name})
		if existing_queue:
			unchanged, changed = _update_existing_queue(
				existing_queue, practitioner, practitioner_user, due_date, doc_type, doc_name
			)
			unchanged_rows += unchanged
			changed_rows += changed
		else:
			_create_new_queue(doc_type, doc_name, practitioner, practitioner_user, due_date)
			new_docs += 1
	frappe.db.commit()
	return {
		"unchanged_rows": unchanged_rows,
		"changed_rows": changed_rows,
		"new_docs": new_docs
	}

def _parse_selected_rows(selected_rows):
	try:
		doc_names_list = json.loads(selected_rows)
		if not isinstance(doc_names_list, list):
			frappe.throw(_("Invalid format for selected rows."))
		return doc_names_list
	except:
		frappe.throw(_("Failed to parse selected rows. Expected a list of document names."))

def _get_practitioner_user(practitioner):
	practitioner_user = frappe.db.get_value("Healthcare Practitioner", practitioner, "user_id")
	if not practitioner_user:
		frappe.throw(_("Healthcare Practitioner {0} does not have a linked user").format(practitioner))
	return practitioner_user

def _update_existing_queue(
	existing_queue, practitioner, practitioner_user, due_date, doc_type, doc_name
):
	queue_doc = frappe.get_doc("Result Queue", existing_queue)
	if queue_doc.assignee == practitioner:
		return 1, 0
	else:
		queue_doc.assignee = practitioner
		queue_doc.user = practitioner_user
		queue_doc.due_date = due_date
		queue_doc.save()
		frappe.db.set_value(doc_type, doc_name, "assignee", practitioner_user)
		return 0, 1

def _create_new_queue(doc_type, doc_name, practitioner, practitioner_user, due_date):
	queue_doc = frappe.new_doc("Result Queue")
	queue_doc.doc_type = doc_type
	queue_doc.doc_name = doc_name
	queue_doc.assignee = practitioner
	queue_doc.user = practitioner_user
	queue_doc.status = "Assigned"
	queue_doc.due_date = due_date
	queue_doc.healthcare_service_unit = frappe.db.get_value(doc_type, doc_name, "service_unit")
	queue_doc.insert()
	frappe.db.set_value(doc_type, doc_name, "assignee", practitioner_user)