// Copyright (c) 2024, GIS and contributors
// For license information, please see license.txt

frappe.ui.form.on('Temporary Registration', {
	setup: function(frm) {
		frm.disable_form();
	},
	refresh: function(frm) {
		if (!frm.doc.patient) {
			frm.add_custom_button(
				'Create Patient',
				() => {
					const name = split_full_name (frm.doc.patient_name);
					frappe.db
					.insert({
						doctype:'Patient',
						first_name: name.first_name,
						middle_name: name.middle_name,
						last_name: name.last_name,
						sex: frm.doc.gender,
						dob: frm.doc.date_of_birth,
						status: 'Active',
						uid: frm.doc.id_number,
						mobile: frm.doc.phone_number,
						customer_group: 'Individual',
						custom_company: frm.doc.company
					})
					.then(doc=> {
						frappe.db.set_value('Temporary Registration', frm.doc.name, 'patient', doc.name)
					})
				},
				'Process'
			);
			frm.add_custom_button(
				'Create from Existing Patient',
				() => {
				},
				'Process'
			);
		} else {
			if (frm.doc.status === 'Draft') {
				frm.add_custom_button(
					'Create Appointment',
					() => {
						if (frm.doc.patient) {
							frappe.new_doc('Patient Appointment', {appointment_type: frm.doc.questionnaire_type === 'Outpatient' ? 'Dokter Consultation (GP)' : frm.doc.questionnaire_type},
								doc => {
									//doc.custom_branch= 'Jakarta Main Clinic'
									doc.priority= frm.doc.questionnaire_type === 'MCU' ? '4. MCU' : '3. Outpatient'
									doc.appointment_for= frm.doc.questionnaire_type === 'MCU' ? 'MCU' : 'Department'
									doc.department= frm.doc.questionnaire_type === 'Outpatient' ? 'General Practice' : ''
									doc.appointment_date= frm.doc.exam_date
									//doc.cu= 'STD-001'
									doc.patient= frm.doc.patient
								}
							)
						}
					},
					'Process'
				);
			}
		}
		if (frm.doc.status !== 'Cancelled') {
			frm.add_custom_button(
				'Cancel',
				() => {
					frappe.db
					.set_value('Temporary Registration', frm.doc.name, 'status', 'Cancelled')
					.then(r=> {
						frappe.show_alert(`Temporary Registration ${frm.doc.name} is Cancelled.`);
						frm.refresh();
					})
				},
				'Process'
			);	
		}
	}
});
const split_full_name = (full_name) => {
	const nameParts = full_name.trim().split(' ');
	const [first_name, ...rest] = nameParts;
	const last_name = rest.pop() | '';
	const middle_name = rest.join(' ');
	return { first_name, middle_name, last_name };
}