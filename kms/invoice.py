import frappe

@frappe.whitelist()
def get_appointments_for_invoice(doctype, txt, searchfield, start, page_len, filters, appt_type_code=None):
	"""
	Fetches Patient Appointments suitable for invoicing for MultiSelectDialog.
	Uses appt_type_code to determine appointment type filtering.
	Handles search and pagination.
	"""
	# Extract filters from the filters dictionary (excluding appointment_type)
	patient = filters.get("patient") if filters else None
	custom_type = filters.get("custom_type") if filters else None
	custom_patient_company = filters.get("custom_patient_company") if filters else None
	status = filters.get("status") if filters else None
	appointment_type = filters.get("at") if filters else None

	query_filters = {}

	# Apply standard filters from the filters dict
	if patient:
		query_filters["patient"] = patient
	if custom_type:
		query_filters["custom_type"] = custom_type
	if custom_patient_company:
		query_filters["custom_patient_company"] = custom_patient_company
	if appointment_type:
		appt_type_code = "IS_MCU"

	# Apply status filter, defaulting to 'Checked Out' if not provided
	query_filters["status"] = status or "Checked Out"

	# Decode appt_type_code to set the appointment_type filter
	if appt_type_code == "IS_MCU":
		query_filters["appointment_type"] = "MCU"
	elif appt_type_code == "NOT_MCU":
		query_filters["appointment_type"] = ["!=", "MCU"]
	elif appt_type_code:
		# Use the specific type string directly
		query_filters["appointment_type"] = appt_type_code
	else:
		# Fallback if no type code is received (should default to NOT_MCU from JS)
		query_filters["appointment_type"] = ["!=", "MCU"]


	# Add search term filter if provided
	# Assuming search applies to the 'name' field or relevant fields like patient name
	if txt:
		# Example: Searching by appointment name or patient name (adjust as needed)
		query_filters["name"] = ["like", f"%{txt}%"]
		# Or search multiple fields:
		# query_filters = [
		#     ["Patient Appointment", "status", "=", "Checked Out"],
		#     ["Patient Appointment", "appointment_type", "!=", "MCU"],
		#     ["Patient Appointment", "name", "like", f"%{txt}%"]
		# ]
		# if patient:
		#     query_filters.append(["Patient Appointment", "patient", "=", patient])

	appointments = frappe.get_all(
		"Patient Appointment",
		filters=query_filters,
		fields=[
			"name",
      "patient",
			"appointment_type",
			"appointment_date",
			"custom_type",
			"custom_patient_company"
		],
		order_by="appointment_date desc",
		start=start,
		page_length=page_len
	)
	return appointments

@frappe.whitelist()
def get_invoice_item_from_encounter(exam_id):
  sql = f"""
    SELECT tpe.title, tpe.patient, tpe.practitioner, custom_service_unit,
    CASE tpa.custom_type
    WHEN 'Personal' THEN (SELECT customer FROM tabPatient tp WHERE tp.name = tpe.patient)
    WHEN 'Bill to Company' THEN (SELECT custom_company FROM tabPatient tp WHERE tp.name = tpe.patient)
    WHEN 'Insurance' THEN custom_provider
    ELSE NULL
    END customer,
    (SELECT price_list_rate FROM `tabItem Price` tip
    WHERE item_code = (SELECT value FROM tabSingles ts
    WHERE field = 'op_consulting_charge_item')
    AND price_list = (
      SELECT default_price_list 
      FROM `tabCustomer Group` tcg 
      WHERE name = (
        SELECT customer_group 
        FROM tabCustomer tc 
        WHERE tc.name = (
          SELECT tp.customer FROM tabPatient tp WHERE tp.name = tpe.patient)))
    AND valid_from <= CURDATE()
    AND (valid_upto >= CURDATE() OR valid_upto IS NULL)
    AND customer IS NULL) harga,
    (SELECT default_income_account FROM tabCompany WHERE name = tpe.company) acc,
    (SELECT default_receivable_account FROM tabCompany WHERE name = tpe.company) rec,
    (SELECT custom_cost_center FROM tabBranch WHERE name = tpe.custom_branch) cc,
    (SELECT value FROM tabSingles where field = 'stock_uom') uom
    FROM `tabPatient Encounter` tpe, `tabPatient Appointment` tpa
    WHERE tpe.appointment = '{exam_id}'
		AND tpa.name = '{exam_id}';
    """
  return frappe.db.sql(sql, as_dict = True)

@frappe.whitelist()
def get_invoice_item_from_mcu(exam_id):
  sql = f"""
    SELECT mcu title, patient, NULL practitioner, NULL custom_service_unit,
    CASE custom_type
    WHEN 'Personal' THEN (SELECT customer FROM tabPatient tp WHERE tp.name = tpe.patient)
    WHEN 'Bill to Company' THEN (SELECT custom_company FROM tabPatient tp WHERE tp.name = tpe.patient)
    WHEN 'Insurance' THEN custom_provider
    ELSE NULL
    END customer,
    (SELECT price_list_rate FROM `tabItem Price` tip
    WHERE item_code = tpe.mcu
    AND selling = 1
    AND valid_from <= CURDATE()
    AND (valid_upto >= CURDATE() OR valid_upto IS NULL)
    AND customer IS NULL) harga,
    (SELECT default_income_account FROM tabCompany WHERE name = tpe.company) acc,
    (SELECT default_receivable_account FROM tabCompany WHERE name = tpe.company) rec,
    (SELECT custom_cost_center FROM tabBranch WHERE name = tpe.custom_branch) cc,
    (SELECT value FROM tabSingles where field = 'stock_uom') uom,
		(SELECT item_name FROM tabItem ti WHERE ti.name = mcu) item_name
    FROM `tabPatient Appointment` tpe
    WHERE tpe.name = '{exam_id}';
    """
  return frappe.db.sql(sql, as_dict = True)

