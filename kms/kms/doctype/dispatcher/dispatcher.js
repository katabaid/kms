// Copyright (c) 2024, GIS and contributors
// For license information, please see license.txt
let utilsLoaded = false;
frappe.ui.form.on('Dispatcher', {
	refresh: function (frm) {
		addFinishButtons(frm);
		addFinishMealButtons(frm);
		addMealButtons(frm);
		hideStandardButtonOnChildTable(frm, childTables);
		addCustomButtonOnRoom(frm);
		addCustomButtonOnPackage(frm);
		addSidebarUserAction(frm);
		refreshRoomResidence(frm);
		frm.disable_save();
	},
	onload: function (frm) {
		frappe.breadcrumbs.add('Healthcare', 'Dispatcher');
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

const addCustomButtonOnPackage = (frm) => {
	let child_table = frm.fields_dict['package'].grid;
	if (child_table && frm.doc.status !== 'Finished') {
		// hide standard buttons
		const customButton = child_table.add_custom_button(
			'Retest',
			() => { 
				let selected_rows = frm.fields_dict['package'].grid.get_selected();
				if (selected_rows && selected_rows.length === 1) {
					const child = locals[frm.fields_dict['package'].grid.doctype][selected_rows];
					frappe.call({
						method: 'kms.healthcare.exam_retest',
						args: {
							name: frm.doc.name,
							item: child.examination_item,
							item_name: child.item_name,
						},
						callback: (r) => {
							if (utilsLoaded && kms.utils) {
								kms.utils.show_alert(`Marked ${child.examination_item} to retest successfully.`, 'green');
							}				
							frm.reload_doc();
						},
						error: (err) => { frappe.msgprint(err) }
					});
				}
			},
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
				customButton.toggle(selected_doc.status === 'Finished');
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

const addFinishMealButtons = (frm) => {
	if (frm.doc.status === 'Meal Time') {
		frm.add_custom_button('Finish Meal', () => {
			frm.doc.status = 'In Queue';
			frm.dirty();
			frm.save();
		});
	}
};

const addMealButtons = (frm) => {
	if (frm.doc.meal_time && frm.doc.status === 'In Queue') {
		frm.add_custom_button('Meal Time', () => {
			frm.doc.status = 'Meal Time';
			frm.doc.meal_time = frappe.datetime.now_datetime();
			frm.dirty();
			frm.save();
		});
	}
};

const addSidebarUserAction = (frm) => {
	frm.sidebar
	.add_user_action(__('Check Patient Result'))
	.attr('href', `/app/query-report/Result per Appointment?exam_id=${frm.doc.patient_appointment}`)
	.attr('target', '_blank')
	frm.sidebar
	.add_user_action(__('Exam Notes'))
	.attr('href', `/app/query-report/Exam%20Notes%20per%20Appointment?exam_id=${frm.doc.patient_appointment}`)
	.attr('target', '_blank')
};

const hideStandardButtonOnChildTable = (frm, childTablesArray) => {
	childTablesArray.forEach((field) => {
		frm.set_df_property(field, 'cannot_add_rows', true);
    frm.set_df_property(field, 'cannot_delete_rows', true);
    frm.set_df_property(field, 'cannot_delete_all_rows', true);
    frm.fields_dict[field].grid.wrapper.find('.row-index').hide();
	});
};

const addCustomButtonOnRoom = (frm) => {
	const grid = frm.fields_dict[childTableButton].grid;
	const buttons = [
		{ label: 'Assign', status: 'Waiting to Enter the Room', statuses: 'Wait for Room Assignment,Additional or Retest Request', class: 'btn-primary', prompt: false },
		{ label: 'Refuse', status: 'Refused', statuses: 'Wait for Room Assignment', class: 'btn-danger', prompt: true },
		{ label: 'Reschedule', status: 'Rescheduled', statuses: 'Wait for Room Assignment,Additional or Retest Request', class: 'btn-warning', prompt: true },
		{ label: 'Remove from Room', status: 'Wait for Room Assignment', statuses: 'Waiting to Enter the Room', class: 'btn-info', prompt: false },
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
		customButton
		.removeClass("btn-default btn-secondary")
		.addClass(`${button.class} btn-sm`)
		.attr('data-statuses', button.statuses)
		.hide();
		});
		setupRowSelector(grid);
	}
};

const refreshRoomResidence = (frm) => {

}
// trigger methods
const updateChildStatus = async (frm, grid, button, reason = null) => {
	const selectedRows = grid.get_selected();
	if (selectedRows.length === 1) {
		let next = false;
		if (frm.doc.status == 'Meal Time') frappe.throw('Cannot modify room assignment. Patient is still on meal time break.');
		if (button.label === 'Assign') next = await assign_to_room(frm);
		else if (button.label === 'Remove from Room') next = await remove_from_room(frm);
		else if (button.label === 'Reschedule') next = await reschedule(frm);
		else if (button.label === 'Refuse') next = await refuse_to_test(frm);
		if (next) {
			if (utilsLoaded && kms.utils) {
				kms.utils.show_alert(`Updated status to ${button.status} successfully.`, 'green');
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
			frappe.set_route('List', 'Dispatcher', 'List');
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
	if (frm.doc.room && frm.doc.status === 'In Room' && method === 'kms.healthcare.remove_from_room') {
		frappe.throw(`Patient ${frm.doc.patient} is already in ${frm.doc.room} room.`);
	} else if (frm.doc.room && frm.doc.status === 'In Queue' && method !== 'kms.healthcare.remove_from_room') {
		frappe.throw(`Patient ${frm.doc.patient} is already in a queue for ${frm.doc.room} room.`);
	} else {
		if (selected_rows.length > 0 && selected_rows) {
			const child = locals[frm.fields_dict['assignment_table'].grid.doctype][selected_rows];
			frappe.call({
				method,
				args: {
					name: frm.doc.name,
					room: child.healthcare_service_unit,
				},
				callback: (r) => {console.log(`r: ${r}`);resolve(!!r.message)},
				error: (err) => {resolve(false)},
			});
		} else {
			resolve(false);
		}
	}
});

const assign_to_room = createPromiseHandler('kms.healthcare.create_service');
const remove_from_room = createPromiseHandler('kms.healthcare.remove_from_room');
const reschedule = createPromiseHandler('kms.api.dispatcher.reschedule');
const refuse_to_test = createPromiseHandler('kms.healthcare.refuse_to_test');
