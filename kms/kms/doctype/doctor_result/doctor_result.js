// Copyright (c) 2024, GIS and contributors
// For license information, please see license.txt

const CHILD_TABLES = ['nurse_grade', 'doctor_grade', 'radiology_grade', 'lab_test_grade'];

frappe.ui.form.on('Doctor Result', {
  onload: function (frm) {
    frappe.breadcrumbs.add('Healthcare', 'Doctor Result');
  },
  refresh: function (frm) {
    if (frm.fields_dict.questionnaire_html && kms.utils && kms.utils.fetch_questionnaire_for_doctype)
      kms.utils.fetch_questionnaire_for_doctype(frm, "appointment", null, "questionnaire_html");
    CHILD_TABLES.forEach(table => {
      utilities.processChildTable(frm, table);
    });
    hide_standard_buttons(frm, CHILD_TABLES);
    add_custom_buttons(frm);
    hide_save_button(frm);
  }
});

// Utility functions
const utilities = {
  processChildTable: (frm, tableName) => {
  if (!frm.doc[tableName] || !frm.fields_dict[tableName] || !frm.fields_dict[tableName].grid) {
  	return;
  }
  const grid = frm.fields_dict[tableName].grid;

  const runGridCustomizations = () => {
  	setTimeout(() => {
  		if (!grid.wrapper) {
  			return;
  		}

  		$(grid.wrapper).find('.row-index').css('display', 'none', 'important');
  		$(grid.wrapper).find(
  			`div.grid-heading-cell[data-col-idx="1"], div.grid-row-cell[data-col-idx="1"], ` +
  			`th[data-col-idx="1"], td[data-col-idx="1"], ` +
  			`.dt-cell-header[data-col-idx="1"], .dt-cell[data-col-idx="1"]`
  		).css('display', 'none', 'important');
  		$(grid.wrapper).find(
  			`div.grid-heading-cell[data-fieldname="idx"], div.grid-row-cell[data-fieldname="idx"], ` +
  			`th[data-fieldname="idx"], td[data-fieldname="idx"], ` +
  			`.dt-cell-header[data-fieldname="idx"], .dt-cell[data-fieldname="idx"]`
  		).css('display', 'none', 'important');
  		const specificFilterInputRowSelector = "div.grid-heading-row.with-filter > div.grid-row:has(div.filter-row)";
  		const $specificFilterInputRow = $(grid.wrapper).find(specificFilterInputRowSelector);
  		if ($specificFilterInputRow.length > 0) {
  			$specificFilterInputRow.css('display', 'none', 'important');
  		} else {
  		}
  		const headingRowWithFilterSelector = "div.grid-heading-row.with-filter";
  		const $headingRowWithFilter = $(grid.wrapper).find(headingRowWithFilterSelector);
  		if ($headingRowWithFilter.length > 0) {
  			$headingRowWithFilter.removeClass('with-filter');
  			$headingRowWithFilter.children('div.grid-row:has(div.filter-row)').css('display', 'none', 'important');
  		} else {
  		}
  	}, 150);

  	if (grid.grid_rows) {
  		grid.grid_rows.forEach(grid_row => {
  			if (!grid_row.doc) return;
  			const row = grid_row.doc;
  			if (frm.doc.docstatus === 0) {
  				utilities.handleGradeField(frm, row, grid_row);
  			}
  			apply_cell_styling(frm, row, tableName);
  		});
  	}
  };

  grid.wrapper.off('grid-refresh.doctorResultCustom')
    .on('grid-refresh.doctorResultCustom', () => {
  	runGridCustomizations();
  });

  grid.wrapper.off('click.doctorResultPagination', '.grid-pagination .btn')
    .on('click.doctorResultPagination', '.grid-pagination .btn', function() {
  	setTimeout(() => {
  		runGridCustomizations();
  	}, 250);
  });

  if (grid.wrapper && typeof grid.wrapper.trigger === 'function') {
  	setTimeout(() => {
  		if (grid.wrapper) {
  			grid.wrapper.trigger('grid-refresh');
  		}
  	}, 100);
  } else {
  	setTimeout(runGridCustomizations, 350);
  }
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

const hide_standard_buttons = (frm, fields) => {
	fields.forEach((field) => {
		if (frm.fields_dict[field]) { // Ensure field exists in form's dictionary
			frm.set_df_property(field, 'cannot_add_rows', true);
			frm.set_df_property(field, 'cannot_delete_rows', true);
			frm.set_df_property(field, 'cannot_delete_all_rows', true);
		} else {
		}
	});
};

const apply_cell_styling = (frm, row, table_name) => {
  let $row = $(frm.fields_dict[table_name].grid.grid_rows_by_docname[row.name]?.row);
  if (!$row) return;
  if (row.result && (row.min_value || row.max_value) && (row.min_value > 0 || row.max_value > 0)) {
    let resultValue = parseFloat(row.result);
    let minValue = parseFloat(row.min_value);
    let maxValue = parseFloat(row.max_value);
    if (resultValue < minValue || resultValue > maxValue) {
      $row.css({'font-weight': 'Bold', 'color': 'Maroon'});
    } else {
      $row.css({'font-weight': 'Normal', 'color': 'Dimgray'});
    }
  }
  if (row.gradable) {
    if (row.hidden_item_group && !row.hidden_item) {
      $row.css({'background-color': '#ffac23'})
    } else {
      $row.css({'background-color': '#f1f5f9'})
    }
  }
  if (row.hidden_item_group && !row.hidden_item) {
    $row.css({'font-weight': 'Bold', 'color': 'midnightblue', 'background-color': '#ffac23'});
  }
  if (row.hidden_item_group && row.hidden_item && row.is_item) {
    $row.css({'font-weight': 'normal', 'color': 'midnightblue'});
  }
}

const add_custom_buttons = (frm) => {
  frm.add_custom_button('Questionnaire', () => {
    window.open(`/app/questionnaire?exam_id=${frm.doc.appointment}`, '_blank');
  })
  if (frm.doc.docstatus === 0) {
    if (frm.doc.healthcare_practitioner) {
      frm.add_custom_button('Check Out', () => {
        frm.set_value('healthcare_practitioner', '');
        frm.save();
      })
    } else {
      frm.add_custom_button('Check In', () => {
        frappe.db.get_value('Healthcare Practitioner', { user_id: frappe.session.user }, 'name')
          .then(r => {
            frm.set_value('healthcare_practitioner', r.message.name);
            frm.save();
          })
      })
    };
  }
}

const hide_save_button = (frm) => {
  if (frm.doc.docstatus === 0) {
    if (frm.doc.healthcare_practitioner_user) {
      if (frm.doc.healthcare_practitioner_user === frappe.session.user) {
        frm.enable_save();
      } else {
        frm.disable_save();
      }
    } else { frm.enable_save(); }
  } else { frm.enable_save(); }
}