frappe.listview_settings['Nurse Result'] = {
	add_fields: ['has_attachment', 'docstatus', 'workflow_state'],
	has_indicator_for_draft: true,
	hide_name_column: true,
	hide_name_filter: true,
	disable_assignment: true,
	get_indicator: function (doc) {
		const statusMap = {
			"1-1": [doc.status.concat(' *'), "blue"],
			"0-1": [doc.status, "light-blue"],
			"0-0": [doc.status, "light-gray"],
			"1-0": [doc.status.concat(' *'), "gray"],
			"1-2": [doc.status.concat(' *'), "red"],
			"0-2": [doc.status, "orange"]
		};
		return statusMap[`${doc.has_attachment}-${doc.docstatus}`] || [doc.status, "dark-gray"];
	},
	onload: (listview) => {
		frappe.breadcrumbs.add('Healthcare', 'Nurse Result');
	},
	refresh: function (listview) {
		setTimeout(() => {
			const assignmentActions = ["Assign%20To", "Clear%20Assignment", "Apply%20Assignment%20Rule"];
			assignmentActions.forEach(action => {
				listview.page.wrapper.find(`span[data-label="${action}"]`).closest('li').remove();
			});
		}, 100);
		frappe.db.get_single_value('MCU Settings', 'external_doctor_role').then(external_doctor_role => {
			if (!frappe.user.has_role(external_doctor_role) || frappe.user.name == 'Administrator') {
				listview.page.add_action_item(__("Result Assignment"), this.handleResultAssignment.bind(this, listview));
			}
		});
	},

	handleResultAssignment: function (listview) {
		const selectedRows = listview.get_checked_items().filter(row => row.docstatus === 0);

		if (selectedRows.length === 0) {
			frappe.msgprint(__("Please select at least one row with draft status (docstatus = 0)"));
			return;
		}

		this.showAssignmentDialog(selectedRows, listview);
	},

	showAssignmentDialog: function (selectedRows, listview) {
		const selectedNames = selectedRows.map(row => row.name);
		const dialog = new frappe.ui.Dialog({
			title: __("Select Healthcare Practitioner"),
			fields: [
				{
					fieldtype: "Link",
					fieldname: "practitioner",
					label: __("Healthcare Practitioner"),
					options: "Healthcare Practitioner",
					reqd: 1
				},
				{
					fieldtype: "Date",
					fieldname: "due_date",
					label: __("Due Date"),
					reqd: 1,
					default: frappe.datetime.nowdate()
				}
			],
			primary_action_label: __("Assign"),
			primary_action: (values) => this.assignResults(values, selectedNames, listview, dialog)
		});
		dialog.show();
	},

	assignResults: function (values, selectedNames, listview, dialog) {
		if (!values.practitioner) {
			frappe.msgprint(__("Please select a Healthcare Practitioner"));
			return;
		}

		dialog.hide();

		frappe.call({
			method: "kms.kms.doctype.radiology_result.radiology_result_list.assign_results",
			args: {
				doc_type: 'Nurse Result',
				selected_rows: selectedNames,
				practitioner: values.practitioner,
				due_date: values.due_date
			},
			callback: (r) => {
				if (r.message) {
					const { unchanged_rows, changed_rows, new_docs } = r.message;
					frappe.show_alert({
						message: `
							<p>${__("Assignment completed:")}</p>
							<ul>
								<li>${__("Unchanged rows: {0}", [unchanged_rows])}</li>
								<li>${__("Changed rows: {0}", [changed_rows])}</li>
								<li>${__("New documents: {0}", [new_docs])}</li>
							</ul>
						`,
						indicator: "green"
					}, 5);
					listview.refresh();
				}
			}
		});
	}
}