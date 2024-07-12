frappe.ui.form.on('Shift Type', {
	custom_create_schedule(frm) {
    if(frm.doc.__islocal && frm.doc.start_time && frm.doc.end_time){
      frm.doc.custom_weekly_assignment = [];
      for(let i=0; i<6; i++) {
        let row = frm.add_child("custom_weekly_assignment");
        const dayName = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
        row.day = dayName[i];
        row.from_time = frm.doc.start_time;
        row.to_time = frm.doc.end_time;
      }
      frm.refresh_field('custom_weekly_assignment');
    } else {
      frappe.msgprint('Please complete the entries of Start Time and End Time.');
    }
	}
});