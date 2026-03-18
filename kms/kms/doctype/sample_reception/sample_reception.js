// Copyright (c) 2024, GIS and contributors
// For license information, please see license.txt

frappe.ui.form.on('Sample Reception', {
	refresh(frm) {
		// Call the MCU Appointment utility if the HTML field exists
		if (frm.fields_dict.custom_mcu_items_html && kms.utils && kms.utils.fetch_mcu_appointment_for_doctype) {
			kms.utils.fetch_mcu_appointment_for_doctype(
				frm, 
				"name", 
				"custom_mcu_items_html"
			);
		} else {
			if (!frm.fields_dict.custom_mcu_items_html) {
				console.warn("Sample Reception form is missing 'custom_mcu_items_html'. MCU Items cannot be displayed.");
			}
			if (!kms.utils || !kms.utils.fetch_mcu_appointment_for_doctype) {
				console.warn("kms.utils.fetch_mcu_appointment_for_doctype is not available. Ensure mcu_appointment_helper.js is loaded.");
			}
		}
	}
});
