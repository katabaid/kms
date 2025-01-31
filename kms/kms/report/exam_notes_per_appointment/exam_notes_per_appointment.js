// Copyright (c) 2025, GIS and contributors
// For license information, please see license.txt

frappe.query_reports["Exam Notes per Appointment"] = {
	"filters": [
    {
      fieldname: "exam_id",
      fieldtype: "Link",
      label: __("Exam ID"),
      options: "Patient Appointment",
    },
	]
};
