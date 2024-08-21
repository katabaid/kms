// Copyright (c) 2024, GIS and contributors
// For license information, please see license.txt
let utilsLoaded = false;
frappe.ui.form.on('Dispatcher', {
	refresh: function (frm) {
		addFinishButtons(frm);
		hideStandardButtonOnChildTable(frm, childTables);
		addCustomButtonOnChildTable(frm);
		addCustomButtononPackage(frm);
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
		frappe.require('/assets/kms/js/utils.js', () => {
			utilsLoaded = true;
		});
	},
});

const childTables = ['assignment_table', 'package'];
const childTableButton = 'assignment_table';

const addCustomButtononPackage = (frm) => {
	let child_table = frm.fields_dict['package'].grid;
	if (child_table) {
		// hide standard buttons
		const customButton = child_table.add_custom_button(
			'Retest',
			() => { frappe.msgprint('tes') },
			'btn-custom'
		);
		customButton.addClass("btn-warning btn-xs").removeClass("btn-default btn-secondary");
		customButton.hide()
		//test condition on selected row to show button
		child_table.wrapper.on('change', '.grid-row-check', function() {
			const selected_rows = child_table.get_selected()
			const buttons = child_table.wrapper.find('.grid-footer').find('.btn-custom');
			if (selected_rows.length === 1) {
				const selected_doc = child_table.get_selected_children()[0];
				customButton.toggle(selected_doc.status >= 'Started');
			} else {
				buttons.hide();
			}
		})
	}
}

// triggers
const addFinishButtons = (frm) => {
	if (frm.doc.status === 'Waiting to Finish') {
		frm.add_custom_button('Finish', () => {
			frm.doc.status = 'Finished';
			frm.dirty();
			frm.save();
		});
	}
};

const hideStandardButtonOnChildTable = (frm, childTablesArray) => {
	childTablesArray.forEach((field) => {
		frm.fields_dict[field].grid.wrapper.find('.grid-add-row, .grid-remove-rows').hide();
		frm.fields_dict[field].grid.wrapper.find('.row-index').hide();
		// Remove buttons from detail view dialog
		frm.fields_dict[field].grid.grid_rows.forEach(function(row) {
			//row.wrapper.find('.row-check').hide(); // Hide the checkbox
			row.wrapper.find('.btn-open-row').on('click', function() {
				setTimeout(function() {
					$('.grid-row-open').find('.grid-delete-row, .grid-insert-row-below, .grid-duplicate-row, .grid-insert-row, .grid-move-row, .grid-append-row').hide();
				}, 100);
			});
		});
	});
};

const addCustomButtonOnChildTable = (frm) => {
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
			if (utilsLoaded && kms.utils) {
				kms.utils.show_alert(`Updated status to ${button.status} Successfully.`, 'green');
			}
			if (reason) { 
				if (utilsLoaded && kms.utils) {
					kms.utils.add_comment(
						frm.doc.doctype,
						frm.doc.name,
						`${button.status} for the reason of: ${reason}`,
						frappe.session.user_fullname,
						'Comment added successfully.'
					) 
				}
			}
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
