// Copyright (c) 2024, GIS and contributors
// For license information, please see license.txt

frappe.ui.form.on('Room Assignment', {
  onload: function (frm) {
    frappe.breadcrumbs.add('Healthcare', 'Room Assignment');
  },
	refresh(frm) {
		if (!frm.is_new() && frm.doc.user === frappe.session.user && frm.doc.assigned) {
			add_change_room_button (frm);
		}
		if (frm.is_new()) {
			add_cancel_button(frm);
		}
	},
	setup(frm) {
		const medical_department = frappe.defaults.get_user_default('medical_department');
		frm.set_query('healthcare_service_unit', () => {
			return { filters: 
				[[ 'is_group', '=', 0 ], ['custom_department', '=', medical_department]] };
		});
	},
	before_load(frm) {
		if (frm.is_new()) {
			frm.set_value('user', frappe.session.user);
		}
	},
	after_save(frm){
		if (frm.is_new()) {
			frappe.set_route('/app/healthcare');
		}
	}
});

function add_change_room_button(frm) {
	frm.add_custom_button("Change Room", () => {
		const medical_department =
			frappe.defaults.get_user_default("medical_department");

		frappe.call({
			method: "kms.kms.doctype.room_assignment.room_assignment.get_room_list",
			args: {
				dept: medical_department,
				room: frm.doc.healthcare_service_unit,
			},
			callback: (r) => {
				if (r.message) {
					const room_list = r.message;

					frappe.prompt(
						{
							label: "Healthcare Service Unit",
							fieldname: "healthcare_service_unit",
							fieldtype: "Select", // Use Select to avoid Link's built-in permissions
							options: room_list.join("\n"), // Populate options dynamically
						},
						(values) => {
							frappe.call({
								method:
									"kms.kms.doctype.room_assignment.room_assignment.change_room",
								args: {
									name: frm.doc.name,
									room: values.healthcare_service_unit,
								},
								callback: function (response) {
									if (response.message) {
										frappe.set_route(
											"Form",
											"Room Assignment",
											response.message,
										);
									}
								},
							});
						},
						"Select Healthcare Service Unit",
					);
				}
			},
		});
	});
}

function add_cancel_button(frm) {
	frm.add_custom_button('Cancel', () => {
		frappe.set_route('/app/healthcare');
	})
}