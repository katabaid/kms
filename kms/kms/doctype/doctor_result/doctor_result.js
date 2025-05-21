// Copyright (c) 2024, GIS and contributors
// For license information, please see license.txt

// Constants
const CHILD_TABLES = ['nurse_grade', 'doctor_grade', 'radiology_grade', 'lab_test_grade'];

// Main form controller
frappe.ui.form.on('Doctor Result', {
  onload: function(frm) {
    frappe.breadcrumbs.add('Healthcare', 'Doctor Result');
  },

  refresh: function(frm) {
    CHILD_TABLES.forEach(table => {
      utilities.processChildTable(frm, table);
    });
    hide_standard_buttons(frm, CHILD_TABLES);
  },
});

// Utility functions
const utilities = {
  processChildTable: (frm, tableName) => {
    if (!frm.doc[tableName]) return;
    const grid = frm.fields_dict[tableName].grid;

    grid.wrapper.on('grid-refresh', () => {
      if (frm.doc.docstatus !== 0) return;
      
      grid.grid_rows.forEach(grid_row => {
        const row = grid_row.doc;
        utilities.handleGradeField(frm, row, grid_row);
        apply_cell_styling(frm, row, tableName);
      });
      
      grid.wrapper.find('.grid-row .row-index').hide();
      grid.wrapper.on('click', '.grid-pagination .btn', function() {
        setTimeout(() =>{
          grid.grid_rows.forEach((grid_row)=>{
            const row = grid_row.doc;
            utilities.handleGradeField(frm, row, grid_row);
            apply_cell_styling(frm, row, tableName);    
          });
          grid.wrapper.find('.grid-row .row-index').hide();
        }, 150)
      })
    });

    grid.wrapper.trigger('grid-refresh');
  },

  handleGradeField: (frm, row, grid_row) => {
    const docfield = frappe.meta.get_docfield('MCU Exam Grade', 'grade', row.name);
    
    if (row.gradable === 1) {
      docfield.read_only = 0;
      docfield.get_query = () => ({ filters: utilities.getGradeFilters(row) });
    } else {
      docfield.read_only = 1;
      docfield.get_query = undefined;
    }
    
    grid_row.refresh_field('grade');
  },

  getGradeFilters: (row) => {
    const filters = [
      ['item_group', '=', row.hidden_item_group],
      ['item_code', '=', row.hidden_item || ''],
      ['increase_decrease', '=', row.incdec || '']
    ];

    if (row.is_item) {
      filters.push(['test_name', '=', '']);
    } else if (row.hidden_item) {
      filters.push(['test_name', '=', row.examination]);
    }

    return filters;
  }
};

// Keep other helper functions (hide_standard_buttons, apply_cell_styling, create_total_comment) unchanged

const hide_standard_buttons = (frm, fields) => {
	fields.forEach((field) => {
		let child = frm.fields_dict[field];
		if (child) {
			if (child.grid.grid_rows) {
				setTimeout(() => {
          $(child.grid.wrapper).find('.grid-add-row, .grid-remove-rows, .row-index').hide();
				}, 300);
				child.grid.grid_rows.forEach(function (row) {
					row.wrapper.find('.btn-open-row').on('click', function () {
						setTimeout(function () {
							const gridRowOpen = document.querySelector('.grid-row-open');
							const elementsToHide = gridRowOpen.querySelectorAll(
								'.grid-delete-row, .grid-insert-row-below, .grid-duplicate-row, .grid-insert-row, .grid-move-row, .grid-append-row',
							);
							elementsToHide.forEach((element) => {
								element.style.display = 'none';
							});
						}, 300);
					});
				});
			}
		}
	});
};

const apply_cell_styling = (frm, row, table_name) => {
  let $row = $(frm.fields_dict[table_name].grid.grid_rows_by_docname[row.name]?.row);
  if(!$row) return;
  if (row.result && (row.min_value || row.max_value) && (row.min_value>0 || row.max_value>0)) {
    let resultValue = parseFloat(row.result);
    let minValue = parseFloat(row.min_value);
    let maxValue = parseFloat(row.max_value);
    if (resultValue < minValue || resultValue > maxValue) {
			$row.css({
				'font-weight': 'Bold',
        'color': 'Maroon'
      });
    } else {
      $row.css({
        'font-weight': 'Normal',
        'color': 'Dimgray'
      });
    }
  }
  if (row.gradable) {
    if (row.hidden_item_group && !row.hidden_item) {
      $row.css({
        'background-color': '#ffac23'
      })  
    } else {
      $row.css({
        'background-color': '#f1f5f9'
      })
    }
  }
  if (row.hidden_item_group && !row.hidden_item) {
    $row.css({
      'font-weight': 'Bold',
      'color': 'midnightblue',
      'background-color': '#ffac23'
    });
  }
  if (row.hidden_item_group && row.hidden_item && row.is_item) {
    $row.css({
      'font-weight': 'normal',
      'color': 'midnightblue'
    });
  }
}
