// Copyright (c) 2024, GIS and contributors
// For license information, please see license.txt

frappe.ui.form.on("Questionnaire", {
	refresh(frm) {
	},
  onload: (frm) => {
    frappe.breadcrumbs.add('Healthcare', 'Questionnaire');
  }
});
