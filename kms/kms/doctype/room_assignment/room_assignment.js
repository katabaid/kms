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
			frm.set_df_property('section_break_jasf', 'hidden', 1);
		}
	},
	setup(frm) {
		const medical_department = frappe.defaults.get_user_default('medical_department');
		frm.set_query('healthcare_service_unit', () => {
			return { filters: 
				[
					['is_group', '=', 0], 
					['custom_department', '=', medical_department],
					['name', 'not in', get_already_assigned_rooms(frm)]
				] 
			};
		});
	},
	before_load(frm) {
		if (frm.is_new()) {
			frm.set_value('user', frappe.session.user);
		}
	},
	after_save(frm){
		window.location = '/app/healthcare';
	},
	mcu(frm) {
		frm.set_df_property('section_break_jasf', 'hidden', 0);
	},
	outpatient(frm) {
		if(frappe.user_roles.includes('HC Dokter Internal'))
			window.location = '/app/healthcare';
		else
			frm.set_df_property('section_break_jasf', 'hidden', 0);
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

function get_already_assigned_rooms(frm) {
	let rooms = [];
	if (!frm.doc.date) {
			frappe.msgprint(__('Please enter a date before selecting a room.'));
			return rooms;
	}
	
	frappe.call({
			method: 'kms.api.get_assigned_room',
			args: {
					date: frm.doc.date,
			},
			async: false, // Ensures this call finishes before returning
			callback: function(response) {
					if (response && response.message) {
							rooms = response.message;
					}
			}
	});
	return rooms;
}