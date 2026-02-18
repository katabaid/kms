# Patient Appointment Lock Solution

## Problem Description

When multiple users simultaneously select the same patient from the queue and click "Add from Queue", they can both proceed to create services in different rooms. This results in the same patient being registered in multiple healthcare service units, which is forbidden.

### Root Cause

The race condition occurs because:
1. Multiple users open the queue dialog and see the same patient as available
2. Both users click to select the patient
3. Both requests reach the server simultaneously
4. The existing checks in `_create_exam` are performed too late in the process
5. Both requests succeed, creating duplicate service records

## Solution

We implemented an **atomic lock mechanism** on the Patient Appointment doctype using a custom field `custom_is_locked`. This ensures that only one user can process a patient at a time.

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     User Action Flow                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  User 1 clicks "Add from Queue"  │  User 2 clicks "Add from Queue" │
└─────────────────────────────────────────────────────────────────┘
                              │                              │
                              ▼                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  Both call create_service(patient_A, room_1)  │  Both call create_service(patient_A, room_2) │
└─────────────────────────────────────────────────────────────────┘
                              │                              │
                              ▼                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  ATOMIC UPDATE: SET custom_is_locked = 1                        │
│  WHERE custom_is_locked = 0                                     │
│  User 1: SUCCESS (1 row updated)  │  User 2: FAILED (0 rows updated) │
└─────────────────────────────────────────────────────────────────┘
                              │                              │
                              ▼                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  User 1: Create service  │  User 2: Throw error "Patient is locked" │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  FINALLY: Release lock (SET custom_is_locked = 0)               │
└─────────────────────────────────────────────────────────────────┘
```

## Implementation Details

### 1. Custom Field Addition

**File:** `kms/kms/patches/add_patient_appointment_lock_field.py`

A migration patch adds the `custom_is_locked` field to the Patient Appointment doctype:

```python
frappe.get_doc({
    'doctype': 'Custom Field',
    'dt': 'Patient Appointment',
    'fieldname': 'custom_is_locked',
    'fieldtype': 'Check',
    'label': 'Is Locked',
    'insert_after': 'custom_procedures',
    'hidden': 1,  # Hidden from UI
    'read_only': 1,
    'module': 'KMS',
    'description': 'Internal field to prevent concurrent room assignments.'
}).insert()
```

### 2. Lock Acquisition in create_service

**File:** `kms/healthcare.py` (lines 5-38)

The [`create_service`](kms/healthcare.py:5) function now:

1. **Gets patient_appointment early** (before any processing)
2. **Attempts atomic lock acquisition** using a conditional UPDATE
3. **Checks if lock was acquired** (returns number of rows affected)
4. **Proceeds with service creation** if lock acquired
5. **Releases lock in finally block** (ensures lock is always released)

```python
@frappe.whitelist()
def create_service(name, room):
    # Get patient_appointment early
    patient_appointment = frappe.db.get_value(doctype, name, 'patient_appointment')
    
    # ATOMIC: Try to acquire lock
    locked = frappe.db.sql("""
        UPDATE `tabPatient Appointment`
        SET custom_is_locked = 1
        WHERE name = %s AND (custom_is_locked = 0 OR custom_is_locked IS NULL)
    """, (patient_appointment,))
    
    # Check if we actually acquired the lock
    if not locked or locked == 0:
        frappe.throw("Patient is currently being processed by another user. Please refresh and try again.")
    
    try:
        # Proceed with service creation
        # ...
    finally:
        # Always release lock
        frappe.db.set_value('Patient Appointment', patient_appointment, 'custom_is_locked', 0)
```

### 3. Why This Works

The atomic UPDATE operation ensures:
- **No race condition**: The database guarantees atomicity
- **Only one winner**: Only one request can update the row from 0 to 1
- **Immediate feedback**: The second request gets 0 rows updated and fails
- **No deadlocks**: Lock is released immediately after service creation
- **Automatic cleanup**: The `finally` block ensures lock is released even on error

## Deployment Instructions

### Step 1: Run the Migration Patch

```bash
cd /home/aulia/frappe-bench
bench execute kms.kms.patches.add_patient_appointment_lock_field.execute
```

Or restart the bench to auto-run patches:
```bash
bench restart
```

### Step 2: Verify the Field Exists

```bash
bench --site [site-name] console
>>> frappe.db.exists('Custom Field', {'dt': 'Patient Appointment', 'fieldname': 'custom_is_locked'})
True
```

### Step 3: Test the Implementation

1. Open two browser windows with different users
2. Both navigate to the same list view (e.g., Doctor Examination)
3. Both click "Add from Queue" simultaneously
4. Both select the same patient
5. Click OK on both dialogs
6. **Expected Result**: Only one succeeds, the other gets an error

## Testing Scenarios

### Scenario 1: Normal Operation
- User clicks "Add from Queue"
- Selects patient
- Service is created successfully
- Lock is released automatically

### Scenario 2: Concurrent Access
- User 1 and User 2 both click "Add from Queue" for same patient
- User 1 acquires lock and creates service
- User 2 gets error: "Patient is currently being processed by another user. Please refresh and try again."

### Scenario 3: Error Handling
- User acquires lock
- An error occurs during service creation
- Lock is released in `finally` block
- Next user can now process the patient

## Benefits

1. **Prevents duplicate service creation**: Only one user can process a patient at a time
2. **No infrastructure changes**: Uses existing database, no Redis or external services needed
3. **Simple implementation**: Minimal code changes, easy to understand and maintain
4. **Automatic lock release**: Uses try/finally to ensure lock is always released
5. **Clear error messages**: Users get informative feedback when patient is locked

## Files Modified

1. `kms/healthcare.py` - Added atomic lock acquisition in [`create_service`](kms/healthcare.py:5)
2. `kms/kms/patches/add_patient_appointment_lock_field.py` - New migration patch
3. `kms/patches.txt` - Added patch reference
4. `kms/kms/patches/__init__.py` - New init file for patches module

## Future Enhancements

1. **Lock timeout**: Add timestamp field to automatically release stale locks
2. **Lock ownership**: Track which user holds the lock for debugging
3. **Queue position**: Show users their position in the processing queue
4. **Frontend refresh**: Auto-refresh the queue list when a patient is locked
