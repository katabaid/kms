// Copyright (c) 2024, GIS and contributors
// For license information, please see license.txt

frappe.query_reports["List MCU"] = {
	"filters": [
		{
			fieldname: 'exam_date',
			fieldtype: 'Date',
			label: __('Exam Date'),
			default: frappe.datetime.nowdate()
		},
		{
			fieldname: 'branch',
			fieldtype: 'Link',
			label: __('Branch'),
			options: 'Branch',
			on_change: function() {
				let branch = frappe.query_report.get_filter_value('branch');
				frappe.call({
						method: 'frappe.client.get_list',
						args: {
								doctype: 'Healthcare Service Unit',
								filters: { custom_branch: branch },
								fields: ['name']
						},
						callback: function(response) {
								let room_filter = frappe.query_report.get_filter('room');
								if (response.message) {
										let room_options = response.message.map(room => room.name);
										room_filter.df.options = [''].concat(room_options).join('\n');
										room_filter.refresh();
								} else {
										room_filter.df.options = '';
								}
								room_filter.refresh();
						}
				});
			}
		},
		{
			fieldname: 'department',
			fieldtype: 'Select',
			label: __('Department'),
			options: '\nNurse Examination\nDoctor Examination\nRadiology\nLaboratorium'
		},
		{
			fieldname: 'room',
			fieldtype: 'Select',
			label: __('Room'),
			// options: 'Healthcare Service Unit'
		}
	]
};
