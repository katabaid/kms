// Copyright (c) 2024, GIS and contributors
// For license information, please see license.txt

frappe.ui.form.on('Dispatcher Tool', {
	refresh(frm) {
		frm.set_query('exam_id', ()=>{
			return{
				filters:{
					appointment_date: new Date().toISOString().split('T')[0]
				}
			}
		})
		frm.fields_dict["app"].grid.add_custom_button(__('Add to Queue'), function() {
			const qb = new frappe.ui.Dialog({
				title: 'Add to Queue',
				fields: {
					fieldname: 'sb_0',
					fieldtype: 'Section Break',
					label: 'Pricing'
				},
				size: 'extra-large',
			})
			qb.show();
		});
        frm.fields_dict["app"].grid.grid_buttons.find('.btn-custom').removeClass('btn-default').addClass('btn-primary');

	},
	exam_id(frm) {
		frappe.call({
			method: 'kms.kms.doctype.dispatcher_tool.dispatcher_tool.get_room',
			args: {
				exam_id: frm.doc.exam_id
			},
			callback: (r) => {
				frappe.msgprint(r.message[0].room)
			}
		})
	},});
