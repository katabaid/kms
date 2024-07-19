// Copyright (c) 2024, GIS and contributors
// For license information, please see license.txt

frappe.ui.form.on('Nurse Examination', {
	refresh: function(frm) {
		frm.trigger('process_custom_buttons');
		frm.trigger('hide_standard_child_tables_buttons');
		frm.trigger('setup_child_table_custom_buttons');
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
	},

	hide_standard_child_tables_buttons(frm) {
		frm.fields_dict['result'].grid.wrapper.find('.grid-add-row').hide();
		frm.fields_dict['non_selective_result'].grid.wrapper.find('.grid-add-row').hide();
		frm.fields_dict['examination_item'].grid.wrapper.find('.grid-add-row').hide();
		frm.fields_dict['result'].grid.wrapper.find('.grid-remove-rows').hide();
		frm.fields_dict['non_selective_result'].grid.wrapper.find('.grid-remove-rows').hide();
		frm.fields_dict['examination_item'].grid.wrapper.find('.grid-remove-rows').hide();
	},
	
	process_custom_buttons(frm) {
		console.log('process_custom_buttons')
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
								'doctype': 'Nurse Examination',
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
	},
	
	process_custom_buttons(frm) {
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
										indicator: 'red'
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
	},
	
	setup_child_table_custom_buttons(frm) {
		let grid = frm.fields_dict['examination_item'].grid;
			
		// Remove existing custom button if any
		grid.wrapper.find('.grid-footer').find('.btn-custom').remove();
		
		// Add custom button (initially hidden)
		let finishButton = grid.add_custom_button(__('Finish'), function() {
			let selected_row = grid.get_selected();
			if (selected_row.length === 1) {
				let child = locals[grid.doctype][selected_row[0]];
				if (child.status === 'Started') {
					frappe.model.set_value(child.doctype, child.name, 'status', 'Finished');
					updateParentStatus(frm).then(() => {
						frm.save().then(()=>{
							frappe.show_alert({
								message: 'Updated status to Finished Successfully.',
								indicator: 'green'
							}, 5);
							frm.refresh()
						}).catch((err)=>{
							frappe.msgprint(__('Error updating status: {0}', [err.message]));
						});
					})
				}
			}
		}, 'btn-custom');
		let refuseButton = grid.add_custom_button(__('Refuse'), function() {
			let selected_row = grid.get_selected();
			if (selected_row.length === 1) {
				let child = locals[grid.doctype][selected_row[0]];
				if (child.status === 'Started') {
					frappe.model.set_value(child.doctype, child.name, 'status', 'Refused');
					updateParentStatus(frm).then(() => {
						frm.save().then(()=>{
							frappe.show_alert({
								message: 'Updated status to Refused Successfully.',
								indicator: 'red'
							}, 5);
							frm.refresh()
						}).catch((err)=>{
							frappe.msgprint(__('Error updating status: {0}', [err.message]));
						});
					})
				}
			}
		}, 'btn-custom');
		let rescheduleButton = grid.add_custom_button(__('Reschedule'), function() {
			let selected_row = grid.get_selected();
			if (selected_row.length === 1) {
				let child = locals[grid.doctype][selected_row[0]];
				if (child.status === 'Started') {
					frappe.model.set_value(child.doctype, child.name, 'status', 'Rescheduled');
					updateParentStatus(frm).then(() => {
						frm.save().then(()=>{
							frappe.show_alert({
								message: 'Updated status to Rescheduled Successfully.',
								indicator: 'orange'
							}, 5);
							frm.refresh()
						}).catch((err)=>{
							frappe.msgprint(__('Error updating status: {0}', [err.message]));
						});
					})
				}
			}
		}, 'btn-custom');
	
		// Apply button styling
		finishButton.addClass('btn-primary btn-sm');
		refuseButton.addClass('btn-danger btn-sm');
		rescheduleButton.addClass('btn-warning btn-sm');
		
		// Initially hide the button
		finishButton.hide(); 
		refuseButton.hide();
		rescheduleButton.hide();
		
		// Override grid's row selection method
		grid.row_selector = function(e) {
			if (e.target.classList.contains('grid-row-check')) {
				let $row = $(e.target).closest('.grid-row');
				let docname = $row.attr('data-name');
				
				if (this.selected_row && this.selected_row === docname) {
					// Deselect the row
					$row.removeClass('grid-row-selected');
					$row.find('.grid-row-check').prop('checked', false);
					this.selected_row = null;
				} else {
					// Deselect all rows
					this.$rows.removeClass('grid-row-selected');
					this.$rows.find('.grid-row-check').prop('checked', false);
					// Select the clicked row
					$row.addClass('grid-row-selected');
					$row.find('.grid-row-check').prop('checked', true);
					this.selected_row = docname;
				}
				
				this.refresh_remove_rows_button();
				updateCustomButton();
		}		}
		
		// Function to update custom button visibility
		function updateCustomButton() {
			let selected_rows = grid.get_selected();
			if (selected_rows && selected_rows.length === 1) {
				let child = locals[grid.doctype][selected_rows];
				if (child.status === 'Started') {
					finishButton.show();
					refuseButton.show();
					rescheduleButton.show();
				} else {
					finishButton.hide();
					refuseButton.hide();
					rescheduleButton.hide();
				}
			} else {
				finishButton.hide();
				refuseButton.hide();
				rescheduleButton.hide();
			}
		}
		
		// Bind updateCustomButton to row selection
		grid.wrapper.on('click', '.grid-row', function() {
			updateCustomButton();
		});
		
		// Update button visibility when field_name changes
		frappe.ui.form.on('ChildDocType', {
			template: function(frm, cdt, cdn) {
				updateCustomButton();
			}
		});

		// Function to update parent status
		function updateParentStatus(frm) {
			return new Promise((resolve) => {
				let hasStarted = false;
				let hasRefusedOrRescheduled = false;
				let allFinished = true;
				
				frm.doc.examination_item.forEach(row => {
					if (row.status === 'Started') {
						hasStarted = true;
						allFinished = false;
					} else if (row.status === 'Refused' || row.status === 'Rescheduled') {
						hasRefusedOrRescheduled = true;
						allFinished = false;
					} else if (row.status !== 'Finish') {
						allFinished = false;
					}
				});
				
				if (hasStarted) {
					// Do nothing
					resolve();
				} else if (hasRefusedOrRescheduled || !allFinished) {
					frm.set_value('status', 'Partial Finished');
					resolve();
				} else {
					frm.set_value('status', 'Finished');
					resolve();
				}
			});
		}
	}
});
