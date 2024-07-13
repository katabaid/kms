import frappe
from frappe.utils.password import update_password, check_password
from frappe.permissions import add_user_permission, has_permission
from frappe import auth

@frappe.whitelist(allow_guest=True)
def register_user(name, email, password, gender, idtype, idnumber, dob):
  try:
    user = frappe.get_doc({
      'doctype': 'User',
      'email': email,
      'first_name': name
    })
    user.insert(ignore_permissions=True)
    update_password(user.name, password)
    # Create a patient in the Healthcare module
    patient = frappe.get_doc({
      'doctype': 'Patient',
      'first_name': user.first_name,
      'email': user.email,
      'user_id': user.name,
      'sex': gender,
      'custom_id_type': idtype,
      'uid': idnumber,
      'dob': dob
    })
    patient.insert(ignore_permissions=True)
    frappe.db.commit()

    # Add user permission for the patient
    add_user_permission('Patient', patient.name, user.name)
    frappe.db.commit()
    return 'User registration successful. Please check your email for the confirmation code.'
  except frappe.DuplicateEntryError:
    return 'Email already exists'
  except Exception as e:
    frappe.db.rollback()
    return str(e)

@frappe.whitelist(allow_guest=True)
def verify_confirmation_code(email, code):
  try:
    user = frappe.get_doc('User', {'email': email})
    if user.confirmation_code == code:
      user.confirmation_code = ''
      user.save(ignore_permissions=True)
      frappe.db.commit()

      # Create a patient in the Healthcare module
      patient = frappe.get_doc({
        'doctype': 'Patient',
        'first_name': user.first_name,
        'email': user.email,
        'user_id': user.name
      })
      patient.insert(ignore_permissions=True)
      frappe.db.commit()

      # Add user permission for the patient
      add_user_permission('Patient', patient.name, user.name)

      return 'User and patient registration successful'
    else:
      return 'Invalid confirmation code'
  except Exception as e:
    frappe.db.rollback()
    return str(e)

@frappe.whitelist(allow_guest=True)
def login(usr, pwd):
  try:
    login_manager = frappe.auth.LoginManager()
    login_manager.authenticate(user=usr, pwd=pwd)
    login_manager.post_login()
  except frappe.exceptions.AuthenticationError:
    frappe.local.response['message']={
      'success_key': 0,
      'message': 'Authentication error.'
    }
    return
  api_generate = generate_key(frappe.session.user)
  user = frappe.get_doc('User', frappe.session.user)
  frappe.response['message']={
    'success_key': 1,
    'message': 'Authentication success.',
    'sid': frappe.session.sid,
    'api_key': user.api_key,
    'api_secret': api_generate,
    'username': user.username,
    'email': user.email
  }

def generate_key(user):
  user_doc = frappe.get_doc('User', user)
  api_secret = frappe.generate_hash(length=15)
  if not user_doc.api_key:
    api_key = frappe.generate_hash(length=15)
    user_doc.api_key = api_key
  user_doc.api_secret = api_secret
  user_doc.save()

  return api_secret

@frappe.whitelist(allow_guest=True)
def create_patient_appointment(patientEmail, appointmentDate, branch, hcu):
  try:
    patient = frappe.get_doc('Patient', {'email': patientEmail})
    service_unit = frappe.db.get_value('Healthcare Service Unit', {'custom_branch': branch, 'service_unit_type': hcu}, 'name')
    appointment = frappe.new_doc('Patient Appointment')
    appointment.patient = patient.name
    appointment.appointment_type = hcu
    appointment.appointment_for = 'Service Unit'
    appointment.appointment_date = appointmentDate
    appointment.service_unit = service_unit
    appointment.custom_priority = '3. Outpatient'
    appointment.insert(ignore_permissions=True)
    frappe.db.commit()
    return 'Patient appointment created successfully'

    """ if has_permission('Patient', patient.name, frappe.session.user):
        appointment = frappe.get_doc({
            'doctype': 'Patient Appointment',
            'patient': patient.name,
            'appointment_type': 'General Practice'
            'appointment_date': frappe.utils.nowdate(),
            'appointment_time': appointmentTime
        })
        appointment = frappe.new_doc('Patient Appointment')
        appointment.patient = patient.name
        appointment.appointment_type = 'General Practice'
        appointment.appointment_date = appointmentDate
        appointment.service_unit = 'GP - JM - KMS'
        appointment.insert(ignore_permissions=True)
        frappe.db.commit()
        return 'Patient appointment created successfully'
    else:
        return 'You do not have permission to create appointments for this patient' """
  except Exception as e:
    frappe.db.rollback()
    return str(e)