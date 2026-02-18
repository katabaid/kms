import frappe

def execute():
    """
    Add custom_include_previous_mcu_results field to Patient Appointment doctype.
    This field is used to control whether previous MCU results are included when generating doctor results.
    It is only visible when appointment_type is "MCU".
    """
    # Check if the field already exists
    if frappe.db.exists('Custom Field', {'dt': 'Patient Appointment', 'fieldname': 'custom_include_previous_mcu_results'}):
        return
    
    # Create the custom field
    frappe.get_doc({
        'doctype': 'Custom Field',
        'dt': 'Patient Appointment',
        'fieldname': 'custom_include_previous_mcu_results',
        'fieldtype': 'Check',
        'label': 'Include Previous MCU Results',
        'default': 1,
        'depends_on': 'eval:doc.appointment_type == "MCU"',
        'insert_after': 'custom_mcu_items',
        'hidden': 0,
        'read_only': 0,
        'module': 'KMS',
        'description': 'Include previous MCU results when generating doctor result. Only visible for MCU appointments.'
    }).insert()
    
    frappe.db.commit()