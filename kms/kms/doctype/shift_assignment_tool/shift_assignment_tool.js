// Copyright (c) 2024, GIS and contributors
// For license information, please see license.txt

frappe.ui.form.on('Shift Assignment Tool', {
	refresh(frm) {
		if(!frm.doc.week_number){
		    frappe.call({
		        method: 'kms.kms.doctype.week_number.week_number.get_current_week_number',
		        callback: (r) => {
		            frm.doc.week_number=r.message[0].current_week_number;
		            frm.doc.from_date=r.message[0].start_date_of_week;
		            frm.doc.to_date=r.message[0].end_date_of_week;
		            frm.refresh_field('week_number');
		            frm.refresh_field('from_date');
		            frm.refresh_field('to_date');
		        }
		    });
		}
	},
	week_number(frm){
	    frm.doc.from_date='';
	    frm.doc.to_date='';
	    frappe.call({
	        method: 'kms.kms.doctype.week_number.week_number.get_week_number_info',
	        args: {
	            week_number: frm.doc.week_number
	        },
	        callback: (r) => {
	            frm.doc.from_date=r.message[0].start_date_of_week;
	            frm.doc.to_date=r.message[0].end_date_of_week;
	            frm.refresh_field('from_date');
	            frm.refresh_field('to_date');
	        }
	    });
	}
});