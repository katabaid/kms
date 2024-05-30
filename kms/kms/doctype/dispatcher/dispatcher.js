// Copyright (c) 2024, GIS and contributors
// For license information, please see license.txt

frappe.ui.form.on('Dispatcher', {
	refresh: function(frm) {
		frm.fields_dict['assign_room_button'].df.hidden = true;
		frm.fields_dict['refuse_to_test_button'].df.hidden = true;
		frm.fields_dict['retest_button'].df.hidden = true;
		frm.refresh_field('assign_room_button');
		frm.refresh_field('refuse_to_test_button');
		frm.refresh_field('retest_button');

		frm.fields_dict['assign_room_button'].input.onclick = function() {
			assign_room(frm);
		}
		frm.fields_dict['refuse_to_test_button'].input.onclick = function() {
			refuse_to_test(frm);
		}
		frm.fields_dict['retest_button'].input.onclick = function() {
			retest(frm);
		}
	},

	onload_post_render: function(frm) {
		frm.fields_dict['assignment_table'].grid.wrapper.on('change', 'input, select', function() {
			check_button_state(frm);
		});
		frm.fields_dict['assignment_table'].grid.wrapper.on('change', '.grid-row-check', function() {
			check_button_state(frm);
		});
		frm.fields_dict['assignment_table'].grid.wrapper.find('.grid-add-row').hide();
		//NOT WORKING!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
		frm.fields_dict['assignment_table'].grid.grid_rows.forEach(row => {
			$(row.wrapper).find('.grid-delete-row').hide();
		});
	},

	setup: function(frm) {
		//NOT WOPRKING!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
		frm.set_indicator_formatter("healthcare_service_unit", function(doc){
			return "red";
		})
	}
});

function check_button_state(frm) {
	let show_assign_room_button = false;
	let show_refuse_to_test_button = false;
	let show_retest_button = false;
	let selected_rows = frm.fields_dict['assignment_table'].grid.get_selected_children();
	if (selected_rows.length > 0) {
		for (let row of selected_rows) {
			if(row.status === 'Wait for Room Assignment') {
				show_assign_room_button = true;
			} else {
				show_assign_room_button = false;
				break;
			}
		}
		for (let row of selected_rows) {
			if(row.status === 'Finished Examination') {
				show_retest_button = true;
			} else {
				show_retest_button = false;
				break;
			}
		}
		for (let row of selected_rows) {
			if(row.status != 'Refused to Test') {
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
}

function assign_room(frm) {
	let selected_rows = frm.fields_dict['assignment_table'].grid.get_selected_children();
	if(selected_rows.length > 0 && selected_rows) {
		selected_rows.forEach(row => {
			if(row.status === 'Wait for Room Assignment'){
				assign_to_room(frm, row.healthcare_service_unit)
			}
		})
	}
}

function refuse_to_test(frm) {
	let selected_rows = frm.fields_dict['assignment_table'].grid.get_selected_children();
	if(selected_rows.length > 0 && selected_rows) {
		selected_rows.forEach(row => {
			frappe.model.set_value(row.doctype, row.name, 'status', 'Refused to Test');
		})
		frm.save()
	}
}

function retest(frm) {
	let selected_rows = frm.fields_dict['assignment_table'].grid.get_selected_children();
	if(selected_rows.length > 0 && selected_rows) {
		selected_rows.forEach(row => {
			frappe.throw('ValidationError:')
		})
		//frm.save()
	}
}

function assign_to_room(frm) {
	//define selected rooms to process
	let selected_rows = frm.fields_dict['assignment_table'].grid.get_selected_children();
	if(selected_rows.length > 0 && selected_rows) {
		selected_rows.forEach(row => {
			//for each room define what method to call
			frappe.db.get_value('Healthcare Service Unit', row.healthcare_service_unit, 'service_unit_type').then(hsu=>{
				frappe.db.get_value('Healthcare Service Unit Type', hsu.message.service_unit_type, 'custom_default_doctype').then(dt=>{
					// Lab
					if (dt.message.custom_default_doctype=='Sample Collection') {
						frappe.call({
							method: 'kms.api.create_sample_and_test',
							args: {
								'disp': frm.doc.name,
								'selected': row.healthcare_service_unit
							},
							callback: function(r) {
								if(r.message) {
									frappe.model.set_value(row.doctype, row.name, 'status', 'Waiting to Enter the Room');
									frm.save()
									frappe.show_alert({
										message: 'Room assigned successfully.',
										indicator: 'green'
									})
								}
							}
						})
					}
					// Radiology
					// Nurse

				})
			})
			
		})
	}
}
