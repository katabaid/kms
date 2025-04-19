import frappe

@frappe.whitelist()
def get_healthcare_services_to_invoice(patient, company):
	if frappe.db.exists("Patient", patient):
		patient = frappe.get_doc("Patient", patient)
		items_to_invoice = []
		if patient:
			validate_customer_created(patient)
		  # Customer validated, build a list of billable services
			items_to_invoice += get_appointments_to_invoice(patient, company)
			#items_to_invoice += get_encounters_to_invoice(patient, company)
			#items_to_invoice += get_lab_tests_to_invoice(patient, company)
			#items_to_invoice += get_clinical_procedures_to_invoice(patient, company)
			return items_to_invoice
	return None

def validate_customer_created(patient):
	if not frappe.db.get_value("Patient", patient.name, "customer"):
		msg = _("Please set a Customer linked to the Patient")
		msg += " <b><a href='/app/Form/Patient/{0}'>{0}</a></b>".format(patient.name)
		frappe.throw(msg, title=_("Customer Not Found"))

def get_appointments_to_invoice(patient, company):
	result = []
	result.append({
						"reference_type": "Patient Appointment",
						"reference_name": '01-20250319-0003',
						"service": 'STD-00047',
						"rate": 100,
						"income_account": '41200110 - Out Patient Income Others - KMS',
					})
	return result
def get_encounters_to_invoice(patient, company):
	if not isinstance(patient, str):
		patient = patient.name
	encounters_to_invoice = []
	encounters = frappe.get_list(
		"Patient Encounter",
		fields=["*"],
		filters={"patient": patient, "company": company, "invoiced": False, "docstatus": 1},
	)
	if encounters:
		for encounter in encounters:
			if not encounter.appointment:
				practitioner_charge = 0
				income_account = None
				service_item = None
				if encounter.practitioner:
					if encounter.inpatient_record and frappe.db.get_single_value(
						"Healthcare Settings", "do_not_bill_inpatient_encounters"
					):
						continue

					details = get_appointment_billing_item_and_rate(encounter)
					service_item = details.get("service_item")
					practitioner_charge = details.get("practitioner_charge")
					income_account = get_income_account(encounter.practitioner, encounter.company)

				encounters_to_invoice.append(
					{
						"reference_type": "Patient Encounter",
						"reference_name": encounter.name,
						"service": service_item,
						"rate": practitioner_charge,
						"income_account": income_account,
					}
				)

	return encounters_to_invoice

def get_lab_tests_to_invoice(patient, company):
	lab_tests_to_invoice = []
	lab_tests = frappe.get_list(
		"Lab Test",
		fields=["name", "template"],
		filters={"patient": patient.name, "company": company, "invoiced": False, "docstatus": 1},
	)
	for lab_test in lab_tests:
		item, is_billable = frappe.get_cached_value(
			"Lab Test Template", lab_test.template, ["item", "is_billable"]
		)
		if is_billable:
			lab_tests_to_invoice.append(
				{"reference_type": "Lab Test", "reference_name": lab_test.name, "service": item}
			)

	lab_prescriptions = frappe.db.sql(
		"""
			SELECT
				lp.name, lp.lab_test_code
			FROM
				`tabPatient Encounter` et, `tabLab Prescription` lp
			WHERE
				et.patient=%s
				and lp.parent=et.name
				and lp.lab_test_created=0
				and lp.invoiced=0
		""",
		(patient.name),
		as_dict=1,
	)

	for prescription in lab_prescriptions:
		item, is_billable = frappe.get_cached_value(
			"Lab Test Template", prescription.lab_test_code, ["item", "is_billable"]
		)
		if prescription.lab_test_code and is_billable:
			lab_tests_to_invoice.append(
				{"reference_type": "Lab Prescription", "reference_name": prescription.name, "service": item}
			)

	return lab_tests_to_invoice


def get_clinical_procedures_to_invoice(patient, company):
	clinical_procedures_to_invoice = []
	procedures = frappe.get_list(
		"Clinical Procedure",
		fields="*",
		filters={"patient": patient.name, "company": company, "invoiced": False},
	)
	for procedure in procedures:
		if not procedure.appointment:
			item, is_billable = frappe.get_cached_value(
				"Clinical Procedure Template", procedure.procedure_template, ["item", "is_billable"]
			)
			if procedure.procedure_template and is_billable:
				clinical_procedures_to_invoice.append(
					{"reference_type": "Clinical Procedure", "reference_name": procedure.name, "service": item}
				)

		# consumables
		if (
			procedure.invoice_separately_as_consumables
			and procedure.consume_stock
			and procedure.status == "Completed"
			and not procedure.consumption_invoiced
		):
			service_item = frappe.db.get_single_value(
				"Healthcare Settings", "clinical_procedure_consumable_item"
			)
			if not service_item:
				frappe.throw(
					_("Please configure Clinical Procedure Consumable Item in {0}").format(
						frappe.utils.get_link_to_form("Healthcare Settings", "Healthcare Settings")
					),
					title=_("Missing Configuration"),
				)

			clinical_procedures_to_invoice.append(
				{
					"reference_type": "Clinical Procedure",
					"reference_name": procedure.name,
					"service": service_item,
					"rate": procedure.consumable_total_amount,
					"description": procedure.consumption_details,
				}
			)

	procedure_prescriptions = frappe.db.sql(
		"""
			SELECT
				pp.name, pp.procedure
			FROM
				`tabPatient Encounter` et, `tabProcedure Prescription` pp
			WHERE
				et.patient=%s
				and pp.parent=et.name
				and pp.procedure_created=0
				and pp.invoiced=0
				and pp.appointment_booked=0
		""",
		(patient.name),
		as_dict=1,
	)

	for prescription in procedure_prescriptions:
		item, is_billable = frappe.get_cached_value(
			"Clinical Procedure Template", prescription.procedure, ["item", "is_billable"]
		)
		if is_billable:
			clinical_procedures_to_invoice.append(
				{
					"reference_type": "Procedure Prescription",
					"reference_name": prescription.name,
					"service": item,
				}
			)

	return clinical_procedures_to_invoice
