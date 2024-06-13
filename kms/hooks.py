from . import __version__ as app_version

app_name = "kms"
app_title = "KMS"
app_publisher = "GIS"
app_description = "KMS customizations"
app_email = "gis@global-infotech.co.id"
app_license = "MIT"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/kms/css/kms.css"
# app_include_js = "/assets/kms/js/kms.js"
# app_include_js = "/assets/kms/js/set_session_default.js"

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
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
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
"Shift Request": "kms.override.shift_request.KmsShiftRequest"
}

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
#	"*": {
#		"on_update": "method",
#		"on_cancel": "method",
#		"on_trash": "method"
#	}
# }
doc_events = {
  "Item Price": {
    "on_change": "kms.api.update_item_price",
    "after_insert": "kms.api.update_item_price",
    "before_save": "kms.api.update_item_price",
  }
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
#	"all": [
#		"kms.tasks.all"
#	],
#	"daily": [
#		"kms.tasks.daily"
#	],
#	"hourly": [
#		"kms.tasks.hourly"
#	],
#	"weekly": [
#		"kms.tasks.weekly"
#	],
#	"monthly": [
#		"kms.tasks.monthly"
#	],
# }

# Testing
# -------

# before_tests = "kms.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
#	"frappe.desk.doctype.event.event.get_events": "kms.event.get_events"
# }
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
  {'dt':'Server Script', 'filters': [['module', '=', 'KMS']]}, 
  {'dt':'Client Script', 'filters': [['module', '=', 'KMS']]}, 
  {'dt':'Custom Field', 'filters': [['module', '=', 'KMS']]}, 
  {'dt':'Property Setter', 'filters': [['module', '=', 'KMS']]}, 
  {'dt':'DocType', 'filters': [['module', '=', 'KMS']]},
  {'dt':'Report', 'filters': [['module', '=', 'KMS']]},
  {'dt':'Healthcare Service Unit'},
  {'dt':'Healthcare Service Unit Type'},
  {'dt':'Workspace'},]
on_logout = ["kms.session.remove_room_assignment"]