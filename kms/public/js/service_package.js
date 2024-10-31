frappe.ui.form.on('Product Bundle', {
	setup(frm) {
		frm.set_df_property('custom_customer', 'read_only', 1);
		frm.set_df_property('custom_lead', 'read_only', 1);
		frm.set_df_property('description', 'read_only', 1);
		frm.set_df_property('new_item_code', 'read_only', 1);
		frm.set_query("custom_customer", ()=>{
      return {
        filters: {
          customer_type: ['in', ['PT', 'CV']]
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
        label: "Copy from Service Package",
        fieldname: "copy_from",
        fieldtype: "Link",
        options: "Product Bundle",
        get_query: () => {
          return {
            filters: {disabled: false}
          };
        }
      }
    ], (values) => {
      frappe.db.insert({
        doctype: "Item",
        item_name: values.bundle_name,
        item_group: "Exam Course",
        stock_uom: "Unit",
        is_stock_item: false,
        include_item_in_manufacturing: false,
        is_purchase_item: false,
        is_sales_item: true,
        custom_bundle_position: 9999999
      }).then(doc=>{
        let new_pb = {};
        new_pb.doctype = 'Product Bundle';
        new_pb.new_item_code = doc.name;
        new_pb.description = values.bundle_name;
        new_pb.items = [];
        if(values.copy_from) {
          frappe.db.get_doc('Product Bundle', values.copy_from).then(copy_from=>{
            copy_from.items.forEach((e,i)=>{
              new_pb.items.push({
                item_code: e.item_code,
                qty: 1,
                description: e.description
              })
            })
            frappe.db.insert(new_pb).then(new_doc => {
              frappe.set_route('Form', new_doc.doctype, new_doc.name)})    
          })
        } else {
          frappe.db.get_list('Item', {
            fields: ['item_code', 'item_name'],
            filters: { is_stock_item: 0, is_sales_item: 1, is_purchase_item: 0, custom_mandatory_item_in_package: 1}
          }).then(mandatory => {
            mandatory.forEach((e) => {
              new_pb.items.push({
                item_code: e.item_code,
                qty: 1,
                description: e.item_name
              })
            })
            frappe.db.insert(new_pb).then(new_doc => {
              frappe.set_route('Form', new_doc.doctype, new_doc.name)})    
          })
        };
      });
    });
	},
});
