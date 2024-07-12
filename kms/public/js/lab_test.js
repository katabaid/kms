frappe.ui.form.on('Lab Test', {
	template: function(frm) {
		if (frm.doc.template) {
			frappe.call({
				method: "healthcare.healthcare.utils.get_medical_codes",
				args: {
					template_dt: "Lab Test Template",
					template_dn: frm.doc.template,
				},
				callback: function(r) {
					if (!r.exc && r.message) {
						frm.doc.codification_table = [];
						$.each(r.message, function(k, val) {
							if (val.medical_code) {
								let child = cur_frm.add_child("codification_table");
								child.medical_code = val.medical_code;
								child.medical_code_standard = val.medical_code_standard;
								child.code = val.code;
								child.description = val.description;
								child.system = val.system;
							}
						});
						frm.refresh_field("codification_table");
						frappe.db.get_doc('Lab Test Template', frm.doc.template).then(doc=>{
              //Get Worksheet & Result Legend Print 
              frm.doc.worksheet_instructions = doc.worksheet_instructions;
              frm.doc.result_legend = doc.result_legend;
              frm.doc.legend_print_position = doc.legend_print_position;
              frm.refresh_field("worksheet_instructions");
              frm.refresh_field("result_legend");
              frm.refresh_field("legend_print_position");
              //Get Stock Consumption
              //Create and Submit Stock Entry
						});
					} else {
						frm.clear_table("codification_table");
						frm.refresh_field("codification_table");
					}
				}
			});
		} else {
			frm.clear_table("codification_table");
			frm.refresh_field("codification_table");
		}
	},
	setup(frm){
    frm.set_query('service_unit', () => {
      return{
        filters: {
          is_group: 0,
          company: frm.doc.company
        }
      };
    });
    if(frm.doc.custom_selective_test_result&&frm.doc.docstatus===0){
      frm.refresh_field('custom_selective_test_result');
      $.each(frm.doc.custom_selective_test_result, (key, value) => {
        frm.fields_dict.custom_selective_test_result.grid.grid_rows[key].docfields[1].options=frm.fields_dict.custom_selective_test_result.get_value()[key].result_set;
      });
      frm.refresh_field('custom_selective_test_result');
    }
	}
});