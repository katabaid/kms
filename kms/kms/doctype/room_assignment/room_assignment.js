// Copyright (c) 2024, GIS and contributors
// For license information, please see license.txt

frappe.ui.form.on('Room Assignment', {
	refresh(frm) {
		if (!frm.is_new() && frm.doc.user === frappe.session.user) {
			add_change_room_button (frm);
		}
		show_user_selection_dialog(frm);
	},
	setup(frm) {
		frm.set_query('healthcare_service_unit', () => {
			return { filters: { is_group: 0 } };
		});
	},
	before_load(frm) {
		if (frm.is_new()) {
			frm.set_value('user', frappe.session.user);
		}
	},
});

function show_user_selection_dialog(frm) {
	frm.add_custom_button('Assign Result', () =>{
		frappe.call({
			method: 'kms.api.get_users_by_role',
			args: {
				role: 'Academics User', // Replace 'Manager' with your desired role
			},
			callback: function (r) {
				if (r.message && r.message.length) {
					show_dialog(frm, r.message);
				} else {
					frappe.msgprint(__('No users found with the specified role.'));
				}
			},
		});
	});
	frm.change_custom_button_type('Assign Result', null, 'info');
}

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

function show_dialog(frm, users) {
	let d = new frappe.ui.Dialog({
		title: 'Select Users',
		fields: [
			{
				label: 'Users',
				fieldname: 'users',
				fieldtype: 'Table',
				cannot_add_rows: true,
				cannot_delete_rows: true,
				in_place_edit: false,
				data: users.map((user) => ({
					user: user.name,
					full_name: user.full_name,
				})),
				fields: [
					{
						fieldtype: 'Data',
						fieldname: 'user',
						label: 'User',
						in_list_view: 1,
						columns: 2,
					},
					{
						fieldtype: 'Data',
						fieldname: 'full_name',
						label: 'Full Name',
						in_list_view: 1,
						columns: 3,
					},
				],
			},
		],
		primary_action_label: 'Select',
		primary_action(values) {
			let selected_users = values.users.filter((user) => user.__checked).map((user) => user.user);
			// Do something with the selected users
			console.log('Selected users:', selected_users);
			frappe.call({
				method: 'frappe.desk.form.assign_to.add',
				args: {
					doctype: frm.doc.doctype,
					name: frm.doc.name,
					assign_to: selected_users,
					notify: true,
					re_assign: true,
				},
				callback: function (r) {
					if (!r.exc) {
						frappe.show_alert({
							message: __('The document has been assigned to {0}', [selected_users]),
							indicator: 'green',
						});
						return;
					} else {
						frappe.show_alert({
							message: __('The document could not be correctly assigned'),
							indicator: 'orange',
						});
						return;
					}
				},
			});
			d.hide();
		},
	});
	d.show();
}
