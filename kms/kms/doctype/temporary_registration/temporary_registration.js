// Copyright (c) 2024, GIS and contributors
// For license information, please see license.txt

frappe.ui.form.on('Temporary Registration', {
  onload: function (frm) {
    frappe.breadcrumbs.add('Healthcare', 'Temporary Registration');
  },
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
					let d = new frappe.ui.Dialog({
						title: 'Select a Patient',
						fields:[
							{
								label: 'Patient',
								fieldname: 'patient',
								fieldtype: 'Link',
								options: 'Patient',
								reqd: 1
							},
							{
								label: 'Name',
								fieldname: 'name',
								fieldtype: 'Data',
								read_only: 1
							},
							{
								label: 'Date of Birth',
								fieldname: 'dob',
								fieldtype: 'Date',
								read_only: 1
							},
							{
								label: 'Gender',
								fieldname: 'gender',
								fieldtype: 'Data',
								read_only: 1
							},
							{
								label: 'ID',
								fieldname: 'id',
								fieldtype: 'Data',
								read_only: 1
							},
							{
								label: 'Company',
								fieldname: 'company',
								fieldtype: 'Data',
								read_only: 1
							},
						],
						primary_action_label: 'Pick',
						primary_action(values) {
							frm.set_value('patient', values.patient)
							d.hide();
							frm.refresh_field('patient');	
						}
					});
					d.fields_dict.patient.df.onchange = function() {
						const patient_id = d.get_value('patient');
						if(patient_id){
							frappe.db
							.get_value('Patient', patient_id, ['patient_name', 'sex', 'uid', 'dob', 'custom_company'])
							.then(r=>{
								if(r.message) {
									d.set_value('name', r.message.patient_name||'');
									d.set_value('gender', r.message.sex||'');
									d.set_value('id', r.message.uid||'');
									d.set_value('dob', r.message.dob||'');
									d.set_value('company', r.message.custom_company||'');
								}
							})
						}
					};
					d.show();
				},
				'Process'
			);
		} else {
			if (frm.doc.status === 'Draft') {
				frm.add_custom_button(
					'Create Appointment',
					() => {
						if (frm.doc.patient) {
							frappe.new_doc('Patient Appointment', {appointment_type: frm.doc.questionnaire_type === 'Outpatient' ? 'Dokter Consultation (GP)' : frm.doc.appointment_type},
								doc => {
									doc.custom_priority= frm.doc.questionnaire_type === 'MCU' ? '4. MCU' : '3. Outpatient'
									doc.appointment_for= frm.doc.questionnaire_type === 'MCU' ? 'MCU' : 'Department'
									doc.department= frm.doc.questionnaire_type === 'Doctor Consultation' ? 'General Practice' : ''
									doc.appointment_date= frm.doc.exam_date
									doc.custom_temporary_registration = frm.doc.name
									doc.patient= frm.doc.patient
								}
							)
						}
					},
					'Process'
				);
			}
		}
		if (frm.doc.status !== 'Cancelled' && frm.doc.status !== 'Transferred') {
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