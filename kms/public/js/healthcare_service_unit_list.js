frappe.listview_settings['Healthcare Service Unit'] = {
	hide_name_column: true,
	add_fields: ["name", "is_group", "custom_branch", "service_unit_type", "custom_default_doctype"],

	/* onload: function (me) {
		if (!frappe.route_options) {
			frappe.route_options = {
				owner: frappe.session.user,
				status: "Open",
			};
		}
		me.page.set_title(__("To Do"));
	}, */

	button: {
		show: function (doc) {
			return !doc.is_group&&doc.custom_default_doctype;
		},
		get_label: function () {
			return __('<i class="fa-solid fa-user-doctor"></i>Room Queue', null, "Access");
		},
		get_description: function (doc) {
			return __("Open room queue for {0}", [`${__(doc.custom_default_doctype)}: ${doc.name}`]);
		},
		action: function (doc) {
			const today = new Date().toISOString().split('T')[0];
			if (doc.custom_default_doctype === 'Sample Collection')
				frappe.set_route("List", doc.custom_default_doctype, {custom_service_unit: doc.name, custom_document_date: today});
			else
				frappe.set_route("List", doc.custom_default_doctype, {service_unit: doc.name, created_date: today});
		},
	},

	refresh: function (litview) {
		$("button.btn.btn-action.btn-default.btn-xs").addClass("btn-info").removeClass("btn-default");
	}
	/* refresh: function (me) {
		if (me.todo_sidebar_setup) return;

		// add assigned by me
		me.page.add_sidebar_item(
			__("Assigned By Me"),
			function () {
				me.filter_area.add([[me.doctype, "assigned_by", "=", frappe.session.user]]);
			},
			'.list-link[data-view="Kanban"]'
		);

		me.todo_sidebar_setup = true;
	}, */
};
