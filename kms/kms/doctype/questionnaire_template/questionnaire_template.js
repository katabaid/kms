// Copyright (c) 2024, GIS and contributors
// For license information, please see license.txt

frappe.ui.form.on('Questionnaire Template', {
  onload: function (frm) {
    frappe.breadcrumbs.add('Healthcare', 'Questionnaire Template');
    frm.fields_dict['detail'].grid.get_field('section').get_query = function (doc, cdt, cdn) {
      let child = locals[cdt][cdn];
      return {
        filters: {
          parent: frm.doc.name
        }
      }
    }
  },
});
