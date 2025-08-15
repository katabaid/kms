import frappe, json
from frappe import _

@frappe.whitelist()
def assign_results(selected_rows, practitioner, due_date):
	"""
	Assign selected radiology results to a healthcare practitioner
	
	Args:
		selected_rows (list): List of selected radiology result documents
		practitioner (str): Healthcare Practitioner to assign to
		due_date (str): Due date for the assignment
	
	Returns:
		dict: Count of unchanged, changed, and new documents
	"""
	try:
		doc_names_list = json.loads(selected_rows)
		if not isinstance(doc_names_list, list):
			frappe.throw(_("Invalid format for selected rows."))
	except:
		frappe.throw(_("Failed to parse selected rows. Expected a list of document names."))
	unchanged_rows = 0
	changed_rows = 0
	new_docs = 0
	
	# Get practitioner user
	practitioner_user = frappe.db.get_value("Healthcare Practitioner", practitioner, "user_id")
	if not practitioner_user:
		frappe.throw(_("Healthcare Practitioner {0} does not have a linked user").format(practitioner))
		
	for doc_name in doc_names_list:
		# Check if Result Queue document already exists
		existing_queue = frappe.db.exists("Result Queue", {"doc_name": doc_name})
		
		if existing_queue:
			# Document exists, check assignee
			queue_doc = frappe.get_doc("Result Queue", existing_queue)
			if queue_doc.assignee == practitioner:
				# Assignee is the same, do nothing
				unchanged_rows += 1
			else:
				# Assignee is different, update it
				queue_doc.assignee = practitioner
				queue_doc.user = practitioner_user
				queue_doc.due_date = due_date
				queue_doc.save()
				changed_rows += 1
		else:
			# Create new Result Queue document
			queue_doc = frappe.new_doc("Result Queue")
			queue_doc.doc_type = "Radiology Result"
			queue_doc.doc_name = doc_name
			queue_doc.assignee = practitioner
			queue_doc.user = practitioner_user
			queue_doc.status = "Assigned"
			queue_doc.due_date = due_date
			queue_doc.insert()
			new_docs += 1
	
	# Commit all changes
	frappe.db.commit()
	
	return {
		"unchanged_rows": unchanged_rows,
		"changed_rows": changed_rows,
		"new_docs": new_docs
	}