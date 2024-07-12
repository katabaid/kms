// Copyright (c) 2024, GIS and contributors
// For license information, please see license.txt

frappe.ui.form.on('KPI', {
	kpi_template: function(frm) {
		frappe.db.get_doc('KPI Template', frm.doc.kpi_template).then(doc=>{
		    frm.doc.kpi_details_tab =[];
		    $.each(doc.kpi_template, (_i,e)=>{
		        let row = frm.add_child('kpi_details_tab');
		        row.key_result_area = e.key_result_area;
		        row.kpi = e.kpi;
		        row.weightage = e.weightage;
		        row.target = e.target;
		        row.unit_of_kpi = e.unit_of_kpi;
		        row.higher_is_better = e.higher_is_better;
		    });
		    frm.refresh_field("kpi_details_tab");
		});
	}
});

frappe.ui.form.on('KPI Details',  'actual', (frm, cdt, cdn) => {
	let d = locals[cdt][cdn];
	d.score_ = d.lower_is_better? d.target/d.actual*100 : d.actual/d.target*100;
	d.final_score = d.lower_is_better? d.target/d.actual*d.weightage : d.actual/d.target*d.weightage;
	frm.refresh_field("kpi_details_tab");
});