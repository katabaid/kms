// Copyright (c) 2024, GIS and contributors
// For license information, please see license.txt

frappe.ui.form.on('Dispatcher', {
	refresh: function(frm) {
		frm.fields_dict['assign_room_button'].df.hidden = true;
		frm.refresh_field('assign_room_button');

		frm.fields_dict['assign_room_button'].input.onclick = function() {
			assign_room(frm);
		}
		frm.fields_dict['refuse_to_test_button'].input.onclick = function() {
			refuse_to_test(frm);
		}
	},

	onload_post_render: function(frm) {
		frm.fields_dict['assignment_table'].grid.wrapper.on('change', 'input, select', function() {
			check_button_state(frm);
		});
		frm.fields_dict['assignment_table'].grid.wrapper.on('change', '.grid-row-check', function() {
			check_button_state(frm);
		});
	}
});

function check_button_state(frm) {
	let show_button = false;
	let selected_rows = frm.fields_dict['assignment_table'].grid.get_selected_children();
	if (selected_rows.length > 0) {
		for (let row of selected_rows) {
			if(row.status === 'Wait for Room Assignment') {
				show_button = true;
			} else {
				show_button = false;
				break;
			}
		}
	} else {
		show_button = false;
	}
	frm.fields_dict['assign_room_button'].df.hidden = !show_button;
	frm.refresh_field('assign_room_button');
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

function assign_to_room(frm, hcsu) {
	frappe.db.get_value('Healthcare Service Unit', hcsu, 'service_unit_type').then(r=>{
		frappe.call({
			method: 'kms.kms.doctype.dispatcher.dispatcher.get_exam_items',
			args: {
				dispatcher_id: frm.doc.name,
				hcsu: hcsu,
				hcsu_type: r.message[0].service_unit_type,
			},
			callback: (r) => {
				frappe.msgprint('Room Assigned')
			}
		})
	})
}
