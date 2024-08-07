// Copyright (c) 2024, GIS and contributors
// For license information, please see license.txt

frappe.ui.form.on('Dispatcher', {
	refresh: function (frm) {
		handleCustomButtons(frm);
		handleHideChildButtons(frm, childTables);
		handleChildCustomButtons(frm);
	},

	setup: function (frm) {
		frm.set_indicator_formatter('healthcare_service_unit', (doc) => {
			const statusColors = {
				'Finished': 'green',
				'Refused': 'red',
				'Wait for Room Assignment': 'cyan',
				'Waiting to Enter the Room': 'yellow',
				'Ongoing Examination': 'pink',
			};
			return statusColors[doc.status] || 'orange';
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
		grid.wrapper.find('.grid-add-row, .grid-remove-rows').hide();
	});
};

const handleChildCustomButtons = (frm) => {
	const grid = frm.fields_dict[childTableButton].grid;
	const buttons = [
		{ label: 'Assign', status: 'Waiting to Enter the Room', statuses: 'Wait for Room Assignment', class: 'btn-primary', prompt: false },
		{ label: 'Refuse', status: 'Refused', statuses: 'Wait for Room Assignment', class: 'btn-danger', prompt: true },
		{ label: 'Retest', status: 'Wait for Room Assignment', statuses: 'Refused,Finished,Rescheduled,Partial Finished', class: 'btn-warning', prompt: true },
		{ label: 'Remove from Room', status: 'Wait for Room Assignment', statuses: 'Waiting to Enter the Room', class: 'btn-warning', prompt: false },
	];
	// Remove existing custom buttons
	grid.wrapper.find('.grid-footer').find('.btn-custom').hide();
	// Add new custom buttons
	if(frm.doc.status!=='Finished') {
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
						(values) => { updateChildStatus(frm, grid, button, values.reason); },
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
	}
};

// trigger methods
const updateChildStatus = async (frm, grid, button, reason = null) => {
	const selectedRows = grid.get_selected();
	if (selectedRows.length === 1) {
		let next = false;
		switch (button.label) {
			case 'Assign':
				next = await assign_to_room(frm);
				break;
			case 'Remove from Room':
				next = await remove_from_room(frm);
				break;
			case 'Retest':
				next = await retest(frm);
				break;
			case 'Refuse':
				next = await refuse_to_test(frm);
				break;
		}
		if (next) {
			showAlert(`Updated status to ${button.status} Successfully.`, 'green');
			if (reason) { addComment(frm, `${button.status} for the reason of: ${reason}`); }
			frm.reload_doc();
		}
	}
};

const setupRowSelector = (grid) => {
	grid.row_selector = (e) => {
		if (e.target.classList.contains('grid-row-check')) {
			const $row = $(e.target).closest('.grid-row');
			const docname = $row.attr('data-name');

			if (grid.selected_row && grid.selected_row === docname) {		
				$row.removeClass('grid-row-selected').find('.grid-row-check').prop('checked', false);
				grid.selected_row = null;
			} else {
				grid.$rows.removeClass('grid-row-selected').find('.grid-row-check').prop('checked', false);
				$row.addClass('grid-row-selected').find('.grid-row-check').prop('checked', true);
				grid.selected_row = docname;
			}
			grid.refresh_remove_rows_button();
			updateCustomButtonVisibility(grid);
		}
	};
	grid.wrapper.on('click', '.grid-row', () => { updateCustomButtonVisibility(grid); });
};

const updateCustomButtonVisibility = (grid) => {
	const selectedRows = grid.get_selected();
	const buttons = grid.wrapper.find('.grid-footer').find('.btn-custom');
	if (selectedRows && selectedRows.length === 1) {
		const child = locals[grid.doctype][selectedRows[0]];
		buttons.each((index, button) => {
			const $button = $(button);
			const buttonStatuses = $button.data('statuses');
			const statuses = buttonStatuses ? buttonStatuses.split(',') : [];
			$button.toggle(statuses.includes(child.status) || child.status === 'Started');
		});
	} else {
		buttons.hide();
	}
}

const createPromiseHandler = (method) => (frm) => new Promise((resolve) => {
	let selected_rows = frm.fields_dict['assignment_table'].grid.get_selected();
	if (selected_rows.length > 0 && selected_rows) {
		const child = locals[frm.fields_dict['assignment_table'].grid.doctype][selected_rows];
		frappe.call({
			method,
			args: {
				name: frm.doc.name,
				room: child.healthcare_service_unit,
			},
			callback: (r) => resolve(!!r.message),
			error: () => resolve(false),
		});
	} else {
		resolve(false);
	}
});

const assign_to_room = createPromiseHandler('kms.healthcare.create_service');
const remove_from_room = createPromiseHandler('kms.healthcare.remove_from_room');
const retest = createPromiseHandler('kms.healthcare.retest');
const refuse_to_test = createPromiseHandler('kms.healthcare.refuse_to_test');

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
