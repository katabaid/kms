# Copyright (c) 2025, GIS and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

class FOPayment(Document):
	def on_submit(self):
		revenue_account, currency = frappe.db.get_value(
			'Sales Invoice', self.invoice, ['debit_to', 'currency'])
		contact = email = bank_account = party_bank_account = None
		for item in self.items:
			result = frappe.db.sql("""
				SELECT IFNULL((SELECT default_bank_account FROM `tabCustomer` tcu WHERE tcu.name = %s),
				(SELECT default_account FROM `tabMode of Payment Account` tmpa WHERE company = %s AND parent = %s)) bank_account,
				IFNULL((SELECT name FROM `tabBank Account` WHERE party_type = 'Customer' AND party = %s AND is_default = 1),
				(SELECT name FROM `tabBank Account` WHERE party_type = 'Customer' AND party = %s LIMIT 1)) party_bank_account,
				(SELECT name FROM tabContact tco WHERE name = 
					(SELECT parent FROM `tabDynamic Link` tdl WHERE link_doctype = 'Customer' AND parenttype = 'Contact' AND link_name = %s)
				) as name, 
				(SELECT email_id FROM tabContact tco WHERE name = 
					(SELECT parent FROM `tabDynamic Link` tdl WHERE link_doctype = 'Customer' AND parenttype = 'Contact' AND link_name = %s)
				) as email_id
			""", 
				(self.customer, self.company, item.mode_of_payment, self.customer, self.customer, self.customer, self.customer), 
				as_dict=True)
			if result:
				contact = result[0].get('name')
				email = result[0].get('email_id')
				bank_account = result[0].get('bank_account')
				party_bank_account = result[0].get('party_bank_account')
			print(bank_account)
			payment_entry = frappe.new_doc('Payment Entry')
			payment_entry.payment_type = 'Receive'
			payment_entry.posting_date = self.posting_date
			payment_entry.company = self.company
			payment_entry.mode_of_payment = item.mode_of_payment
			payment_entry.party_type = 'Customer'
			payment_entry.party = self.customer
			payment_entry.party_name = self.customer_name
			payment_entry.cost_center = self.cost_center
			payment_entry.reference_no = item.reference_no
			payment_entry.reference_date = item.reference_date
			payment_entry.contact_person = contact
			payment_entry.contact_email = email
			payment_entry.bank_account = bank_account
			payment_entry.party_bank_account = party_bank_account
			payment_entry.party_balance = self.outstanding_amount
			payment_entry.paid_from = revenue_account
			payment_entry.paid_from_account_currency = currency
			payment_entry.paid_from_account_balance = self.outstanding_amount
			payment_entry.paid_to = bank_account
			payment_entry.paid_to_account_currency = currency
			payment_entry.paid_amount = item.amount
			payment_entry.received_amount = item.amount
			payment_entry.append('references', {
				'reference_doctype': 'Sales Invoice',
				'reference_name': self.invoice,
				'allocated_amount': item.amount,
				'total_amount': self.outstanding_amount,
				'outstanding_amount': self.outstanding_amount-item.amount,
				'account': revenue_account,
			})
			payment_entry.flags.ignore_permissions = True
			payment_entry.insert()
			payment_entry.submit()

	def validate(self):
		if not self.items:
			frappe.throw('At least one line of payment must exists.')
		if self.total_payment <= 0:
			frappe.throw('Add payment amount to continue.')
		if sum((item.amount or 0) for item in self.items) <= 0:
			frappe.throw("Total of payment amounts must be greater than 0.")
