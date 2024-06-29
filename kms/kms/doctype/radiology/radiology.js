frappe.ui.form.on('Radiology', {
	template: (frm) => {
		if(frm.doc.template) {
			frappe.db.get_doc('Radiology Result Template', frm.doc.template).then(doc=>{
				$.each(doc.items, (key, value) => {
					let result = cur_frm.add_child('result');
					result.result_line = value.result_text;
					result.normal_value = value.normal_value;
					result.result_check = value.normal_value;
					result.item_code = doc.item_code;
					result.result_options = value.result_select;
					frappe.db.get_value('Item', doc.item_code, 'item_name').then(i => {result.item_name =i.message.item_name});
				});
				frm.refresh_field('result');
				$.each(doc.items, (key, value) => {
					frm.fields_dict.result.grid.grid_rows[key].docfields[3].options = value.result_select.split("\n");
						console.log(frm.fields_dict.result.grid);
				});
			});
		}
	},
	appointment: (frm) => {
		frm.add_fetch('appointment', 'patient', 'patient');
	},
	queue_pooling: (frm) => {
		frm.add_fetch('queue_pooling', 'appointment', 'appointment');
		frm.add_fetch('queue_pooling', 'patient', 'patient');
	},
	refresh: (frm) => {
	  frm.set_query('appointment', () =>{
			return {
				filters: {
					status: ['in', ['Open', 'Checked In']]
				}
			};
	  });
	  frm.set_query('queue_pooling', () =>{
			return {
				filters: {
					status: ['in', ['Queued', 'Ongoing']]
				}
			};
	  });
	  frm.set_query('service_unit', () => {
			return {
				filters: {
					service_unit_type: 'Radiology'
				}
			};
	  });
	},
	setup(frm) {
		frm.set_query('service_unit', () => {
			return{
				filters: {
					is_group: 0,
					company: frm.doc.company
				}
			};
		});
		if(frm.doc.result&&frm.doc.docstatus===0){
			frm.refresh_field('result');
			$.each(frm.doc.result, (key, value) => {
				frm.fields_dict.result.grid.grid_rows[key].docfields[3].options = value.result_options;
			});
		}
	}
});

frappe.ui.form.on('Radiology Result', {
	result_check(frm, cdt, cdn) {
		let d = locals[cdt][cdn];
		let current_row = frm.fields_dict.result.grid.grid_rows_by_docname[d.name];
		current_row.toggle_editable('result_text', (d.result_check !== d.normal_value));
		current_row.toggle_reqd('result_text', (d.result_check !== d.normal_value));
	}
});