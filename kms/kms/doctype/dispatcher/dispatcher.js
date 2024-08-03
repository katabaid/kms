// Copyright (c) 2024, GIS and contributors
// For license information, please see license.txt

frappe.ui.form.on('Dispatcher', {
	refresh: function (frm) {
		frm.trigger('setup_custom_buttons');
		frm.trigger('hide_standard_child_tables_buttons');
		//frm.trigger('setup_child_table_custom_buttons');
		handleChildCustomButtons(frm);

		/* frm.fields_dict['assign_room_button'].df.hidden = true;
		frm.fields_dict['refuse_to_test_button'].df.hidden = true;
		frm.fields_dict['retest_button'].df.hidden = true;
		frm.fields_dict['remove_from_room_button'].df.hidden = true;
		frm.refresh_field('assign_room_button');
		frm.refresh_field('refuse_to_test_button');
		frm.refresh_field('retest_button');
		frm.refresh_field('remove_from_room_button');

		frm.fields_dict['assign_room_button'].input.onclick = function() {
			assign_room(frm);
		}
		frm.fields_dict['refuse_to_test_button'].input.onclick = function() {
			refuse_to_test(frm);
		}
		frm.fields_dict['retest_button'].input.onclick = function() {
			retest(frm);
		}
		frm.fields_dict['remove_from_room_button'].input.onclick = function() {
			remove_from_room(frm);
		}

		if(frm.doc.status === 'Waiting to Finish') {
			frm.add_custom_button(
				'Finish', 
				() => {
					frm.doc.status = 'Finished';
					frm.dirty();
					frm.save();
				}, 
				'Status')
		} */
	},

	setup_custom_buttons: function (frm) {
		handleCustomButtons(frm);
	},

	hide_standard_child_tables_buttons: function (frm) {
		handleHideChildButtons(frm, childTables);
	},

	setup_child_table_custom_buttons: function (frm) {
		handleChildCustomButtons(frm);
	},

	/* onload_post_render: function(frm) {
		frm.fields_dict['assignment_table'].grid.wrapper.on('change', 'input, select', function() {
			check_button_state(frm);
		});
		frm.fields_dict['assignment_table'].grid.wrapper.on('change', '.grid-row-check', function() {
			check_button_state(frm);
		});
		
		frm.fields_dict['assignment_table'].grid.wrapper.find('.grid-add-row').hide();
		frm.fields_dict['assignment_table'].grid.wrapper.find('.grid-remove-rows').hide();

		frm.fields_dict['assignment_table'].grid.wrapper.on('click', '.grid-row-check', function() {
			ensure_single_selection(frm);
		});
	}, */

	setup: function (frm) {
		frm.set_indicator_formatter('healthcare_service_unit', function (doc) {
			if (doc.status === 'Finished') return 'green';
			else if (doc.status === 'Refused') return 'red';
			else if (doc.status === 'Wait for Room Assignment') return 'cyan';
			else if (doc.status === 'Waiting to Enter the Room') return 'yellow';
			else if (doc.status === 'Ongoing Examination') return 'pink';
			else return 'orange';
		});
	},
});

const childTables = ['assignment_table', 'package'];
const childTableButton = 'assignment_table';

// triggers
const handleCustomButtons = (frm) => {
	if (frm.doc.status === 'Waiting to Finish') {
		frm.add_custom_button('Finish', () => {
			frm.doc.status = 'Finished';
			frm.dirty();
			frm.save();
		});
	}
};

const handleHideChildButtons = (frm, childTablesArray) => {
	childTablesArray.forEach((field) => {
		const grid = frm.fields_dict[field].grid;
		grid.wrapper.find('.grid-add-row').hide();
		grid.wrapper.find('.grid-remove-rows').hide();
	});
};

const handleChildCustomButtons = (frm) => {
	const grid = frm.fields_dict[childTableButton].grid;
	const buttons = [
		{ label: 'Assign', status: 'Waiting to Enter the Room', statuses: 'Wait for Room Assignment', class: 'btn-primary', prompt: false },
		{ label: 'Refuse', status: 'Refused', statuses: 'Wait for Room Assignment', class: 'btn-danger', prompt: false },
		{ label: 'Retest', status: 'Wait for Room Assignment', statuses: 'Refused,Finished,Rescheduled,Partial Finished', class: 'btn-warning', prompt: false },
		{ label: 'Remove from Room', status: 'Wait for Room Assignment', statuses: 'Waiting to Enter the Room', class: 'btn-warning', prompt: false },
	];

	// Remove existing custom buttons
	grid.wrapper.find('.grid-footer').find('.btn-custom').hide();

	// Add new custom buttons
	buttons.forEach((button) => {
		const customButton = grid.add_custom_button(
			__(button.label),
			function () {
				if (button.prompt) {
					frappe.prompt(
						{
							fieldname: 'reason',
							label: 'Reason',
							fieldtype: 'Small Text',
							reqd: 1,
						},
						(values) => {
							updateChildStatus(frm, grid, button, values.reason);
						},
						__('Provide a Reason'),
						__('Submit')
					);
				} else {
					updateChildStatus(frm, grid, button);
				}
			},
			'btn-custom'
		);
		customButton.addClass(`${button.class} btn-sm`).attr('data-statuses', button.statuses);
		customButton.hide();
	});
	setupRowSelector(grid);
};

// trigger methods
const updateChildStatus = (frm, grid, button, reason = null) => {
	const selectedRows = grid.get_selected();
	if (selectedRows.length === 1) {
		const child = locals[grid.doctype][selectedRows[0]];
		frappe.model.set_value(child.doctype, child.name, 'status', button.status);
		if (button.label === 'Assign') {
			console.log('before assign_to_room')
			assign_to_room(frm);
			console.log('after assign_to_room')
		} else if (button.label === 'Remove from Room') {
			
		}
		frm
			.save()
			.then(() => {
				showAlert(`Updated status to ${button.status} Successfully.`, button.status === 'Refused' ? 'red' : 'green');
				frm.refresh();
				if (reason) {
					addComment(frm, reason);
				}
			})
			.catch((err) => {
				frappe.msgprint(__('Error updating status: {0}', [err.message]));
			});
	}
};

const setupRowSelector = (grid) => {
	grid.row_selector = function (e) {
		if (e.target.classList.contains('grid-row-check')) {
			const $row = $(e.target).closest('.grid-row');
			const docname = $row.attr('data-name');

			if (this.selected_row && this.selected_row === docname) {
				$row.removeClass('grid-row-selected');
				$row.find('.grid-row-check').prop('checked', false);
				this.selected_row = null;
			} else {
				this.$rows.removeClass('grid-row-selected');
				this.$rows.find('.grid-row-check').prop('checked', false);
				$row.addClass('grid-row-selected');
				$row.find('.grid-row-check').prop('checked', true);
				this.selected_row = docname;
			}
			this.refresh_remove_rows_button();
			updateCustomButtonVisibility(grid);
		}
	};
	grid.wrapper.on('click', '.grid-row', function () {
		updateCustomButtonVisibility(grid);
	});
};

const updateCustomButtonVisibility = (grid) => {
	const selectedRows = grid.get_selected();
	const buttons = grid.wrapper.find('.grid-footer').find('.btn-custom');
	if (selectedRows && selectedRows.length === 1) {
		const child = locals[grid.doctype][selectedRows[0]];
		buttons.each((index, button) => {
			const $button = $(button);
			const buttonStatuses = $button.data('statuses');
			if (buttonStatuses) {
				const statuses = buttonStatuses.split(',');
				$button.toggle(statuses.includes(child.status));
			} else {
				$button.toggle(child.status === 'Started');
			}
		});
	} else {
		buttons.hide();
	}
}

function check_button_state(frm) {
	let show_assign_room_button = false;
	let show_refuse_to_test_button = false;
	let show_retest_button = false;
	let show_remove_from_room = false;
	let selected_rows = frm.fields_dict['assignment_table'].grid.get_selected_children();
	if (selected_rows.length > 0) {
		for (let row of selected_rows) {
			if (row.status === 'Wait for Room Assignment') {
				show_assign_room_button = true;
			} else {
				show_assign_room_button = false;
				break;
			}
		}
		for (let row of selected_rows) {
			if (row.status === 'Finished' || row.status === 'Refused') {
				show_retest_button = true;
			} else {
				show_retest_button = false;
				break;
			}
		}
		for (let row of selected_rows) {
			if (row.status === 'Waiting to Enter the Room') {
				show_remove_from_room = true;
			} else {
				show_remove_from_room = false;
				break;
			}
		}
		for (let row of selected_rows) {
			if (row.status != 'Refused' && row.status != 'Finished') {
				show_refuse_to_test_button = true;
			} else {
				show_refuse_to_test_button = false;
				break;
			}
		}
	}
	frm.fields_dict['assign_room_button'].df.hidden = !show_assign_room_button;
	frm.refresh_field('assign_room_button');
	frm.fields_dict['refuse_to_test_button'].df.hidden = !show_refuse_to_test_button;
	frm.refresh_field('refuse_to_test_button');
	frm.fields_dict['retest_button'].df.hidden = !show_retest_button;
	frm.refresh_field('retest_button');
	frm.fields_dict['remove_from_room_button'].df.hidden = !show_remove_from_room;
	frm.refresh_field('remove_from_room_button');
}

function assign_room(frm) {
	let selected_rows = frm.fields_dict['assignment_table'].grid.get_selected_children();
	if (selected_rows.length > 0 && selected_rows) {
		selected_rows.forEach((row) => {
			if (row.status === 'Wait for Room Assignment') {
				assign_to_room(frm, row.healthcare_service_unit);
			}
		});
	}
}

function refuse_to_test(frm) {
	let selected_rows = frm.fields_dict['assignment_table'].grid.get_selected_children();
	if (selected_rows.length > 0 && selected_rows) {
		selected_rows.forEach((row) => {
			frappe.model.set_value(row.doctype, row.name, 'status', 'Refused');
		});
		frm.save();
	}
}

function retest(frm) {
	let selected_rows = frm.fields_dict['assignment_table'].grid.get_selected_children();
	if (selected_rows.length > 0 && selected_rows) {
		selected_rows.forEach((row) => {
			frappe.model.set_value(row.doctype, row.name, 'status', 'Wait for Room Assignment');
		});
		frm.save();
	}
}

function remove_from_room(frm) {
	let selected_rows = frm.fields_dict['assignment_table'].grid.get_selected_children();
	if (selected_rows.length > 0 && selected_rows) {
		selected_rows.forEach((row) => {
			const reference_doctype = row.reference_doctype;
			const reference_doc = row.reference_doc;
			if (reference_doctype === 'Sample Collection') {
				frappe.call({
					method: 'kms.sample_collection.remove',
					args: {
						name: reference_doc,
						reason: 'Removed from Room',
					},
					callback: (r) => {
						if (r.message) {
							console.log(r.message);
							frm.reload_doc();
						}
					},
				});
			}
		});
	}
}

function assign_to_room(frm) {
	//define selected rooms to process
	let selected_rows = frm.fields_dict['assignment_table'].grid.get_selected();
	if (selected_rows.length > 0 && selected_rows) {
		const child = locals[frm.fields_dict['assignment_table'].grid.doctype][selected_rows];
		//for each room define what method to call
		frappe.db.get_value('Healthcare Service Unit', child.healthcare_service_unit, 'service_unit_type').then((hsu) => {
			frappe.db
			.get_value('Healthcare Service Unit Type', hsu.message.service_unit_type, 'custom_default_doctype')
			.then((dt) => {
				console.log(dt.message.custom_default_doctype);
				// Lab
				if (dt.message.custom_default_doctype == 'Sample Collection') {
					frappe.call({
						method: 'kms.api.create_sample_and_test',
						args: {
							disp: frm.doc.name,
							selected: child.healthcare_service_unit,
						},
						callback: function (r) {
							if (r.message) {
								frappe.model.set_value(child.doctype, child.name, 'status', 'Waiting to Enter the Room');
								frappe.model.set_value(child.doctype, child.name, 'reference_doctype', 'Sample Collection');
								frappe.model.set_value(child.doctype, child.name, 'reference_doc', r.message.sample);
								frm.save();
								frappe.show_alert({
									message: 'Room assigned successfully.',
									indicator: 'green',
								});
							}
						},
					});
				} else if (
					dt.message.custom_default_doctype == 'Doctor Examination' ||
					dt.message.custom_default_doctype == 'Nurse Examination' ||
					dt.message.custom_default_doctype == 'Radiology'
				) {
					console.log('before kms.healthcare.create_service')
					frappe.call({
						method: 'kms.healthcare.create_service',
						args: {
							target: dt.message.custom_default_doctype,
							source: frm.doc.doctype,
							name: frm.doc.name,
							room: child.healthcare_service_unit,
						},
						callback: function (r) {
							console.log('after kms.healthcare.create_service')
							console.log(r);
							if (r.message) {
								frappe.model.set_value(child.doctype, child.name, 'status', 'Waiting to Enter the Room');
								frappe.model.set_value(
									child.doctype,
									child.name,
									'reference_doctype',
									dt.message.custom_default_doctype
								);
								frappe.model.set_value(child.doctype, child.name, 'reference_doc', r.message.docname);
								frm.save();
								frappe.show_alert({
									message: 'Room assigned successfully.',
									indicator: 'green',
								});
							}
						},
					});
				} else {
					frappe.throw('Room type default DocType has not been configured. Please contact Administrator.');
				}
			});
		});
	}
}
function ensure_single_selection(frm) {
	let selected_row = null;
	frm.fields_dict['assignment_table'].grid.wrapper.find('.grid-row-check').each(function () {
		if ($(this).is(':checked')) {
			if (selected_row) {
				$(this).prop('checked', false);
			} else {
				selected_row = $(this);
			}
		}
	});
}

function addComment(frm, reason) {
	frappe.call({
		method: 'frappe.client.insert',
		args: {
			doc: {
				doctype: 'Comment',
				comment_type: 'Comment',
				reference_doctype: frm.doc.doctype,
				reference_name: frm.doc.name,
				content: `<div class="ql-editor read-mode"><p>${reason}</p></div>`,
				comment_by: frappe.session.user_fullname
			}
		},
		callback: function (response) {
			if (!response.exc) {
				showAlert('Comment added successfully.', 'green');
			}
		}
	});
}

function showAlert(message, indicator) {
	frappe.show_alert({
		message: message,
		indicator: indicator
	}, 5);
}
