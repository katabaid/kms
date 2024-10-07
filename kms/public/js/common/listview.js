frappe.provide('frappe.views');

(function () {
	// Store the original ListView class
	var OriginalListView = frappe.views.ListView;

	// Create a new ListView class that extends the original
	frappe.views.ListView = class CustomListView extends OriginalListView {
		constructor(opts) {
			super(opts);
			this.remove_love_button();
		}

		remove_love_button() {
			// Override the setup_like method to do nothing
			this.setup_like = function () {};
		}
	};

	// Ensure the new class has all the properties of the original
	Object.assign(frappe.views.ListView, OriginalListView);
})();
