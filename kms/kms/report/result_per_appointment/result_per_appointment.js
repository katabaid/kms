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
	]
};
