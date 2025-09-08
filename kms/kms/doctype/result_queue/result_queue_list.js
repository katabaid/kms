frappe.listview_settings['Radiology Result'] = {
	has_indicator_for_draft: true,
	hide_name_column: true,
	hide_name_filter: true,
	disable_assignment: true,
	onload: (listview) => {
		frappe.breadcrumbs.add('Healthcare', 'Result Queue');
	},
}