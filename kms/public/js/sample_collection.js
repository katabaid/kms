frappe.ui.form.on('Sample Collection', {
	setup(frm) {
		frm.set_query('custom_service_unit', () => {
			return {
				filters: {
					is_group: 0,
					company: frm.doc.company
				}
			};
		});
	},
	refresh(frm) { 
	    //Initialize buttons 
		frm.add_custom_button('Remove', () => {
			remove(frm);
		}, 'Status');
		frm.fields_dict['custom_refuse'].df.hidden = true;
		frm.refresh_field('custom_refuse');
		frm.fields_dict['custom_give_cup'].df.hidden = true;
		frm.refresh_field('custom_give_cup'); 
		//populate lab test data 
		if (frm.doc.custom_lab_test) {
			frappe.db.get_doc('Lab Test', frm.doc.custom_lab_test).then(doc => {
				cur_frm.fields_dict.custom_lab_test_table.$wrapper.empty();
				cur_frm.fields_dict.custom_lab_test_table.$wrapper.append(`<table class="form-grid"><thead class="grid-heading-row"><tr class="grid-row"><th class="col grid-static-col col-xs-2 ">Test Name</th><th class="col grid-static-col col-xs-2 ">Event</th><th class="col grid-static-col col-xs-1 ">UOM</th><th class="col grid-static-col col-xs-2 ">Min Value</th><th class="col grid-static-col col-xs-2 ">Max Value</th></tr></thead><tbody class="grid-body">`);
				$.each(doc.normal_test_items, (_i, e) => {
					cur_frm.fields_dict.custom_lab_test_table.$wrapper.append(`<tr class="grid-row"><td class="col grid-static-col col-xs-2 ">${e.lab_test_name}</td><td class="col grid-static-col col-xs-2 ">${e.lab_test_event}</td><td class="col grid-static-col col-xs-1 ">${e.lab_test_uom?e.lab_test_uom:''}</td><td class="col grid-static-col col-xs-2" style="text-align: right">${e.custom_min_value}</td><td class="col grid-static-col col-xs-2" style="text-align: right">${e.custom_max_value}</td></tr>`);
				});
				cur_frm.fields_dict.custom_lab_test_table.$wrapper.append(`</tbody></table>`);
			});
		} 
		//setup Refuse button 
		if (frm.doc.custom_status === 'Started') {
			frm.fields_dict['custom_refuse'].input.onclick = function() {
				refuse_to_test(frm);
			};
			frm.add_custom_button('Check In', () => {
        frappe.call({
          method: 'kms.sample_collection.check_in',
          args: {
            name: frm.doc.name
          },
          callback: function(r) {
            if(r.message){
              frm.reload_doc();
            }
          }
        });
			}, 'Status');
		}
		if (frm.doc.custom_status === 'Checked In') {
			frm.fields_dict['custom_give_cup'].input.onclick = function() {
				give_cup(frm);
			};
			frm.fields_dict['custom_refuse'].input.onclick = function() {
				refuse_to_test(frm);
			};
			frm.trigger('check_lines_status');
		}
		if (frm.doc.custom_status === 'Partially Finished') {
			frm.remove_custom_button('Remove', 'Status');
		}
		if (frm.doc.custom_status === 'Refused') {
			frm.remove_custom_button('Remove', 'Status');
		}
		if (frm.doc.custom_status === 'Finished') {
			frm.remove_custom_button('Remove', 'Status');
		}
		if (frm.doc.custom_status === 'Removed') {
			frm.remove_custom_button('Remove', 'Status');
		}
		// hide add and delete buttons
		frm.fields_dict['custom_sample_table'].grid.wrapper.find('.grid-add-row').hide();
		frm.fields_dict['custom_sample_table'].grid.wrapper.find('.grid-remove-rows').hide();
	},
	before_submit(frm) {
		if (frm.doc.custom_status === 'Partially Finished' || frm.doc.custom_status === 'Finished') {
      frm.doc.collected_by = frappe.session.user;
      let sekarang = new Date();
      frm.doc.collected_time = formatDate(sekarang);
			frm.refresh_field('collected_by');
			frm.refresh_field('collected_time');
			frm.save();
			if (frm.doc.custom_dispatcher) {
				frappe.call({
					method: 'frappe.client.get',
					args: {
						doctype: 'Dispatcher',
						name: frm.doc.custom_dispatcher
					},
					callback: function(response) {
						if (response.message) {
							let disp_doc = response.message;
							console.log('a')
							let count_row = 0;
							let count_finished = 0;
							disp_doc.assignment_table.forEach(row => {
                count_row += 1;
                if (row.status === 'Finished Examination'||row.status === 'Refused to Test') count_finished += 1;
								if (row.healthcare_service_unit == frm.doc.custom_service_unit) {
                  row.status = 'Finished Examination';
                  count_finished += 1;
								}
							});
							if (count_row === count_finished) {
                disp_doc.status = 'Waiting to Finish';
                disp_doc.room = '';
							} else {
                disp_doc.status = 'In Queue';
                disp_doc.room = '';
							}
							frappe.call({
								method: 'frappe.client.save',
								args: {
									doc: disp_doc
								},
								callback: function(save_response) {
									console.log(save_response)
									frappe.msgprint('Dispatcher status updated with Finished Examination.');
								}
							});
						}
					}
				});
			}
		} else {
			frappe.throw('Status must be Partially Finished or Finished to Submit.');
		}
	},
	onload_post_render(frm) {
		frm.fields_dict['custom_sample_table'].grid.wrapper.on('change', 'input, select', function() {
			check_button_state(frm);
		});
		frm.fields_dict['custom_sample_table'].grid.wrapper.on('change', '.grid-row-check', function() {
			check_button_state(frm);
		});
	},
	check_lines_status(frm) {
		const total_rows = frm.doc.custom_sample_table.length;
		let finished_rows = 0;
		let refused_rows = 0;
		frm.doc.custom_sample_table.forEach(row => {
			if (row.status === 'Finished') {
				finished_rows += 1;
			} else if (row.status === 'Refused') {
				refused_rows += 1;
			}
		});
		if (total_rows === finished_rows) {
			frm.doc.custom_status = 'Finished';
			frm.refresh_field('custom_status');
			frm.dirty();
			frm.save();
		} else if (total_rows === refused_rows) {
			frm.doc.custom_status = 'Refused';
			frm.refresh_field('custom_status');
			frm.dirty();
			frm.save();
		} else if (total_rows === refused_rows + finished_rows) {
			frm.doc.custom_status = 'Partially Finished';
			frm.refresh_field('custom_status');
			frm.dirty();
			frm.save();
		}
	}
});

function check_button_state(frm) {
	let show_refuse_to_test_button = false;
	let show_give_cup_button = false;
	let selected_rows = frm.fields_dict['custom_sample_table'].grid.get_selected_children();
	if (selected_rows.length > 0) {
		for (let row of selected_rows) {
			if (row.status === 'Checked In') {
				show_give_cup_button = true;
				show_refuse_to_test_button = true;
			} else {
				show_give_cup_button = false;
				show_refuse_to_test_button = false;
				continue;
			}
		}
	}
	frm.fields_dict['custom_refuse'].df.hidden = !show_refuse_to_test_button;
	frm.refresh_field('custom_refuse');
	frm.fields_dict['custom_give_cup'].df.hidden = !show_give_cup_button;
	frm.refresh_field('custom_give_cup');
}

function refuse_to_test(frm) {
	let selected_rows = frm.fields_dict['custom_sample_table'].grid.get_selected_children();
	if (selected_rows.length > 0 && selected_rows) {
    frappe.prompt('Enter refuse reason', ({value})=>{
      frappe.call({
        method: 'kms.sample_collection.refuse_to_test',
        args: {
          name: frm.doc.name,
          selected: selected_rows,
          reason: value
        },
        callback: function(r) {
          if(r.message){
            frm.reload_doc();
          }
        }
      })
    })
	}
}

function give_cup(frm) {
	let selected_rows = frm.fields_dict['custom_sample_table'].grid.get_selected_children();
	if (selected_rows.length > 0 && selected_rows) {
		selected_rows.forEach(row => {
			frappe.model.set_value(row.doctype, row.name, 'status', 'Finished');
		});
		frm.save();
		frm.refresh_field('custom_sample_table');
	}
}

function remove(frm) {
  frappe.prompt('Enter reason to remove', ({value})=>{
    frappe.call({
      method: 'kms.sample_collection.remove',
      args: {
        name: frm.doc.name,
        reason: value
      },
      callback: function(r) {
        if(r.message) {
          frm.reload_doc();
        }
      }
    })
  })
}

function formatDate(date) {
  const pad = (num) => (num < 10 ? '0' : '') + num;

  const day = pad(date.getDate());
  const month = pad(date.getMonth() + 1); // Months are zero-based
  const year = date.getFullYear();
  const hours = pad(date.getHours());
  const minutes = pad(date.getMinutes());
  const seconds = pad(date.getSeconds());

  return `${day}-${month}-${year} ${hours}:${minutes}:${seconds}`;
}