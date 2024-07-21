frappe.ui.form.on('Quotation', {
  quotation_to(frm) {
    frm.doc.party_name = '';
    if(frm.doc.quotation_to === 'Customer'){
      frm.set_query('party_name', () => {
        return {
          filters: {customer_type: 'Company'}
        };
      });
    }
  },
  /* setup(frm) {
    if(frm.doc.__islocal){
      frm.doc.items = [];
      frm.set_df_property('items', 'hidden', 1);
    } else {
      frm.set_df_property('items', 'hidden', 0);
    }
  }, */
  refresh(frm) {
    frm.trigger('create_package_items_tab');
    frm.add_custom_button(__('Process'), () => {
      frm.trigger('process');
    });

    frm.trigger('hide_add_and_multiple_buttons');

    frm.set_query("item_code", "items", function(doc, cdt, cdn){
      let d = locals[cdt][cdn];
      return {
        filters: {
          is_sales_item : true,
          disabled: false,
          is_purchase_item: false
        }
      };
    });
    /***Custom button to create product bundle within a Lead before save***/
    if (frm.doc.docstatus===0 && frm.doc.party_name && (frm.doc.quotation_to === 'Customer' || frm.doc.quotation_to === 'Lead')){
      frm.add_custom_button(
        __('New Product Bundle'),
        () => {
          //ambil data item
          frappe.call({
            method: "kms.api.get_items_to_create_bundle"
          }).then((r)=>{
            console.log(JSON.stringify(r.message))
            const uniqueLv1 = [...new Set(r.message.map(item=> item.lv1))].join('\n');
            let fields = [
              {
                fieldname: 'package_name',
                fieldtype: 'Data',
                label: 'Package Name',
                reqd: 1
              },
              {
                fieldname: 'sb_00',
                fieldtype: 'Section Break',
                label: 'Copy From',
                collapsible: 1
              },
              {
                fieldtype: 'Link',
                fieldname: 'copy_from',
                label: 'Copy from Package',
                options: 'Product Bundle'
              },
              {
                fieldname: 'sb_3',
                fieldtype: 'Section Break',
                label: 'Selected Examination Items',
                hidden: 0
              },
              {
                fieldname: 'html_1',
                fieldtype: 'HTML',
                label: 'Selected Examinations'
              },
              {
                fieldname: 'sb_1',
                fieldtype: 'Section Break',
                label: 'Examination Type'
              },
              {
                fieldname: 'select_1',
                fieldtype: 'Select',
                options: uniqueLv1,
              },
              {
                fieldname: 'cb_1',
                fieldtype: 'Column Break'
              },
              {
                fieldname: 'select_2',
                fieldtype: 'Select',
                hidden: 1,
                options: '',
              },
              {
                fieldname: 'cb_2',
                fieldtype: 'Column Break'
              },
              {
                fieldname: 'select_3',
                fieldtype: 'Select',
                hidden: 1,
                options: ''
              },
              {
                fieldname: 'sb_2',
                fieldtype: 'Section Break',
                label: 'Select Examination Items',
                hidden: 0
              },
              {
                fieldname: 'html_0',
                fieldtype: 'HTML',
                label: 'Selected Examinations'
              },
            ];

              // Grouping the data by distinct lv2 and lv3 values
            const groupedData = {};
            r.message.forEach(item => {
              const key = item.lv3 || item.lv2; // Use lv2 if lv3 is empty, otherwise use lv3
              if (!groupedData[key]) {
                groupedData[key] = [];
              }
              groupedData[key].push(item);
            });

            // Function to divide an array into n balanced arrays
            const divideArray = (arr, n) => {
              const result = Array.from({ length: n }, () => []);
              arr.forEach((item, index) => {
                result[index % n].push(item);
              });
              return result;
            };

            // Divide each group into three arrays with balanced count
            const dividedData = {};
            Object.keys(groupedData).forEach(key => {
              const groupItems = groupedData[key];
              const approxItemCount = Math.ceil(groupItems.length / 3);
              dividedData[key] = divideArray(groupItems, 3);
            });
            $.each(dividedData, (_i, e)=>{
              $.each(e, (a,b) =>{
                if(a==1){
                  fields.push({
                    fieldtype: 'Column Break',
                    fieldname: 'cb'
                  });
                }
                $.each(b, (c,d)=>{
                    fields.push({
                      fieldtype: 'Check',
                      label: d.item_name,
                      fieldname: d.name,
                      hidden: 1
                    });
                });
                if(a==1){
                  fields.push({
                    fieldtype: 'Column Break',
                    fieldname: 'cb'
                  });
                }
              });
            });
              
            /* fields.push(
              {
                fieldname: 'sb_0',
                fieldtype: 'Section Break',
                label: 'Pricing'
              },
              {
                fieldname: 'hpp',
                fieldtype: 'Currency',
                label: 'HPP',
                reqd: 1,
                read_only: 1
              },
              {
                fieldname: 'col_2',
                fieldtype: 'Column Break'
              },
              {
                fieldname: 'margin',
                fieldtype: 'Percent',
                label: 'Margin',
                reqd: 1
              },
              {
                fieldname: 'col_3',
                fieldtype: 'Column Break'
              },
              {
                fieldname: 'price',
                fieldtype: 'Currency',
                label: 'Price',
                reqd: 1
              }
            ); */

            //create dialog
            const pb = new frappe.ui.Dialog({
              title: 'Create Product Bundle',
              fields: fields,
              size: 'extra-large',
              primary_action_label: 'Create',
              primary_action(values) {
                console.log(values);
                const exams = Object.keys(values).filter(key => values[key] === 1);
                const item_rec = exams.map(item => (
                {
                  item_code: item,
                  description: '',
                  qty: 1,
                  rate: 0,
                  uom: "",
                  parent: ""
                }));
                frappe.call({
                  method: 'kms.api.create_product_bundle_from_quotation',
                  freeze: true,
                  args: {
                    items: item_rec,
                    name: values.package_name,
                    price_list: '',
                    party_name: frm.doc.party_name,
                    quotation_to: frm.doc.quotation_to,
                    //price: values.price,
                    //margin: values.margin
                  },
                  callback: (r) => {
                    if(r.message) {
                      let item = frm.add_child('items');
                      item.item_code = r.message.name;
                      item.item_name = r.message.description;
                      item.description = r.message.description;
                      //item.qty = values.qty;
                      item.uom = 'Unit';
                      //item.rate = values.price;
                      item.warehouse = '';
                      frm.refresh_field("items");
                    }
                  }
                });
                pb.hide();
              }
            });
            /***REACTIVITY ZONE***/	                    
            //Margin and Price reactivity
            /* pb.fields_dict.margin.$input.on('change', ()=>{
              let hpp_field = Number(pb.fields_dict.hpp.get_value());
              if(hpp_field){
                pb.fields_dict.price.set_value(hpp_field+pb.fields_dict.margin.get_value()*hpp_field/100);
              }
            });
            pb.fields_dict.price.$input.on('change', ()=>{
              let hpp_field = Number(pb.fields_dict.hpp.get_value());
              if(hpp_field){
                pb.fields_dict.margin.set_value((pb.fields_dict.price.get_value()-hpp_field)/hpp_field*100);
              }
            }); */
            let selectedValues = new Set();
              
            //Copy From Reactivity
            pb.fields_dict.copy_from.$input.on('blur', ()=>{
                //get item from db
              let copy_from_value = pb.get_value('copy_from');
              if(copy_from_value){
                frappe.db.get_doc('Product Bundle', copy_from_value).then((copy_doc)=>{
                  console.log(copy_doc);
                  //put items to checkboxes
                  if(copy_doc.items) {
                    $.each(copy_doc.items, (i_, e)=>{
                      pb.set_value(e.item_code, 1);
                      //update table
                      selectedValues.add(e.item_code);
                    });
                    let table_html = processDataWithRate(r.message, [...selectedValues]);
                    pb.fields_dict.html_1.$wrapper.html(table_html);
                    //update hpp, margin, price
                    pb.set_value('hpp', hpp);
                    pb.set_value('price', copy_doc.custom_rate);
                    pb.set_value('margin', copy_doc.custom_margin);
                  }
                });
              }
            });
            //create level 1 select event
            pb.fields_dict.select_1.$input.on('change', ()=>{
              //reset lower level selects
              pb.fields_dict.select_2.df.options = '';
              pb.fields_dict.select_2.df.hidden = 1;
              pb.fields_dict.select_3.df.options = '';
              pb.fields_dict.select_3.df.hidden = 1;
              pb.fields_dict.select_2.refresh();
              pb.fields_dict.select_3.refresh();
              //reset checkboxes
              $.each(r.message, (_i, e)=>{
                  pb.fields_dict[`${e.name}`].df.hidden = 1;
                  pb.fields_dict[`${e.name}`].refresh();
              });
              //create level 2 select
              const uniqueLv2 = [...new Set(r.message.filter(item => item.lv1 === pb.get_value('select_1')).map(item => item.lv2))].join('\n');
              pb.fields_dict.select_2.df.options = uniqueLv2;
              pb.fields_dict.select_2.df.hidden = 0;
              pb.fields_dict.select_2.refresh();
              //create level 2 select event
              pb.fields_dict.select_2.$input.on('change', ()=>{
                //reset lower level selects
                pb.fields_dict.select_3.df.options = '';
                pb.fields_dict.select_3.df.hidden = 1;
                pb.fields_dict.select_3.refresh();
                const uniqueLv3 = [...new Set(r.message.filter(item => item.lv2 === pb.get_value('select_2')).map(item => item.lv3))].join('\n');
                if(uniqueLv3){
                  //create level 2 select if available
                  pb.fields_dict.select_3.df.options = uniqueLv3;
                  pb.fields_dict.select_3.df.hidden = 0;
                  pb.fields_dict.select_3.refresh();
                  //create level 3 select event
                  pb.fields_dict.select_3.$input.on('change', ()=>{
                    $.each(r.message, (_i, e)=>{
                      pb.fields_dict[`${e.name}`].df.hidden = 1;
                      pb.fields_dict[`${e.name}`].refresh();
                    });
                    //display level 3 checkboxes
                    pb.fields_dict.sb_2.df.hidden = 0;
                    let display = r.message.filter(item => item.lv3 === pb.get_value('select_3')).map(item=>item.name);
                    $.each(display, (_i,e)=>{
                      pb.fields_dict[`${e}`].df.hidden=0;
                      pb.fields_dict[`${e}`].refresh();
                      //create level 3 checkboxes event
                      $(`input.input-with-feedback[data-fieldname="${e}"]`).change(function(){
                        let checkbox = $(this);
                        let value = checkbox.attr('data-fieldname');
                        if (checkbox.is(':checked')) {
                          selectedValues.add(value);
                        } else {
                          selectedValues.delete(value);
                        }
                        let table_html = processDataWithRate(r.message, [...selectedValues])
                        pb.fields_dict.html_1.$wrapper.html(table_html);
                        pb.fields_dict.hpp.set_value(hpp);
                        pb.fields_dict.html_1.refresh();
                      });
                    });
                  });
                } else {
                  //no level 3 select available, reset level 2 instead
                  $.each(r.message, (_i, e)=>{
                    pb.fields_dict[`${e.name}`].df.hidden = 1;
                    pb.fields_dict[`${e.name}`].refresh();
                  });
                  pb.fields_dict.sb_2.df.hidden = 0;
                  let display = r.message.filter(item => item.lv2 === pb.get_value('select_2')).map(item=>item.name);
                  //display level 2 checkboxes
                  $.each(display, (_i,e)=>{
                    pb.fields_dict[`${e}`].df.hidden=0;
                    pb.fields_dict[`${e}`].refresh();
                    //create level 2 checkboxes event
                    $(`input.input-with-feedback[data-fieldname="${e}"]`).change(function(){
                      let checkbox = $(this);
                      let value = checkbox.attr('data-fieldname');
                      if (checkbox.is(':checked')) {
                        selectedValues.add(value);
                      } else {
                        selectedValues.delete(value);
                      }
                      let table_html = processDataWithRate(r.message, [...selectedValues])
                      pb.fields_dict.html_1.$wrapper.html(table_html);
                      pb.fields_dict.hpp.set_value(Number(hpp));
                      pb.fields_dict.html_1.refresh();
                    });
                  });
                }
              });
            });
            /***REACTIVITY ZONE END***/
            pb.show();
          });
        },
        __('Get Items From'),
        'btn_default'
      );
    }
    
    /***Custom button to create Blanket Order after quotation is submitted***/
    if(frm.doc.docstatus===1 && !["Lost", "Ordered"].includes(frm.doc.status)){
      frm.add_custom_button(
        __('Blanket Order'),
        ()=> {
          frappe.new_doc(
            'Blanket Order',
            {
              blanket_order_type: 'Selling',
              customer: frm.doc.party_name,
              custom_quotation: frm.doc.name
            },
            doc => {
              let today = frappe.datetime.get_today();
              doc.from_date = today;
              doc.to_date = frappe.datetime.add_months(today, 1);
              doc.items = [];
              $.each(frm.doc.items, (_i,e)=>{
                let row = frappe.model.add_child(doc, "items");
                row.item_code = e.item_code;
                row.rate = e.rate;
                row.item_name = e.item_name;
                row.qty = e.qty;
              });
              refresh_field("items");
            }
          );
        },
        __('Create')
      );
    }
  },
  onload_post_render(frm) {
    frm.trigger('hide_add_and_multiple_buttons');
  },
  hide_add_and_multiple_buttons(frm){
    console.log('aaaaaaaaaaaaaaaaaaaaaaaa aa')
    frm.fields_dict['items'].grid.wrapper.find('.grid-add-multiple-rows').hide();
    frm.fields_dict['items'].grid.wrapper.find('.grid-add-row').hide();
  },
  process(frm){
    let dialog = new frappe.ui.Dialog({
      title: 'Process Quotation',
      size: 'extra-large',
      fields: [
        {
          fieldname: 'level_1',
          fieldtype: 'Select',
          label: 'Level 1',
          options: []
        },
        {
          fieldname: 'col2',
          fieldtype: 'Column Break',
        },
        {
          fieldname: 'level_2',
          fieldtype: 'Select',
          label: 'Level 2',
          options: [],
          hidden: 1
        },
        {
          fieldname: 'col3',
          fieldtype: 'Column Break',
        },
        {
          fieldname: 'level_3',
          fieldtype: 'Select',
          label: 'Level 3',
          options: [],
          hidden: 1
        },
        {
          fieldname: 'dynamic_selects_section',
          fieldtype: 'Section Break',
          label: 'Select Examination',
        },
        {
          fieldname: 'selected_items',
          fieldtype: 'MultiCheck',
          options: [],
          hidden: 1,
          columns: 3
        },
        {
          fieldname: 'selected_items_table',
          fieldtype: 'Table',
          label: 'Selected Items',
          cannot_add_rows: true,
          cannot_delete_rows: true,
          in_place_edit: true,
          data: [],
          fields: [
            {fieldname: 'name', label: 'Item / Group', fieldtype: 'Data', in_list_view: 1, read_only: 1, columns: 10},
            {fieldname: 'is_group', label: 'Is Group', fieldtype: 'Check', hidden: 1},
            {fieldname: 'item_code', label: 'Item Code', fieldtype: 'Data', hidden: 1}
          ]
        }
      ],
      primary_action: (values) => {
        processSelectedItems(values.selected_items);
        dialog.hide();
      },
      primary_action_label: __('Process')
    });
    setupDynamicSelects(dialog);
    dialog.show();
  },

  create_package_items_tab(frm) {
    frappe.call({
      method: 'kms.api.get_quotation_item',
      freeze: true,
      args: {quotation_no: frm.doc.name},
      callback: (r) => {
        if(r.message) {
          let prev_idx = '';
          let prev_item_group = '';
          
          cur_frm.fields_dict.custom_html_field.$wrapper.empty();
          cur_frm.fields_dict.custom_html_field.$wrapper.append(`<div class="grid-field" id="pigf"></div>`);
          $('#pigf').append(`<div class="form-grid-container" id="pigc"></div>`);
          $('#pigc').append(`<div class="form-grid" id="pig"></div>`);
          $('#pig').append(`<div class="grid-heading-row" id="pighr"></div)`);
          $('#pighr').append(`<div class="grid-row" id="pigr"></div>`);
          $('#pigr').append(`<div class="data-row row" id="pidrr"></div>`);
          $('#pidrr').append(`<div class="col grid-static-col col-xs-4" id="picol1"></div>`);
          $('#picol1').append(`<div class="static-area" id=picol1s>Item Code</div>`);
          $('#pidrr').append(`<div class="col grid-static-col col-xs-1 text-right" id="picol2"></div>`);
          $('#picol2').append(`<div class="static-area" id=picol2s>Qty</div>`);
          $('#pidrr').append(`<div class="col grid-static-col col-xs-2 text-right" id="picol3"></div>`);
          $('#picol3').append(`<div class="static-area" id=picol5s>Rate</div>`);
          $('#pidrr').append(`<div class="col grid-static-col col-xs-2 text-right" id="picol4"></div>`);
          $('#picol4').append(`<div class="static-area" id=picol4s>Amount</div>`);
          $('#pidrr').append(`<div class="col grid-static-col col-xs-3 text-right" id="picol5"></div>`);
          $('#picol5').append(`<div class="static-area" id=picol5s>Total</div>`);
          
          $('#pig').append(`<div class="grid-body" id="pigb"></div)`);
          $('#pigb').append(`<div class="rows" id="pir"></div)`);
          
          $.each(r.message, (_i, e) => {
            $('#pir').append(`<div class="grid-row" data-idx="${_i}" id="pigr${_i}"></div>`);
            $(`#pigr${_i}`).append(`<div class="data-row row" id="pidr${_i}"></div>`);
            if(prev_idx != e.idx){
              $(`#pidr${_i}`).append(`<div class="col grid-static-col col-xs-4 bold grid-heading-row" id="pigscidx1${_i}"></div>`);
              $(`#pigscidx1${_i}`).append(`<a href="/app/product-bundle/${e.name}">&rsaquo; &rsaquo; ${e.bundle_name}</a>`);
              $(`#pidr${_i}`).append(`<div class="col grid-static-col col-xs-1 bold grid-heading-row" id="pigscidx2${_i}"></div>`);
              $(`#pigscidx2${_i}`).append(`<div style="text-align: right">${frappe.format(e.quotation_qty, {"fieldtype":"Int"})}</div>`);
              $(`#pidr${_i}`).append(`<div class="col grid-static-col col-xs-2 bold grid-heading-row" id="pigscidx3${_i}"></div>`);
              $(`#pigscidx3${_i}`).append(`<div style="text-align: right">${frappe.format(0, {"fieldtype":"Currency"})}</div>`);
              $(`#pidr${_i}`).append(`<div class="col grid-static-col col-xs-2 bold grid-heading-row" id="pigscidx4${_i}"></div>`);
              $(`#pigscidx4${_i}`).append(`<div style="text-align: right">${frappe.format(e.quotation_rate, {"fieldtype":"Currency"})}</div>`);
              $(`#pidr${_i}`).append(`<div class="col grid-static-col col-xs-3 bold grid-heading-row" id="pigscidx5${_i}"></div>`);
              $(`#pigscidx5${_i}`).append(`<div style="text-align: right">${frappe.format(e.quotation_rate*e.quotation_qty, {"fieldtype":"Currency"})}</div>`);

              $(`#pidr${_i}`).append(`<div class="col grid-static-col col-xs-12 bold grid-heading-row" id="pigscig2${_i}"></div>`);
              $(`#pigscig2${_i}`).append(`<a href="/app/item-group/${e.item_group}">&rsaquo; ${e.item_group}</a>`);
            } else {
              if(prev_item_group != e.item_group){
                $(`#pidr${_i}`).append(`<div class="col grid-static-col col-xs-12 bold grid-heading-row" id="pigscig2${_i}"></div>`);
                $(`#pigscig2${_i}`).append(`<a href="/app/item-group/${e.item_group}">&rsaquo; ${e.item_group}</a>`);
              }
            }
            $(`#pidr${_i}`).append(`<div class="col grid-static-col col-xs-4 bold" id="pigsc1${_i}"></div>`);
            $(`#pigsc1${_i}`).append(`<a href="/app/item/${e.item_code}">${e.item_name}</a>`);
            $(`#pidr${_i}`).append(`<div class="col grid-static-col col-xs-1 bold" id="pigsc2${_i}"></div>`);
            $(`#pigsc2${_i}`).append(`<div style="text-align: right">1</div>`);
            $(`#pidr${_i}`).append(`<div class="col grid-static-col col-xs-2 bold" id="pigsc3${_i}"></div>`);
            $(`#pigsc3${_i}`).append(`<div style="text-align: right">${frappe.format(e.item_cogs, {"fieldtype":"Currency"})}</div>`);
            $(`#pidr${_i}`).append(`<div class="col grid-static-col col-xs-2 bold" id="pigsc4${_i}"></div>`);
            $(`#pigsc4${_i}`).append(`<div style="text-align: right">${frappe.format(e.item_rate, {"fieldtype":"Currency"})}</div>`);
            $(`#pidr${_i}`).append(`<div class="col grid-static-col col-xs-3 bold" id="pigsc5${_i}"></div>`);
            $(`#pigsc5${_i}`).append(`<div style="text-align: right">${frappe.format(e.item_rate, {"fieldtype":"Currency"})}</div>`);
            prev_idx = e.idx;
            prev_item_group = e.item_group;
          });
        }
      }
    });
  }
});

let hpp = 0;
function processDataWithRate(source, param) {
  // Step 1: Make a temporary array of distinct lv1 from the data filtered by parameter
  const lv1Set = new Set();
  param.forEach(item => {
    const found = source.find(dataItem => dataItem.name === item);
    if (found && found.lv1) {
      lv1Set.add(found.lv1);
    }
  });
  const distinctLv1 = Array.from(lv1Set);

  // Step 2: For each lv1 data, gather its item name and its rate from the data filtered by parameter
  const lv1Data = [];
  distinctLv1.forEach(lv1 => {
    const itemsWithRate = param.reduce((acc, item) => {
      const found = source.find(dataItem => dataItem.name === item);
      if (found && found.lv1 === lv1 && found.item_name && found.rate) {
        acc.push({ item_name: found.item_name, rate: found.rate });
      }
      return acc;
    }, []);
    lv1Data.push({ lv1, items_with_rate: itemsWithRate });
  });

// Step 3: Return an array of objects with lv1 data followed by correlated item names and their rates
  const result = [];
  lv1Data.forEach(item => {
      result.push({ lv1: item.lv1 });
      item.items_with_rate.forEach(itemWithRate => {
          result.push({ item_name: itemWithRate.item_name, rate: itemWithRate.rate });
      });
  });
  let table_html = '<table border="1"><tr><th>Selected Options</th><th>HPP</th></tr>';
  hpp = 0;
  result.forEach(kolom=>{
    table_html += `<tr><td>${kolom.lv1?kolom.lv1:kolom.item_name}</td><td>${kolom.rate?new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR' }).format(kolom.rate):''}</td></tr>`;
    if(kolom.rate) hpp+=kolom.rate
  });
  
  table_html += `<tr><td>Total</td><td>${new Intl.NumberFormat('id-ID', { style: 'currency', currency: 'IDR' }).format(hpp)}</td></tr>`;
  table_html += '</table>';
  return table_html;
};

let allSelectedItems = {};
let selectedItems = []
const setupDynamicSelects = (dialog) => {
  const root = 'Examination';
  let examItemsMap = {};
  let examGroupMap = {};
  let currentItemGroup = '';

  frappe.call({
    method: 'kms.healthcare.get_exam_items',
    args: {
      root: root
    },
    freeze: true,
    callback: (r) => {
      const {exam_items, exam_group} = r.message;
      examItemsMap = exam_items.reduce((acc, item) => {
        acc[item.name] = item;
        return acc;
      }, {});
      examGroupMap = exam_group.reduce((acc, group) => {
        acc[group.name] = group;
        return acc;
      }, {});

      const updateSelectField = (parentGroup, level) =>{
        const options = exam_group
          .filter(item => item.parent_item_group === parentGroup)
          .filter(item => {
            // Check if this group or any of its descendants have items
            const hasItems = (group) => {
              return exam_items.some(item => item.item_group === group.name) ||
                     exam_group.some(childGroup => 
                       childGroup.parent_item_group === group.name && hasItems(childGroup)
                     );
            };
            return hasItems(item);
          })
          .sort((a,b) => a.custom_bundle_position - b.custom_bundle_position)
          .map(item => ({value: item.name, label: item.name}))
        dialog.set_df_property(`level_${level}`, 'options', options);
        dialog.set_df_property(`level_${level}`, 'hidden', 0);
        dialog.fields_dict[`level_${level}`].refresh();
      }
      const setupSelectField = (level) => {
        dialog.fields_dict[`level_${level}`].df.onchange = () => {
          const selectedValue = dialog.get_value(`level_${level}`);
          const selectedItem = exam_group.find(item => item.name === selectedValue);

          for(let i = level+1; i <= 3; i++) {
            dialog.set_df_property(`level_${i}`, 'hidden', 1);
          }
          dialog.set_df_property('selected_items', 'hidden', 1);

          if(selectedItem.is_group === 1 && level <3) {
            updateSelectField(selectedItem.name, level+1);
          } else {
            updateMultiSelect(selectedValue);
          }
          dialog.refresh()
        };
      }
      const updateMultiSelect = (itemGroup) => {
        currentItemGroup = itemGroup;
        const options = exam_items
          .filter(item => item.item_group === itemGroup)
          .sort((a, b) => a.name.localeCompare(b.name))
          .map(item => {
            return {value: item.name, label: item.item_name, checked: allSelectedItems[itemGroup]?.includes(item.name) || false}
          });
        dialog.set_df_property('selected_items', 'options', options);
        dialog.set_df_property('selected_items', 'hidden', 0);
        dialog.fields_dict['selected_items'].refresh();
      }

      const buildHierarchy = () => {
        const hierarchy = {};
        const flattenedData = [];

        const getFullPath = (itemGroup) => {
          const path = [];
          let currentGroup = examGroupMap[itemGroup];
          while (currentGroup && currentGroup.name !== root && currentGroup.parent_item_group !== 'All Item Groups') {
            path.unshift(currentGroup.name);
            currentGroup = examGroupMap[currentGroup.parent_item_group];
          }
          return path;
        };
        console.log(Object.values(allSelectedItems).flat())
        Object.values(allSelectedItems).flat().forEach(itemCode => {
          const item = examItemsMap[itemCode];
          const fullPath = getFullPath(item.item_group);
          console.log(item)
          console.log(fullPath)
          
          let currentLevel = hierarchy;
          console.log(currentLevel)

          fullPath.forEach(group => {
            if (!currentLevel[group]) {
              currentLevel[group] = { items: [], subgroups: {} };
            }
            currentLevel = currentLevel[group].subgroups;
          });
          
          if (!currentLevel[item.item_group]) {
            currentLevel[item.item_group] = { items: [], subgroups: {} };
          }
          currentLevel[item.item_group].items.push(item);
        });

        const addToFlattenedData = (obj, level = 0, path = []) => {
          Object.entries(obj).forEach(([key, value]) => {
            const newPath = [...path, key];
            flattenedData.push({ name: key, level, isGroup: true, path: newPath.join(' > ') });
            
            value.items.forEach(item => {
              flattenedData.push({ 
                name: item.item_name, 
                level: level + 1, 
                isGroup: false, 
                itemCode: item.name,
                path: [...newPath, item.item_name].join(' > ')
              });
            });

            addToFlattenedData(value.subgroups, level + 1, newPath);
          });
        };

        addToFlattenedData(hierarchy);
        return flattenedData;
      };

      const updateSelectedItemsTable = () => {
        const grid = dialog.fields_dict.selected_items_table.grid;
        const flattenedData = buildHierarchy();

        const newData = flattenedData.map(item => ({
          name: '  '.repeat(item.level) + item.name,
          is_group: item.isGroup,
          item_code: item.itemCode || '',
          path: item.path
        }));

        grid.df.data = newData;
        grid.data = grid.df.data;
        grid.refresh();
      };

      // Set up event listener for changes in the MultiCheck field
      dialog.$wrapper.on('change', '[data-fieldname="selected_items"] .checkbox-options input[type="checkbox"]', function () {
        const checkboxes = dialog.$wrapper.find('[data-fieldname="selected_items"] .checkbox-options input[type="checkbox"]');
        selectedItems = [];  // Clear the array and rebuild it based on checked items
        checkboxes.each(function () {
          const value = $(this).attr('data-unit');
          if ($(this).is(':checked')) {
            selectedItems.push(value);
          }
        });
        // Update global allSelectedItems with the current group
        allSelectedItems[currentItemGroup] = selectedItems;
        updateSelectedItemsTable();
      });

      updateSelectField(root, 1);
      setupSelectField(1);
      setupSelectField(2);
      setupSelectField(3);
      // Update the MultiSelect initially to ensure all checkboxes are correctly set
      updateMultiSelect(currentItemGroup);
    },
    error: (r) => {
      console.log(r);
    },
  })
}

const processSelectedItems = (selectedItems) => {
  console.log(selectedItems);
}