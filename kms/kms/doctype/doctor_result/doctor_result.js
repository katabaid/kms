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
          frm.doc[child_table_name].forEach(value => {
            frappe.meta.get_docfield('MCU Exam Grade', 'grade', value.name).read_only = (value.gradable === 1) ? 0 : 1;
          });
        }
      });
    }
    hide_standard_buttons (frm, child_tables);
  },
  refresh: function (frm) {
    if (frm.doc.nurse_grade) {
			frm.refresh_field('nurse_grade');
			frm.fields_dict['nurse_grade'].grid.grid_rows.forEach((row) =>{
				apply_cell_styling (frm, row.doc, row.doc.parentfield);
				frm.fields_dict.nurse_grade.grid.wrapper.find('.grid-row .row-index').hide();
			})
		}
    if (frm.doc.doctor_grade) {
			frm.refresh_field('doctor_grade');
			frm.fields_dict['doctor_grade'].grid.grid_rows.forEach((row) =>{
				apply_cell_styling (frm, row.doc, row.doc.parentfield);
				frm.fields_dict.doctor_grade.grid.wrapper.find('.grid-row .row-index').hide();
			})
		}
    if (frm.doc.lab_test_grade) {
			frm.refresh_field('lab_test_grade');
			frm.fields_dict['lab_test_grade'].grid.grid_rows.forEach((row) =>{
				apply_cell_styling (frm, row.doc, row.doc.parentfield);
				frm.fields_dict.lab_test_grade.grid.wrapper.find('.grid-row .row-index').hide();
			})
		}
    if (frm.doc.docstatus === 0) {
      frm.add_custom_button('Copy Comment', ()=>{
        if (frm.doc.remark) {
          frappe.warn(
            'There are already entries', 
            'Do you want to overwrite?', 
            () => {
              frm.set_value('remark', frm.doc.copied_remark)
           },
            'Continue',
            true
          )
        } else {
          frm.set_value('remark', frm.doc.copied_remark)
        }
      })
    }
  },
  before_save: function (frm) {
    const child_tables = ['nurse_grade', 'doctor_grade', 'radiology_grade', 'lab_test_grade'];
    create_total_comment(frm, child_tables)
  }
});

function set_grade_query_for_child_table(frm, child_table_name) {
  frm.fields_dict[child_table_name].grid.get_field('grade').get_query = function (doc, cdt, cdn) {
    let row = locals[cdt][cdn];
    if(row.hidden_item_group && !row.hidden_item && !row.is_item && row.gradable) {
      return {
        filters: [
          ['item_group', '=', row.hidden_item_group],
          ['item_code', '=', '']
        ]
      }
    } else if (row.hidden_item_group && row.hidden_item && row.is_item && row.gradable) {
      return {
        filters: [
          ['item_group', '=', row.hidden_item_group],
          ['item_code', '=', row.hidden_item],
          ['test_name', '=', ''],
        ]
      }
    } else if (row.hidden_item_group && row.hidden_item && !row.is_item && row.gradable) {
      if (!row.incdec) {
        return {
          filters: [
            ['item_group', '=', row.hidden_item_group],
            ['item_code', '=', row.hidden_item],
            ['test_name', '=', row.examination],
            ['increase_decrease', '=', '']
          ]
        }  
      } else {
        return {
          filters: [
            ['item_group', '=', row.hidden_item_group],
            ['item_code', '=', row.hidden_item],
            ['test_name', '=', row.examination],
            ['increase_decrease', '=', row.incdec]
          ]
        }
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
        }, 200)
				child.grid.grid_rows.forEach(function(row) {
					row.wrapper.find('.btn-open-row').on('click', function() {
						setTimeout(function() {
							const gridRowOpen = document.querySelector('.grid-row-open');
              const elementsToHide = gridRowOpen.querySelectorAll('.grid-delete-row, .grid-insert-row-below, .grid-duplicate-row, .grid-insert-row, .grid-move-row, .grid-append-row');
              elementsToHide.forEach(element => {
                  element.style.display = 'none';
              });
						}, 200);
					});
				});
			}
		}
	});
}

const apply_cell_styling = (frm, row, table_name) => {
  let $row = $(frm.fields_dict[table_name].grid.grid_rows_by_docname[row.name].row);
  if (row.result && row.min_value && row.max_value && (row.min_value>0 && row.max_value>0)) {
    let resultValue = parseFloat(row.result);
    let minValue = parseFloat(row.min_value);
    let maxValue = parseFloat(row.max_value);
    if (resultValue < minValue || resultValue > maxValue) {
			$row.css({
				'font-weight': 'bold',
        'color': 'red'
      });
    } else {
      $row.css({
        'font-weight': 'normal',
        'color': 'black'
      });
    }
  }
  if (row.gradable) {
    $row.css({
      'background-color': '#f1f5f9'
    })
  }
}

const create_total_comment = (frm, fields) => {
  let copied_remark = '';
  fields.forEach((field) => {
    frm.doc[field].forEach((row) => {
      if (row.grade && row.grade.split('-').pop() != 'A') {
        console.log(row.grade)
        if (copied_remark) copied_remark += '\n';
        copied_remark += row.description;
      }
    })
  })
  frm.set_value('copied_remark', copied_remark)
}