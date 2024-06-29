frappe.pages['kms'].on_page_load = function(wrapper) {
	let page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Home',
		single_column: true
	});
	let sideNavbarContents = $('.layout-side-section').html();
	$(page.body).append(sideNavbarContents);
}