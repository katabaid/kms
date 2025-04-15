// Copyright (c) 2025, GIS and contributors
// For license information, please see license.txt

frappe.ui.form.on("FO Payment", {
	items_remove(frm) {
    update_total_payment(frm);
	},
	items_add(frm) {
    update_total_payment(frm);
	},
  validate(frm) {
    if (frm.doc.total_payment > frm.doc.outstanding_amount) {
      frappe.throw(__('Total Payment cannot exceed Outstanding Amount.'));
    }
  }
});

frappe.ui.form.on("FO Payment Detail", {
  amount(frm, cdt, cdn){
    update_total_payment(frm)
  }
});

const update_total_payment = (frm) => {
  const outstanding = flt(frm.doc.outstanding_amount);
  let total =0;
  (frm.doc.items||[]).forEach(item => {
    total += flt(item.amount);
  });
  if (total > outstanding) {
    frappe.msgprint(__('Total Payment ({0}) exceeds Outstanding Amount ({1})', [
      total, frm.doc.outstanding_amount
    ]));
  }
  frm.set_value('total_payment', total)
}