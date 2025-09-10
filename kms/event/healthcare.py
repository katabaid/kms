import frappe
from kms.utils import calculate_patient_age
from frappe.utils import getdate, today, nowdate, nowtime, now

def patient_appointment_after_insert(doc, method=None):
	################Doctype: Patient Appointment################
	if doc.custom_temporary_registration:
		frappe.db.set_value(
			'Temporary Registration', 
			doc.custom_temporary_registration, 
			{'patient_appointment': doc.name, 'status': 'Transferred'})
	_set_completed_questionnaire_status(doc.name)
	if doc.custom_temporary_registration:
		_set_questionnaire_key(doc.name, doc.custom_temporary_registration)
	frappe.db.set_value('Patient Appointment', doc.name, 'patient_age', 
		calculate_patient_age(
			getdate(doc.custom_patient_date_of_birth), getdate(doc.appointment_date)))
	frappe.db.set_value('Patient Appointment', doc.name, 'notes', frappe.db.get_value(
		'Patient', doc.patient, 'patient_details'))
	doc.reload()

def patient_appointment_on_update(doc, method=None):
	################Doctype: Patient Appointment################
	doc.status = doc.status or 'Open'
	previous_doc = doc.get_doc_before_save()
	date = doc.custom_rescheduled_date if doc.custom_rescheduled_date else doc.appointment_date
	dispatcher_user = frappe.db.get_value("Dispatcher Settings", 
		{"branch": doc.custom_branch, 'enable_date': date}, ['dispatcher'])
	if not previous_doc and doc.status == 'Checked In':
		if dispatcher_user:
			_create_dispatcher(doc.name, doc.custom_branch)
		else:
			_create_mcu_queue_pooling(doc.name, doc.custom_branch)
		_set_mcu_queue_no(doc.name)
		return
	if previous_doc and previous_doc.status in ['Open','Rescheduled'] and doc.status == 'Checked In':
		if doc.appointment_type == 'MCU':
			_validate_mcu_templates(doc)
			if dispatcher_user:
				_create_dispatcher(doc.name, doc.custom_branch)
			else:
				_create_mcu_queue_pooling(doc.name, doc.custom_branch)
			_set_mcu_queue_no(doc.name)
		else:
			_create_vital_signs(doc)
	elif doc.status in ['Checked In', 'Ready to Check Out']:
		_validate_with_today_date(doc.appointment_date)
		if str(doc.appointment_date) == nowdate():
			if doc.has_value_changed('patient_age'):
				return
			if doc.appointment_type == 'MCU':
				if not doc.custom_queue_no:
					_set_mcu_queue_no(doc.name)
				if len(doc.custom_additional_mcu_items) > len(previous_doc.custom_additional_mcu_items):
					_set_completed_questionnaire_status(doc.name)
				additional = [row for row in doc.custom_additional_mcu_items if row.status == 'To be Added']
				if additional:
					exist_docname = frappe.db.get_value(
						'Dispatcher', {'patient_appointment': doc.name}, ['name'])
					if exist_docname:
						_add_dispatcher_additional_mcu_item(
							exist_docname, additional, dispatcher_user)
					else:
						_add_queue_pooling_additional_mcu_item(doc.name, doc.custom_branch, additional)

def _create_vital_signs(doc):
	vs_doc = frappe.get_doc(dict(
		doctype = 'Vital Signs',
		patient = doc.patient,
		signs_date = nowdate(),
		signs_time = nowtime(),
		appointment = doc.name,
		custom_branch = doc.custom_branch,
		custom_patient_sex = doc.patient_sex,
		custom_patient_age = doc.patient_age,
		custom_patient_company = doc.custom_patient_company,
		custom_date_of_birth = doc.custom_patient_date_of_birth,
		vital_signs_note = doc.notes))
	vs_doc.insert(ignore_permissions=True)

def _add_dispatcher_additional_mcu_item(dispatcher, additional_table, dispatcher_user):
	doc = frappe.get_doc('Dispatcher', dispatcher)
	if doc.status == 'Finished':
		doc.status = 'In Queue'
	for entry in additional_table:
		# add new line to package
		new_entry = entry.as_dict()
		new_entry.name = None
		new_entry.parentfield = 'package'
		new_entry.parenttype = 'Dispatcher'
		new_entry.parent = doc.name
		doc.append('package', new_entry)
		# find related room to added item
		rooms = frappe.get_all(
			'Item Group Service Unit', 
			filters={'parent': entry.examination_item, 'branch': doc.branch}, 
			pluck='service_unit'
		)
		found = False
		row_counter = row_founder = 0
		for hsu in doc.assignment_table:
			row_counter += 1
		# update if there are already room 
			if hsu.healthcare_service_unit in rooms:
				hsu.status = 'Additional or Retest Request'
				found = True
			else:
				row_founder += 1
		# add if room previously not there
		if not found and row_founder == row_counter:
			for room in rooms:
				reference_doctype = frappe.db.get_value(
					'Healthcare Service Unit', room, 'custom_default_doctype')
				new_entry = dict()
				new_entry['name'] = None
				new_entry['healthcare_service_unit'] = room
				new_entry['status'] = 'Wait for Room Assignment'
				new_entry['reference_doctype'] = reference_doctype if reference_doctype else None
				doc.append('assignment_table', new_entry)
		# create notification for dispatcher user
		notification_doc = frappe.new_doc('Notification Log')
		notification_doc.for_user = dispatcher_user
		notification_doc.from_user = frappe.session.user
		notification_doc.document_type = 'Dispatcher'
		notification_doc.document_name = doc.name
		notification_doc.subject = f"""Patient <strong>{doc.patient_name}</strong> has """\
			f"""added additional MCU examination item: {entry.item_name}."""
		notification_doc.insert(ignore_permissions=True)
	doc.save(ignore_permissions=True)

def _create_dispatcher(exam_id, branch):
	doc = frappe.get_doc({
		'doctype': 'Dispatcher',
		'patient_appointment': exam_id,
		'date': today(),
		'status': 'In Queue'
	})
	rooms = __get_mcu_rooms(branch, exam_id)
	reception_room = __get_reception_room(branch)[0]
	for room in rooms:
		new_entry = dict()
		new_entry['name'] = None
		new_entry['healthcare_service_unit'] = room.service_unit
		new_entry['status'] = 'Wait for Room Assignment'
		new_entry['reference_doctype'] = room.custom_default_doctype
		doc.append('assignment_table', new_entry)
		if room.custom_default_doctype == 'Sample Collection':
			if not any(row.get('healthcare_service_unit') == reception_room
				for row in doc.assignment_table):
				new_entry = dict()
				new_entry['name'] = None
				new_entry['healthcare_service_unit'] = reception_room
				new_entry['status'] = 'Wait for Sample'
				doc.append('assignment_table', new_entry)
	items = frappe.db.sql("""SELECT * FROM `tabMCU Appointment` tma
		WHERE tma.parenttype = 'Patient Appointment'
		AND tma.parent = %s AND tma.status = 'Started' ORDER BY idx""", (exam_id), as_dict=True)
	for item in items:
		new_entry = dict()
		new_entry['examination_item'] = item['examination_item']
		new_entry['item_name'] = item['item_name']
		new_entry['item_group'] = item['item_group']
		new_entry['healthcare_service_unit'] = item['healthcare_service_unit']
		new_entry['status'] = item['status']
		doc.append('package', new_entry)
	doc.save(ignore_permissions=True)

def _create_queue_pooling_record(exam_id, service_unit, status, reference_doctype=None):
	doc_data = {
		'doctype': 'MCU Queue Pooling',
		'patient_appointment': exam_id,
		'date': today(),
		'arrival_time': nowtime(),
		'service_unit': service_unit,
		'status': status
	}
	if reference_doctype:
		doc_data['reference_doctype'] = reference_doctype
	doc = frappe.get_doc(doc_data)
	doc.save(ignore_permissions=True)

def _create_mcu_queue_pooling(exam_id, branch):
	rooms = __get_mcu_rooms(branch, exam_id)
	reception_room = __get_reception_room(branch)[0]
	for room in rooms:
		_create_queue_pooling_record(
			exam_id, room.service_unit, 'Wait for Room Assignment', room.custom_default_doctype)
		if room.custom_default_doctype == 'Sample Collection':
			if not frappe.db.exists('MCU Queue Pooling', f'{exam_id}-{today()}-{reception_room}'):
				_create_queue_pooling_record(exam_id, reception_room, 'Wait for Sample')
			
def __get_mcu_rooms(branch, exam_id):
	return frappe.db.sql("""SELECT distinct tigsu.service_unit, thsu.custom_default_doctype
		FROM `tabItem Group Service Unit` tigsu, `tabHealthcare Service Unit` thsu 
		WHERE tigsu.branch = %s
		AND tigsu.parenttype = 'Item'
		AND tigsu.service_unit = thsu.name 
		AND EXISTS (
			SELECT 1 FROM `tabMCU Appointment` tma
			WHERE tma.parenttype = 'Patient Appointment'
			AND tma.parent = %s AND tma.status = 'Started'
			AND tma.examination_item = tigsu.parent)
		ORDER BY thsu.custom_room, thsu.custom_default_doctype""", (branch, exam_id), as_dict=1)

def __get_reception_room(branch):
	return frappe.db.get_all('Healthcare Service Unit', 
		{'custom_branch': branch, 'service_unit_type': 'Sample Reception'}, pluck='name')

def _add_queue_pooling_additional_mcu_item(exam_id, branch, additional):
	items = list(set(item.get('examination_item') for item in additional))
	rooms = frappe.db.get_all(
		'Item Group Service Unit',
		filters={'parent': ['in', items], 'branch': branch},
		pluck='service_unit'
	)
	for room in rooms:
		qp = frappe.db.get_value(
			'MCU Queue Pooling', {'appointment': exam_id, 'service_unit': room}, 'name')
		if qp:
			frappe.db.set_value('MCU Queue Pooling', qp, 'status', 'Additional or Retest Request')
		else:
			doctype = frappe.db.get_value('Healthcare Service Unit', room, 'custom_default_doctype')
			pa = frappe.get_doc('Patient Appointment', exam_id)
			_create_queue_pooling_record(pa, room, 'Additional or Retest Request', doctype)

def patient_encounter_on_trash(doc, method=None):
	################Doctype: Patient Encounter################
	if doc.custom_queue_pooling:
		qp = frappe.get_doc("Queue Pooling", doc.custom_queue_pooling)
		qp.status = "Queued"
		qp.dequeue_time = None
		qp.encounter = None
		qp.healthcare_practitioner = None
		qp.save(ignore_permissions=True)

def patient_encounter_after_insert(doc, method=None):
	################Doctype: Patient Encounter################
	if doc.custom_queue_pooling:
		qp = frappe.get_doc("Queue Pooling", doc.custom_queue_pooling)
		qp.status = "Ongoing"
		qp.dequeue_time = nowtime()
		qp.encounter = doc.name
		qp.healthcare_practitioner = doc.practitioner
		qp.save(ignore_permissions=True)
		vs = doc.custom_vital_signs
		frappe.db.set_value('Vital Signs', vs, 'encounter', doc.name)

def patient_encounter_on_submit(doc, method=None):
	################Doctype: Patient Encounter################
	if doc.custom_queue_pooling:
		qp = frappe.get_doc("Queue Pooling", doc.custom_queue_pooling)
		qp.status = "Closed"
		qp.save(ignore_permissions=True)

def patient_encounter_validate(doc, method=None):
	################Doctype: Patient Encounter################
	if doc.custom_radiology:
		for radiology in doc.custom_radiology:
			if not radiology.status_time:
				radiology.status_time = now()

def patient_encounter_on_update(doc, method=None):
	################Doctype: Patient Encounter################
	if doc.docstatus == 1:
		frappe.db.set_value("Patient Appointment", doc.appointment, "status", "Ready to Check Out")
	else:
		frappe.db.set_value("Patient Appointment", doc.appointment, "status", doc._appointment_status)

def patient_encounter_before_safe(doc, method=None):
	################Doctype: Patient Encounter################
	doc._appointment_status = frappe.db.get_value('Patient Appointment', doc.appointment, 'status')

def prescription_duration_autoname(doc, method=None):
	################Doctype: Prescription Duration################
	doc.name = 'Mix ' + doc.custom_uom + ' ' + str(doc.number)

def vital_signs_before_submit(doc, method=None):
	################Doctype: Vital Signs################
	_validate_with_today_date(doc.signs_date)
	_validate_vs_mandatory_fields(doc, ['temperature', 'pulse', 'bp_systolic', 'bp_diastolic'])
	appt = frappe.get_doc('Patient Appointment', doc.appointment)
	_create_queue_pooling(doc, appt)

def patient_before_save(doc, method=None):
	################Doctype: Patient################
	doc.custom_age = calculate_patient_age(getdate(doc.dob), getdate(today()))

def _validate_with_today_date(validate_date):
	if str(validate_date) != today():
		frappe.throw(
			title = 'Error', 
			msg=f"Date {validate_date} must be the same as today's date {today()}.", 
			exc='ValidationError')
	
def _validate_vs_mandatory_fields(doc, fields):
	for field in fields:
		label = doc.meta.get_field(field).label
		if not doc.get(field):
			frappe.throw(title=f"{label} is Missing", msg=f"{label} is mandatory.")

def _create_queue_pooling(doc, appt):
	frappe.get_doc(dict(
		doctype = 'Queue Pooling',
		appointment = doc.appointment,
		appointment_type = appt.appointment_type,
		patient = doc.patient,
		date = nowdate(),
		arrival_time = nowtime(),
		status = 'Queued',
		priority = appt.custom_priority,
		vital_sign = doc.name,
		company = doc.company,
		department = appt.department if appt.appointment_for == 'Department' else None,
		service_unit = appt.service_unit if appt.appointment_for == 'Service Unit' else None,
		branch = doc.custom_branch,
		note = doc.vital_signs_note)).insert(ignore_permissions=True)

def _set_completed_questionnaire_status(name):
	sql = """SELECT name, (SELECT IF(count(*)>0,1,0) FROM `tabQuestionnaire Detail` tqd 
		WHERE tqd.parent = %(name)s AND tqd.template = tqt.name) completed
		FROM `tabQuestionnaire Template` tqt
		WHERE (EXISTS (SELECT 1 FROM `tabPatient Appointment` tpa WHERE tpa.name = %(name)s 
			AND tpa.appointment_type = tqt.appointment_type)
		OR EXISTS (SELECT 1 FROM `tabMCU Appointment` tma WHERE tma.parent = %(name)s 
			AND tma.examination_item = tqt.item_code))
		AND active = 1 AND (internal_questionnaire = 0 OR internal_questionnaire IS NULL)"""
	templates = frappe.db.sql(sql, {'name': name}, as_dict=True)
	if templates:
		frappe.db.delete('Questionnaire Completed', {'parent': name})
		for template in templates:
			doc_qc = frappe.get_doc({
				'doctype': 'Questionnaire Completed',
				'parent': name,
				'parentfield': 'custom_completed_questionnaire',
				'parenttype': 'Patient Appointment',
				'template': template.name,
				'is_completed': template.completed,
				'status': 'Completed' if template.completed else 'Started'
			})
			doc_qc.db_insert()

def _set_mcu_queue_no(name):
	custom_queue_no = frappe.db.get_all(
		'Patient Appointment', 
		filters={
			'company': 'Kyoai Medical Services',
			'custom_branch': 'Jakarta Main Clinic', 
			'appointment_type': 'MCU'
		},
		or_filters={
			'appointment_date': today(),
			'custom_rescheduled_date': today(),
		},
		fields=['max(custom_queue_no)+1 as maks'],
		pluck='maks'
	)[0]
	if not custom_queue_no:
		custom_queue_no = 1
	frappe.db.set_value(
		'Patient Appointment', name, 'custom_queue_no', custom_queue_no, update_modified=False)

def _set_questionnaire_key(name, temp_reg):
	q_list = frappe.db.get_all(
		'Questionnaire', filters={'temporary_registration': temp_reg}, pluck='name')
	for q in q_list:
		frappe.db.set_value('Questionnaire', q, 'patient_appointment', name)

def _validate_mcu_templates(doc):
	mcu_items = doc.get('custom_mcu_exam_items', []) + doc.get('custom_additional_mcu_items', [])
	if not mcu_items:
		return
	missing_templates = []
	template_doctypes = [
		'Lab Test Template',
		'Nurse Examination Template',
		'Doctor Examination Template',
		'Radiology Result Template'
	]
	for item in mcu_items:
		item_code = item.get('examination_item')
		if not item_code:
			continue
		found = False
		for doctype in template_doctypes:
			if frappe.db.exists(doctype, item_code):
				found = True
				break
		if not found:
			missing_templates.append(item.get('item_name') or item_code)
	if missing_templates:
		err_str = ', '.join(missing_templates)
		frappe.throw(title='Missing Templates',
			msg=f"The following MCU examination items do not have a corresponding template: {err_str}"
		)
