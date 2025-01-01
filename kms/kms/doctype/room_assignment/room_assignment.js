// Copyright (c) 2024, GIS and contributors
// For license information, please see license.txt

frappe.ui.form.on('Room Assignment', {
  onload: function (frm) {
    frappe.breadcrumbs.add('Healthcare', 'Room Assignment');
  },
	refresh(frm) {
		if (!frm.is_new() && frm.doc.user === frappe.session.user) {
			add_change_room_button (frm);
		}
	},
	setup(frm) {
		const medical_department = frappe.defaults.get_user_default('medical_department');
		frm.set_query('healthcare_service_unit', () => {
			return { filters: [[ 'is_group', '=', 0 ], ['custom_department', '=', medical_department]] };
		});
	},
	before_load(frm) {
		if (frm.is_new()) {
			frm.set_value('user', frappe.session.user);
		}
	},
});

function add_change_room_button (frm) {
	frm.add_custom_button('Change Room', () => {
		frappe.prompt(
			{
				label: 'Healthcare Service Unit',
				fieldname: 'healthcare_service_unit',
				fieldtype: 'Link',
				options: 'Healthcare Service Unit',
				get_query: () => {
					return { filters: { is_group: 0 } };
				},
			},
			(values) => {
				frappe.call({
					method: 'kms.kms.doctype.room_assignment.room_assignment.change_room',
					args: {
						name: frm.doc.name,
						room: values.healthcare_service_unit,
					},
					callback: function (r) {
						if (r.message) {
							frappe.set_route('Form', 'Room Assignment', r.message);
						}
					},
				});
			}
		);
	});
}
