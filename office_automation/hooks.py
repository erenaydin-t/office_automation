app_name = "office_automation"
app_title = "Office Automation"
app_publisher = "Milanpars"
app_description = (
	"Iranian-style office automation (Cartable, Erja referrals, delegation, "
	"thread printing) for Frappe/ERPNext"
)
app_email = "aydineren1986@gmail.com"
app_license = "mit"

# Apps
# ------------------

# This module targets Persian (Jalali) deployments and relies on the
# persian_calendar app for Jalali display across the desk + print helpers.
required_apps = ["persian_calendar"]

# Each item in the list will be shown as an app icon on the /apps screen.
add_to_apps_screen = [
	{
		"name": "office_automation",
		"logo": "/assets/office_automation/images/office_automation_logo.svg",
		"title": "Office Automation",
		"route": "/app/inbox",
		"has_permission": "office_automation.office_automation.api.permissions.has_app_permission",
	}
]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# Routing-layer guard that redirects the Office Automation workspace to /app/inbox
# (overridable with ?noredirect=1). Lightweight; only acts on that one route.
app_include_js = "/assets/office_automation/js/oa_router.js"

# Standalone @font-face stylesheet for the bundled free Persian fonts
# (Vazirmatn, Shabnam). Loaded directly (not via the SPA bundle, whose esbuild
# has no font loader) so the editor + letter views can render them.
app_include_css = "/assets/office_automation/css/oa_fonts.css"

# include js, css files in header of web template
# web_include_css = "/assets/office_automation/css/office_automation.css"
# web_include_js = "/assets/office_automation/js/office_automation.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "office_automation/public/scss/website"

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	"Automation Letter": {
		"on_trash": "office_automation.office_automation.doctype.document_referral.document_referral.on_reference_trash",
	},
}

# Jinja
# ----------
# Add methods and filters to jinja environment so the thread print format can
# recursively pull the Erja tree.

jinja = {
	"methods": [
		"office_automation.office_automation.print_format.thread_print.get_letter_thread",
	],
}

# Installation
# ------------

# before_install = "office_automation.install.before_install"
after_install = "office_automation.install.after_install"
after_migrate = "office_automation.install.after_migrate"

# Permissions
# -----------
# Permissions evaluated in scripted ways

permission_query_conditions = {
	"Automation Letter": "office_automation.office_automation.permissions.delegation.automation_letter_query_conditions",
	"Document Referral": "office_automation.office_automation.permissions.delegation.document_referral_query_conditions",
}

has_permission = {
	"Automation Letter": "office_automation.office_automation.permissions.delegation.has_permission",
	"Document Referral": "office_automation.office_automation.permissions.delegation.has_permission",
}

# Scheduled Tasks
# ---------------

scheduler_events = {
	"daily": [
		"office_automation.tasks.daily",
	],
}

# Fixtures
# --------
# Exported so the custom roles travel between sites. Standard records (DocTypes,
# Page, Print Format, Workspace, Number Cards) already ship as module files and
# are synced on `bench migrate`.

fixtures = [
	{
		"dt": "Role",
		"filters": [["name", "in", ["Office Automation Manager", "Office Automation User"]]],
	}
]

# Testing
# -------

# before_tests = "office_automation.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "office_automation.event.get_events"
# }
