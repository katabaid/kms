// Copyright (c) 2024, GIS and contributors
// For license information, please see license.txt

frappe.ui.form.on('Doctor Result', {
  onload: function (frm) {
    frappe.breadcrumbs.add('Healthcare', 'Doctor Result');
  },
  setup: function (frm) {
    const child_tables = ['nurse_grade', 'doctor_grade', 'radiology_grade', 'lab_test_grade'];
    if(frm.doc.docstatus===0) {
      child_tables.forEach(child_table_name => {
        set_grade_query_for_child_table(frm, child_table_name);
        if (frm.doc[child_table_name]) {
          frm.refresh_field(child_table_name);
          //$.each(frm.doc[child_table_name], (key, value) => {
          frm.doc[child_table_name].forEach(value => {
            frappe.meta.get_docfield('MCU Exam Grade', 'grade', value.name).read_only = (value.gradable === 1) ? 0 : 1;
          });
        }
      });
    }
    hide_standard_buttons (frm, child_tables);
  },
});

function set_grade_query_for_child_table(frm, child_table_name) {
  frm.fields_dict[child_table_name].grid.get_field('grade').get_query = function (doc, cdt, cdn) {
    let row = locals[cdt][cdn];
    if(row.item_group && !row.item && row.gradable) {
      return {
        filters: [
          ['item_group', '=', row.item_group],
          ['item_code', '=', '']
        ]
      }
    } else if (row.hidden_item_group && row.item && row.gradable) {
      return {
        filters: [
          ['item_group', '=', row.hidden_item_group],
          ['item_code', '=', row.item]
        ]
      }
    } else if (row.hidden_item_group && row.hidden_item && row.examination) {
      return {
        filters: [
          ['item_group', '=', row.hidden_item_group],
          ['item_code', '=', row.hidden_item],
          ['test_name', '=', row.examination],
        ]
      }
    }
  }
}

const hide_standard_buttons = (frm, fields) => {
	fields.forEach((field) => {
		let child = frm.fields_dict[field];
		if (child) {
			if (child.grid.grid_rows) {
        setTimeout(()=>{
          const elementsToHide = child.grid.wrapper[0].querySelectorAll('.grid-add-row, .grid-remove-rows, .row-index');
          elementsToHide.forEach(element => {
            element.style.display = 'none';
          });
        }, 100)
				child.grid.grid_rows.forEach(function(row) {
					row.wrapper.find('.btn-open-row').on('click', function() {
						setTimeout(function() {
							const gridRowOpen = document.querySelector('.grid-row-open');
              const elementsToHide = gridRowOpen.querySelectorAll('.grid-delete-row, .grid-insert-row-below, .grid-duplicate-row, .grid-insert-row, .grid-move-row, .grid-append-row');
              elementsToHide.forEach(element => {
                  element.style.display = 'none';
              });
						}, 100);
					});
				});
			}
		}
	});
}