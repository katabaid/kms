// Copyright (c) 2024, GIS and contributors
// For license information, please see license.txt

frappe.ui.form.on('Doctor Examination', {
	refresh: function(frm) {
		if(frm.doc.checked_in) {
			frm.remove_custom_button('Check In');
		}
		if(frm.doc.docstatus === 0) {
			if(frm.doc.dispatcher) {
				if(frm.doc.status==='Started'){
					frm.add_custom_button('Check In', ()=>{
						frappe.call({
							method: 'kms.kms.doctype.dispatcher.dispatcher.checkin_room',
							args: {
								'dispatcher_id': frm.doc.dispatcher,
								'hsu': frm.doc.service_unit,
								'doctype': 'Doctor Examination',
								'docname': frm.doc.name
							},
							callback: function(r) {
								if(r.message) {
									frappe.show_alert({
										message: r.message,
										indicator: 'green'
									}, 5);
									frm.doc.status = 'Checked In';
									frm.dirty();
									frm.save();
								}
							}
						})
					}, 'Status');
					frm.add_custom_button('Remove', ()=>{
						frappe.call({
							method: 'kms.kms.doctype.dispatcher.dispatcher.removed_from_room',
							args: {
								'dispatcher_id': frm.doc.dispatcher,
								'hsu': frm.doc.service_unit,
							},
							callback: function(r) {
								if(r.message) {
									frappe.show_alert({
										message: r.message,
										indicator: 'green'
									}, 5);
									frm.doc.status = 'Removed';
									frm.dirty();
									frm.save();
								}
							}
						})
					}, 'Status');
				} else if(frm.doc.status==='Checked In'){
					frm.remove_custom_button('Check In', 'Status');
				} else {
					frm.remove_custom_button('Remove', 'Status');
					frm.remove_custom_button('Check In', 'Status');
				}
			}
			if(frm.doc.result){
				frm.refresh_field('result');
				$.each(frm.doc.result, (key, value) => {
					frm.fields_dict.result.grid.grid_rows[key].docfields[3].options = value.result_options;
				});
			}
		}
		frm.fields_dict['result'].grid.wrapper.find('.grid-add-row').hide();
		frm.fields_dict['non_selective_result'].grid.wrapper.find('.grid-add-row').hide();
		frm.fields_dict['examination_item'].grid.wrapper.find('.grid-add-row').hide();
		frm.fields_dict['result'].grid.wrapper.find('.grid-remove-rows').hide();
		frm.fields_dict['non_selective_result'].grid.wrapper.find('.grid-remove-rows').hide();
		frm.fields_dict['examination_item'].grid.wrapper.find('.grid-remove-rows').hide();		
	},
	before_submit: function(frm) {
		if(frm.doc.dispatcher) {
			frappe.call({
				method: 'kms.kms.doctype.dispatcher.dispatcher.finish_exam',
				args: {
					'dispatcher_id': frm.doc.dispatcher,
					'hsu': frm.doc.service_unit,
				},
				callback: function(r) {
					if(r.message) {
						frappe.show_alert({
							message: r.message,
							indicator: 'green'
						}, 5)
					}
				}
			})
		}
	}
});
