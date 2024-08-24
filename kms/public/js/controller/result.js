function show_user_selection_dialog(frm) {
	$('.add-assignment-btn').remove();
	frm.add_custom_button('Assign Result', () => {
		frappe.call({
			method: 'kms.api.get_users_by_doctype',
			args: {
				doctype: frm.doc.doctype
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
					} else {
						frappe.show_alert({
							message: __('The document could not be correctly assigned'),
							indicator: 'orange',
						});
					}
				},
			});
			d.hide();
		},
	});
	d.show();
}

// Function to initialize the dialog in different doctypes
function assign_result_dialog_setup(frm) {
  show_user_selection_dialog(frm);
}

// Export the function for reuse in multiple doctypes
frappe.provide('kms');
kms.assign_result_dialog_setup = assign_result_dialog_setup;
