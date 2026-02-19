import frappe

def execute():
  """
  Create the kms_patient_lock table for patient appointment locking.
  This table is used to prevent race conditions when multiple users
  try to assign the same patient to different rooms simultaneously.
  """
  frappe.db.sql("""
    CREATE TABLE IF NOT EXISTS `kms_patient_lock` (
      `lock_key` VARCHAR(255) NOT NULL PRIMARY KEY,
      `locked_by` VARCHAR(255) NOT NULL,
      `locked_at` DATETIME NOT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  """)
  frappe.db.commit()
