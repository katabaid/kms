frappe.pages['kms-home'].on_page_load = function(wrapper) {
	let page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Home',
		single_column: true
	});
	let field = page.add_field({
    label: 'Status',
    fieldtype: 'Select',
    fieldname: 'status',
    options: [
        'Open',
        'Closed',
        'Cancelled'
    ],
    change() {
        console.log(field.get_value());
    }
	 });



}