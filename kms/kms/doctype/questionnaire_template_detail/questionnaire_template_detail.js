frappe.ui.form.on('Questionnaire Template Detail', {
  refresh: function(frm) {
    frm.fields_dict['section'].get_query = function (doc) {
      return { filters: {parent: frm.doc.parent}}
    }
  }
});