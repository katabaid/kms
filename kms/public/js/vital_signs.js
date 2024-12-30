frappe.ui.form.on('Vital Signs', {
	height: function(frm) {
		if (frm.doc.height && frm.doc.weight) {
			calculate_bmi(frm);
		}
	},

	weight: function(frm) {
		if (frm.doc.height && frm.doc.weight) {
			calculate_bmi(frm);
		}
	},

});

calculate_bmi = function(frm){
	// Reference https://en.wikipedia.org/wiki/Body_mass_index
	// bmi = weight (in Kg) / height * height (in Meter)
	let bmi = (frm.doc.weight / (frm.doc.height * frm.doc.height / 10000)).toFixed(2);
	let bmi_note = null;
	if (bmi<18.5) {
		bmi_note = __('Underweight');
	} else if (bmi>=18.5 && bmi<25) {
		bmi_note = __('Normal');
	} else if (bmi>=25 && bmi<30) {
		bmi_note = __('Overweight');
	} else if (bmi>=30) {
		bmi_note = __('Obese');
	}
	frappe.model.set_value(frm.doctype,frm.docname, 'bmi', bmi);
	frappe.model.set_value(frm.doctype,frm.docname, 'nutrition_note', bmi_note);
};