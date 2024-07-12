frappe.ui.form.on('Product Bundle', {
	setup(frm) {
		frm.set_df_property('custom_customer', 'read_only', 1);
		frm.set_df_property('description', 'read_only', 1);
		frm.set_df_property('new_item_code', 'read_only', 1);
		frm.set_query("custom_price_list", ()=>{
      return {
        filters: {
          selling: true
        }
      };
		});
		/*Child Table filter*/
		frm.set_query("item_code", "items", () =>{
      return {
        filters: {
          custom_product_bundle: true,
          is_sales_item: true,
          is_stock_item: false
        }
      };
		});
	},
	/*BUTTON CREATE*/
	custom_create(frm) {
    frappe.prompt([
      {
        label: 'Bundle Name',
        fieldname: 'bundle_name',
        fieldtype: 'Data',
        reqd: true
      },
      {
        label: 'Customer',
        fieldname: 'customer',
        fieldtype: 'Link',
        reqd: true,
        options:"Customer",
        get_query: () => {
          return {
            filters: {"customer_type": "Company"}
          };
        }
      },
      {
        label: "Price List",
        fieldname: "price_list",
        fieldtype: "Link",
        reqd: true,
        options: "Price List",
        get_query: () => {
          return {
            filters: {selling: true}
          };
        }
      },
      {
        label: "Medical Check Up",
        fieldname: "is_mcu",
        fieldtype: "Check"
      },
      {
        label: "From Service Package",
        fieldname: "copy_from",
        fieldtype: "Link",
        options: "Product Bundle",
        get_query: () => {
          return {
            filters: {custom_enable: true}
          };
        }
      }
    ], (values) => {
        /*AUTOMATICALLY CREATE ITEM*/
      frappe.db.insert({
        doctype: "Item",
        item_name: values.bundle_name,
        item_group: "Exam Course",
        stock_uom: "Unit",
        is_stock_item: false,
        include_item_in_manufacturing: false,
        is_purchase_item: false,
        is_sales_item: true,
        custom_product_bundle_customer: values.customer
      }). then(doc=>{
        /*SET PARENT VALUES*/
        frm.set_value({
          new_item_code: doc.name,
          description: doc.item_name,
          custom_customer: values.customer,
          custom_price_list: values.price_list
        });
        /*SET MANDATORY ITEMS IF MCU*/
        if (!values.copy_from) {
          if(values.is_mcu){
            /*fetch only mandatory item*/
            frappe.call({
              method: "kms.api.get_mcu",
              args: {price_list: values.price_list}
            }).then((r)=>{
              frm.doc.items = [];
              let total = 0;
              $.each(r.message, function(_i, e){
                let item = frm.add_child("items");
                item.item_code = e.item_code;
                item.qty = 1;
                item.description = e.item_name;
                item.rate = e.price_list_rate;
                total += e.price_list_rate;
                frm.set_value("custom_rate", total);
                frm.refresh_field("custom_rate");
              });
              refresh_field("items");
            });
          }
        } else {
          /*fetch from other product bundle*/
          frappe.db.get_doc("Product Bundle", values.copy_from).then(doc=>{
            frm.doc.items =[];
            let total = 0;
            $.each(doc.items, function(_i, e){
              let item = frm.add_child("items");
              item.item_code = e.item_code;
              item.qty = e.qty;
              item.description = e.description;
              item.rate = e.rate;
              total += e.rate;
              frm.set_value("custom_rate", total);
            });
            refresh_field("custom_rate");
            refresh_field("items");
          });
        }
      });
    });
	},
	after_save(frm) {
    let filters = {};
    filters.item_code = frm.doc.new_item_code;
    filters.price_list = frm.doc.custom_price_list;
    filters.customer = frm.doc.custom_customer;
    filters.price_list_rate = frm.doc.custom_rate;
    frappe.call({
      method:'kms.api.upsert_item_price',
      args: {
        item_code: frm.doc.new_item_code, 
        price_list: frm.doc.custom_price_list,
        customer: frm.doc.custom_customer,
        price_list_rate: frm.doc.custom_rate
      }
    }).then((r)=>{
        console.log(r);
    });
	}
});

frappe.ui.form.on('Product Bundle Item', {
	item_code(frm, cdt, cdn) {
    let d = locals[cdt][cdn];
    frappe.model.set_value(d.doctype, d.name, "qty", 1);
    frappe.db.get_doc(
      'Item Price',
      null,
      {
        item_code: d.item_code,
        selling: true,
        price_list: frm.doc.custom_price_list
      }).then(r=>{
        frappe.model.set_value(d.doctype, d.name, 'rate', r.price_list_rate);
      });
    frm.refresh_field("items");
	},
	rate(frm, cdt, cdn) {
    let d = locals[cdt][cdn];
    let total = 0;
    frm.doc.items.forEach((d)=>{
      total += d.rate ? d.rate : 0;
    });
    frm.set_value("custom_rate", total);
	},
	items_add(frm, cdt, cdn) {
    let d = locals[cdt][cdn];
    let total = 0;
    frm.doc.items.forEach((d)=>{
      total += d.rate ? d.rate : 0;
    });
    frm.set_value("custom_rate", total);
	},
	items_remove(frm, cdt, cdn) {
    let d = locals[cdt][cdn];
    let total = 0;
    frm.doc.items.forEach((d)=>{
      total += d.rate ? d.rate : 0;
    });
    frm.set_value("custom_rate", total);
	},
});