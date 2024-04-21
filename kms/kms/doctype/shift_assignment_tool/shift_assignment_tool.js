// Copyright (c) 2024, GIS and contributors
// For license information, please see license.txt

frappe.ui.form.on('Shift Assignment Tool', {
	refresh(frm) {
		if(!frm.doc.week_number){
			frm.trigger('reset_week_number');
		}
		frm.trigger('load_employee');
		frm.trigger('set_primary_button');
	},
	week_number(frm){
		frm.set_value('from_date', '');
		frm.set_value('to_date', '');
		frappe.call({
				method: 'kms.kms.doctype.week_number.week_number.get_week_number_info',
				args: {
						week_number: frm.doc.week_number
				},
				callback: (r) => {
						frm.doc.from_date=r.message[0].start_date_of_week;
						frm.doc.to_date=r.message[0].end_date_of_week;
						frm.refresh_field('from_date');
						frm.refresh_field('to_date');
						frm.trigger('load_employee');
				}
		});
	},
	company(frm){
		frm.trigger('load_employee');
	},
	branch(frm){
		frm.trigger('load_employee');
	},
	department(frm){
		frm.trigger('load_employee');
	},
	
	reset_week_number(frm){
		frappe.call({
			method: 'kms.kms.doctype.week_number.week_number.get_current_week_number',
			callback: (r) => {
					frm.doc.week_number=r.message[0].current_week_number;
					frm.doc.from_date=r.message[0].start_date_of_week;
					frm.doc.to_date=r.message[0].end_date_of_week;
					frm.refresh_field('week_number');
					frm.refresh_field('from_date');
					frm.refresh_field('to_date');
					frm.trigger('load_employee');
			}
		});
	},
	load_employee(frm){
		if((!frm.doc.week_number||!frm.doc.from_date||!frm.doc.to_date||!frm.doc.company)&&(!frm.doc.branch||!frm.doc.department)){
			return;
		}
		frappe.call({
			method: 'kms.kms.doctype.shift_assignment_tool.shift_assignment_tool.get_employees',
			args: {
				week_number: frm.doc.week_number,
				from_date: frm.doc.from_date,
				to_date: frm.doc.to_date,
				company: frm.doc.company,
				branch: frm.doc.branch,
				department: frm.doc.department
			},
			callback: (r) => {
				frm.employees=r.message['unmarked'];
				if (r.message['marked'].length > 0) {
					unhide_field('assigned_employees_section');
					frm.events.show_marked_employees(frm, r.message['marked']);
				} else {
					hide_field('assigned_employees_section');
				}
				if (r.message['unmarked'].length > 0) {
					unhide_field('select_employees_section');
					frm.events.show_unmarked_employees(frm, r.message['unmarked']);
				} else {
					hide_field('select_employees_section');
				}
			}
		})
	},
	set_primary_button(frm){
		frm.disable_save();
		frm.page.set_primary_action(__('Assign Shifts'), () => {
			if (frm.employees.length === 0) {
				frappe.msgprint({
					message: __("Attendance for all the employees under this criteria has been marked already."),
					title: __("Attendance Marked"),
					indicator: "green"
				});
				return;
			}
			if (frm.employees_multicheck.get_checked_options().length === 0) {
				frappe.throw({
					message: __("Please select the employees you want to mark attendance for."),
					title: __("Mandatory")
				});
			}
			if (!frm.doc.shift) {
				frappe.throw({
					message: __("Please select the which shift to assign."),
					title: __("Mandatory")
				});
			}
			frm.trigger('assign_shift');
		});
	},

	assign_shift(frm){
		const marked_employees = frm.employees_multicheck.get_checked_options();

		frappe.call({
			method: "kms.kms.doctype.shift_assignment_tool.shift_assignment_tool.assign_employee_shift",
			args: {
				employee_list: marked_employees,
				from_date: frm.doc.from_date,
				to_date: frm.doc.to_date,
				shift: frm.doc.shift
			},
			freeze: true,
			freeze_message: __("Assigning Shift")
		}).then((r) => {
			if (!r.exc) {
				frappe.show_alert({ message: __("Shift assigned successfully"), indicator: "green" });
				frm.refresh();
			}
		});
	},
	show_marked_employees(frm, marked_employees){
		const $wrapper = frm.get_field("employee_shift_html").$wrapper;
		const summary_wrapper = $(`<div class="summary_wrapper">`).appendTo($wrapper);

		const data = marked_employees.map((entry) => {
			let tanggal = new Date(Date.parse(entry.date));
			return [`${entry.name} : ${entry.employee_name}`, tanggal.toLocaleString('id-ID', {weekday: "long", year: "numeric", month: "long", day: "numeric"}), entry.shift_type];
		});

		frm.events.render_datatable(frm, data, summary_wrapper);
	},
	show_unmarked_employees(frm, unmarked_employees){
		const $wrapper = frm.get_field("employees_html").$wrapper;
		$wrapper.empty();
		const employee_wrapper = $(`<div class="employee_wrapper">`).appendTo($wrapper);

		frm.employees_multicheck = frappe.ui.form.make_control({
			parent: employee_wrapper,
			df: {
				fieldname: "employees_multicheck",
				fieldtype: "MultiCheck",
				select_all: true,
				columns: 4,
				get_data: () => {
					return unmarked_employees.map((employee) => {
						return {
							label: `${employee.name} : ${employee.employee_name}`,
							value: employee.name,
							checked: 0,
						};
					});
				},
			},
			render_input: true,
		});

		frm.employees_multicheck.refresh_input();
	},
	render_datatable(frm, data, summary_wrapper) {
		const columns = frm.events.get_columns_for_marked_attendance_table(frm);

		if (!frm.marked_emp_datatable) {
			const datatable_options = {
				columns: columns,
				data: data,
				dynamicRowHeight: true,
				inlineFilters: true,
				layout: "fixed",
				cellHeight: 35,
				noDataMessage: __("No Data"),
				disableReorderColumn: true,
			};
			frm.marked_emp_datatable = new frappe.DataTable(
				summary_wrapper.get(0),
				datatable_options,
			);
		} else {
			frm.marked_emp_datatable.refresh(data, columns);
		}
	},

	get_columns_for_marked_attendance_table(frm) {
		return [
			{
				name: "employee",
				id: "employee",
				content: `${__("Employee")}`,
				editable: false,
				sortable: false,
				focusable: false,
				dropdown: false,
				align: "left",
				width: 350,
			},
			{
				name: "date",
				id: "date",
				content: `${__("Date")}`,
				editable: false,
				sortable: false,
				focusable: false,
				dropdown: false,
				align: "left",
				width: 150,
			},
			{
				name: "shift_type",
				id: "shift_type",
				content: `${__("Shift Type")}`,
				editable: false,
				sortable: false,
				focusable: false,
				dropdown: false,
				align: "left",
				width: 350,
			},
		]
	},
});