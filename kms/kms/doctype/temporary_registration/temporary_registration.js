// Copyright (c) 2024, GIS and contributors
// For license information, please see license.txt

frappe.ui.form.on('Temporary Registration', {
  onload: function (frm) {
    frappe.breadcrumbs.add('Healthcare', 'Temporary Registration');
  },
	/* setup: function(frm) {
		frm.disable_form();
	}, */
	refresh: function(frm) {
		if (!frm.doc.patient) {
			add_questionnaire_dialog_button(frm);
		} else {
			if (frm.doc.status === 'Draft') {
				add_create_appointment_button(frm);
			}
		}
		if (frm.doc.status !== 'Cancelled' && frm.doc.status !== 'Transferred') {
			add_cancel_button(frm);
		}
		if (frm.fields_dict.questionnaire) {
			kms.utils.fetch_questionnaire_for_doctype(
				frm, "name", null, "questionnaire"
			);
		}
	},
});


const add_create_appointment_button = (frm) => {
	frm.add_custom_button(
		'Create Appointment',
		() => {
			if (frm.doc.patient) {
				frappe.new_doc('Patient Appointment', 
					{appointment_type: 
						frm.doc.questionnaire_type === 
						'Outpatient' ? 'Dokter Consultation (GP)' : frm.doc.appointment_type},
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

const add_cancel_button = (frm) => {
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

const add_create_patient_button = (frm) => {
	frm.add_custom_button(
		'Create Patient',
		() => {
			frappe.confirm(
				__('Are you sure you want to create a new patient with this data?'),
				() => {
					frappe.db.insert({
						doctype:'Patient',
						first_name: frm.doc.first_name,
						middle_name: frm.doc.middle_name,
						last_name: frm.doc.last_name,
						sex: frm.doc.gender,
						dob: frm.doc.date_of_birth,
						status: 'Active',
						uid: frm.doc.id_number,
						mobile: frm.doc.phone_number,
						customer_group: 'Individual',
						custom_company: frm.doc.company
					}).then(doc=> {
						frappe.db.set_value('Temporary Registration', frm.doc.name, 'patient', doc.name);
						frm.refresh_field('patient');
						frappe.db.insert({
							doctype: 'Address',
							address_title: doc.patient_name,
							address_type: 'Billing',
							address_line1: frm.doc.address_line_1,
							address_line2: frm.doc.address_line_2,
							city: frm.doc.city,
							state: frm.doc.province,
							pincode: frm.doc.postal_code,
							links: [{
								link_doctype: 'Patient',
								link_name: doc.name,
							}]
						}).then(addr=>{
							frappe.msgprint(`Patient ${doc.patient_name} successfully created.`)
						})
					})
				},
				() => {
					frappe.show_alert(__('Patient creation cancelled.'));
				}
			);
		},
		'Process'
	);
}

const add_existing_patient_button = (frm) => {
	frm.add_custom_button(
		'Create from Existing Patient',
		() => {
			const dialog = new frappe.ui.form.MultiSelectDialog({
				doctype: 'Patient',
				target: frm,
				date_field: 'dob',
				setters: {
					patient_name:  null,
					custom_id_type: null,
					uid: null,
					dob: null,
					custom_company: null
				},
				get_query: function() {
					return {
						filters: {status: 'Active'}
					}
				},
				action: function(selections){
					if(selections){
						const full_name = [frm.doc.first_name, frm.doc.middle_name, frm.doc.last_name]
						.filter(Boolean).join(' ');
						frappe.warn('Setting portal data to use existing patient',
							`Are you sure want to change ${full_name} in to ${selections[0]}?`,
							() => {
								//frappe.get_doc('Patient', selections[0]).then(doc=>{
									frm.set_df_property('patient_section', 'hidden', 1);
									frm.set_df_property('company_section', 'hidden', 1);
									frm.set_df_property('address_section', 'hidden', 1);
									/* frm.toggle_display(
										['patient_section', 'company_section','address_section'], frm.doc.patient!='') */
									frm.set_value('patient', selections[0]);
									frm.refresh_field('patient');
									/* frm.refresh_field('patient_section');
									frm.refresh_field('company_section');
									frm.refresh_field('address_section'); */
								//})
							},
							'Continue',
						)
					}
					dialog.dialog.hide();
				}
			})
			const bindCheckboxWatcher = setInterval(() => {
				const $checkboxes = dialog.$wrapper.find('input[type="checkbox"]');
				if ($checkboxes.length > 0) {
					clearInterval(bindCheckboxWatcher);
					dialog.$wrapper.on('change', 'input[type="checkbox"]', function () {
						if (this.checked) {
							dialog.$wrapper
								.find('input[type="checkbox"]')
								.not(this)
								.prop('checked', false);
						}
					});
				}
			}, 100);
		},
		'Process'
	);
}

const questionnaire_questions = [
	{ id: 'q1', label: 'Do you have any known allergies?' },
	{ id: 'q2', label: 'Are you currently taking any medications?' },
	{ id: 'q3', label: 'Do you have any chronic medical conditions?' },
	{ id: 'q4', label: 'Have you had any surgeries in the past?' },
	{ id: 'q5', label: 'Do you have a family history of hereditary diseases?' }
];

const add_questionnaire_dialog_button = (frm) => {
	frm.add_custom_button(
		'Create Patient',
		() => show_questionnaire_dialog(frm),
		'Process'
	);
};

const show_questionnaire_dialog = (frm) => {
	const fields = questionnaire_questions.map(q => ({
		fieldtype: 'Check',
		fieldname: q.id,
		label: q.label
	}));

	const dialog = new frappe.ui.Dialog({
		title: 'Patient Verification Questions',
		fields: fields,
		primary_action_label: 'Continue',
		primary_action: () => {
			const values = dialog.get_values();
			const checked_count = Object.values(values).filter(v => v).length;

			dialog.hide();

			frm.remove_custom_button('Create Patient', 'Process');

			if (checked_count === 0) {
				add_existing_patient_button(frm);
			} else {
				add_create_patient_button(frm);
			}
		}
	});

	dialog.show();
};