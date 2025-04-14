from . import __version__ as app_version

app_name = "kms"
app_title = "KMS"
app_publisher = "GIS"
app_description = "KMS customizations"
app_email = "gis@global-infotech.co.id"
app_license = "MIT"

# Includes in <head>
# ------------------

website_context = {
  'splash_image': '/assets/kms/images/logo.png',
  'favicon': '/assets/kms/images/logo.png',
}
# include js, css files in header of desk.html
app_include_css = "/assets/kms/css/kms.css"
app_include_js = [
  "/assets/kms/js/controller/examination.js",
  "/assets/kms/js/common/listview.js",
  "/assets/kms/js/common/redirect_after_boot.js",
  "/assets/kms/js/common/clear_local_storage.js",
  "/assets/kms/node_modules/qrcodejs/qrcode.min.js",
]

# include js, css files in header of web template
# web_include_css = "/assets/kms/css/kms.css"
# web_include_js = "/assets/kms/js/kms.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "kms/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
  "Blanket Order": "public/js/blanket_order.js",
  "Clinical Procedure": "public/js/clinical_procedure.js",
  "Customer": "public/js/customer.js",
  "Lab Test": "public/js/lab_test.js",
  "Leave Application": "public/js/leave_application.js",
  "Material Request": "public/js/material_request.js",
  "Patient": "public/js/patient.js",
  "Patient Appointment": "public/js/patient_appointment.js",
  "Patient Encounter": "public/js/patient_encounter.js",
  "Patient History Settings": "public/js/patient_history_settings.js",
  "Product Bundle": "public/js/service_package.js",
  "Quotation": "public/js/quotation.js",
  "Sales Order": "public/js/sales_order.js",
  "Sales Invoice": "public/js/sales_invoice.js",
  "Sample Collection": "public/js/sample_collection.js",
  "Shift Type": "public/js/shift_type.js",
  "Vital Signs": "public/js/vital_signs.js",
}
doctype_list_js = {
  "ToDo": "public/js/todo_list.js",
  "Healthcare Service Unit" : "public/js/healthcare_service_unit_list.js",
}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
#	"methods": "kms.utils.jinja_methods",
#	"filters": "kms.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "kms.install.before_install"
# after_install = "kms.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "kms.uninstall.before_uninstall"
# after_uninstall = "kms.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "kms.utils.before_app_install"
# after_app_install = "kms.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "kms.utils.before_app_uninstall"
# after_app_uninstall = "kms.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "kms.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
#	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
#	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

override_doctype_class = {
  "Shift Request": "kms.override.shift_request.KmsShiftRequest",
  #"ToDo": "kms.override.todo.CustomToDo",
}

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
#  "*": {
#		"on_submit": "kms.event.create_medical_record",
#		"on_cancel": "kms.event.delete_medical_record",
#		"on_update_after_submit": "kms.event.update_medical_record",
#	},
  "Customer": {
    "after_insert": "kms.event.erpnext.update_customer_name",
  },
  "File": {
    "after_insert": "kms.event.erpnext.set_has_attachment",
    "on_trash": "kms.event.erpnext.set_has_attachment",
  },
  "Item": {
    "before_save": "kms.event.erpnext.item_before_save",
  },
  "Item Price": {
    "on_change": "kms.event.erpnext.update_item_price",
    "after_insert": "kms.event.erpnext.update_item_price",
    "before_save": "kms.event.erpnext.update_item_price",
  },
  "Material Request": {
    "on_submit": "kms.event.erpnext.on_submit_material_request",
  },
  "Quotation": {
    "before_save": "kms.event.erpnext.update_rate_amount_after_amend",
  },
  "Sales Invoice": {
    "on_submit": "kms.event.erpnext.sales_invoice_on_submit",
  },
  "Patient Appointment": {
    "after_insert": "kms.event.healthcare.patient_appointment_after_insert",
    "on_update": "kms.event.healthcare.patient_appointment_on_update",
  },
  "Patient Encounter": {
    "on_trash": "kms.event.healthcare.patient_encounter_on_trash",
    "after_insert": "kms.event.healthcare.patient_encounter_after_insert",
    "on_submit": "kms.event.healthcare.patient_encounter_on_submit",
    "validate": "kms.event.healthcare.patient_encounter_validate",
    "on_update": "kms.event.healthcare.patient_encounter_on_update",
    "before_save": "kms.event.healthcare.patient_encounter_before_safe",
  },
  "Prescription Duration": {
    "autoname": "kms.event.healthcare.prescription_duration_autoname",
  },
  "Vital Signs": {
    "before_submit": "kms.event.event.vital_signs_before_submit",
  },
  "Lab Test": {
    "on_submit": "kms.event.lab_sample.lab_on_submit",
    "before_submit": "kms.event.lab_sample.lab_before_submit",
    "before_save": "kms.event.lab_sample.lab_before_save",
  },
  "Sample Collection": {
    "before_insert": "kms.event.lab_sample.sample_before_insert",
    "after_submit": "kms.event.lab_sample.sample_after_submit",
    "before_submit": "kms.event.lab_sample.sample_before_submit",
  },
}

# Scheduled Tasks
# ---------------

scheduler_events = {
  "daily": [
    "kms.scheduled.set_cancelled_open_appointment",
    "kms.scheduled.set_no_show_queue_pooling",
    "kms.scheduled.set_cancelled_timeout_queue_pooling"
  ],
  "cron": {
    "*/10 * * * *": [
      "kms.scheduled.reset_dispatcher_status",
    ]
  }
}

# Testing
# -------

# before_tests = "kms.install.before_tests"

# Overriding Methods
# ------------------------------
#
override_whitelisted_methods = {
  "healthcare.healthcare.utils.get_healthcare_services_to_invoice": "kms.override.healthcare.get_healthcare_services_to_invoice",
}
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
#	"Task": "kms.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["kms.utils.before_request"]
# after_request = ["kms.utils.after_request"]

# Job Events
# ----------
# before_job = ["kms.utils.before_job"]
# after_job = ["kms.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
#	{
#		"doctype": "{doctype_1}",
#		"filter_by": "{filter_by}",
#		"redact_fields": ["{field_1}", "{field_2}"],
#		"partial": 1,
#	},
#	{
#		"doctype": "{doctype_2}",
#		"filter_by": "{filter_by}",
#		"partial": 1,
#	},
#	{
#		"doctype": "{doctype_3}",
#		"strict": False,
#	},
#	{
#		"doctype": "{doctype_4}"
#	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
#	"kms.auth.validate"
# ]
fixtures = [
  {'dt':'Role', 'filters': [["is_custom", "=", 1]]},
  {'dt':'Custom DocPerm', 'filters': [["role", "in", [["is_custom", "=", 1]]]]},
  {'dt':'User Permission'},
  {'dt':'Custom Field', 'filters': [['module', '=', 'KMS']]}, 
  {'dt':'Property Setter', 'filters': [['module', '=', 'KMS']]}, 
  {'dt':'Workspace'},
  {'dt':'Custom HTML Block'},
  {'dt':'Report', 'filters': [['module', '=', 'KMS']]},
  {'dt':'Print Format', 'filters': [["custom_format", "=", 1]]},
]
on_logout = ["kms.session.remove_room_assignment"]
on_session_creation = ["kms.session.process_login"]