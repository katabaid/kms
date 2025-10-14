// Copyright (c) 2025, GIS and contributors
// For license information, please see license.txt

frappe.query_reports["MCU Recapitulation"] = {
	"filters": [
		{
			fieldname: "customer",
			fieldtype: "Link",
			label: __("Customer"),
			options: "Customer",
			get_query: () => {
				return {
					filters: {
						customer_group: 'Commercial'
					}
				};
			}
		},
		{
			fieldname: "from_date",
			fieldtype: "Date",
			label: __("From Date"),
		},
		{
			fieldname: "to_date",
			fieldtype: "Date",
			label: __("To Date"),
		},
	]
};
