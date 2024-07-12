// Copyright (c) 2024, GIS and contributors
// For license information, please see license.txt

frappe.ui.form.on('Queue Pooling', {
	refresh(frm) {
		if(frm.doc.status === 'Queued'&& !frm.doc.encounter){
			const now = new Date();
			const hour = now.getHours();
			const minute = now.getMinutes();
			const second = now.getSeconds();
			const formattedTime = hour + ":" + minute + ":" + second;
			frm.add_custom_button(
				__('Cancel'),
				()=> {
					frappe.prompt([
						{
							label: 'Cancel Reason',
							fieldname: 'cancel_reason',
							fieldtype: 'Data',
							reqd: true
						}], (values)=>{
							frappe.db.set_value('Queue Pooling', frm.doc.name, {
								status: 'Cancelled',
								cancelled_time: formattedTime,
								cancel_reason: values.cancel_reason
							});
						}
					);
				}
			);
			frm.add_custom_button(
				__('Create Encounter'), 
				()=>{
					frappe.new_doc('Patient Encounter',{
						appointment: frm.doc.appointment,
						patient: frm.doc.patient,
						company: frm.doc.company,
						custom_queue_pooling: frm.doc.name,
						custom_service_unit: frm.doc.service_unit
					});
				}
			);
		}
	}
});