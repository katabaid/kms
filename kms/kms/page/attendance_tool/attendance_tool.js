frappe.pages['attendance-tool'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Attendance Tool',
		single_column: true
	});
}