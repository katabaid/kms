// Copyright (c) 2024, GIS and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Result per Appointment"] = {
	"filters": [
		{
			fieldname: 'exam_id',
			fieldtype: 'Link',
			label: __('Exam ID'),
			options: 'Patient Appointment'
		}
	],
	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === 'result_value' && data.min_value && data.max_value && (data.result_value < data.min_value || data.result_value > data.max_value)) {
			value = `<b style="color:brown">${value}</b>`
		}
		return value;
	}
};
