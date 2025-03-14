frappe.ui.form.on('Clinical Procedure', {
	procedure_template: function(frm) {
		if (frm.doc.procedure_template) {
			frappe.call({
				'method': 'frappe.client.get',
				args: {
					doctype: 'Clinical Procedure Template',
					name: frm.doc.procedure_template
				},
				callback: function (data) {
					frm.set_value('consume_stock', data.message.consume_stock);
					frm.events.set_warehouse(frm);
					frm.events.set_procedure_consumables(frm);
          frappe.call({
            "method": "healthcare.healthcare.utils.get_medical_codes",
            args: {
              template_dt: "Clinical Procedure Template",
              template_dn: frm.doc.procedure_template,
            },
            callback: function(r) {
              if (!r.exc && r.message) {
                frm.doc.codification_table = []
                $.each(r.message, function(k, val) {
                  if (val.medical_code) {
                    var child = cur_frm.add_child("codification_table");
                    child.medical_code = val.medical_code
                    child.medical_code_standard = val.medical_code_standard
                    child.code = val.code
                    child.description = val.description
                    child.system = val.system
                  }
                });
                frm.refresh_field("codification_table");
              } else {
                frm.clear_table("codification_table")
                frm.refresh_field("codification_table");
              }
            }
          })
				}
			});
		} else {
			frm.clear_table("codification_table")
			frm.refresh_field("codification_table");
		}
	},
  /* appointment: function(frm) {
    if(frm.doc.appointment) {
      frappe.db.get_doc('Patient Appointment', frm.doc.appointment).then(function(patient_appointment) {
        let tindakan_list = patient_appointment.custom_procedures || [];
        let tindakan_values = tindakan_list.map(item => item.procedure);
        frm.fields_dict['procedure_template'].get_query = function() {
          return {
              filters: {
                  'name': ['in', tindakan_values]
              }
          };
        };
        frm.refresh_field('procedure_template');
      })
    }
  }, */
})