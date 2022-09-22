odoo.define('aspl_sale_combo_ee.ListController', function (require) {
"use strict";

var core = require('web.core');
var ListRenderer = require('web.ListRenderer');
var Dialog = require('web.Dialog');
var viewUtils = require('web.viewUtils');
var rpc = require('web.rpc')
var QWeb = core.qweb;
var Widget = require('web.Widget');
var _t = core._t;
var select_product_ids = {}
var select_combo_categ={}


ListRenderer.include({
        init: function (parent, state, params) {
            var self = this;
            this._super.apply(this, arguments);
        },

        _onRowClicked: function (event) {
            if($(event.target).hasClass('combo') || $(event.target).parent().hasClass('combo')){
            }
            else{
                if (!$(event.target).prop('special_click') && !this.isEditable()) {
                   var id = $(event.currentTarget).data('id');
                   if (id) {
                       this.trigger_up('open_record', { id: id, target: event.target });
                   }
                }
            }
        },

        _renderButton: function(record, node){
            var state = this._super.apply(this, arguments);
            if (this.state.model && this.state.model == 'sale.order.line'){
                var $button = viewUtils.renderButtonFromNode(node,
                {
                    extraClass: node.attrs.icon ? 'combo' : undefined,
                    textAsTitle: !!node.attrs.icon,
                });
                this._handleAttributes($button, node);
            this._registerModifiers(node, record, $button);

            $button.on("click .combo", function (e) {
                console.log ("\n \norder_line", record.data)
                if (record.data.product_id && record.data.is_combo){
                    var combo_seq = record.data.combo_product_sequence
                    var result = rpc.query({
                        model:'sale.order.line',
                        method: 'execute',
                        args: [{'res_id': record.data.product_id.data.id, 'sale_order_line': record.data.combo_product_sequence}]
                        }).then(function (result){
                            console.log ("\n \nresult", result)
                            if (result.categ){
                                select_product_ids = result.categ[0]
                                select_combo_categ = result.categ[0]
                                console.log ("\n \n1select_combo_categ", select_combo_categ)
                                console.log ("\n \n1select_product_ids", select_product_ids)
                            }
                            if (!result.categ){
                                for(var i=0; i<result.keys.length; i++){
                                    var name=result.keys[i]
                                    select_combo_categ[name]=[]
                                    select_product_ids[name]=[]
                                    for(var k=0; k<result.optional[name].length;k++)
                                    {
                                        if (result.optional[name][k].includes('selected')){
                                            select_combo_categ[name].push(result.optional[name][k][0])
                                            select_product_ids[name].push(result.optional[name][k][0])
                                        }
//                                        select_combo_categ[name]=[]
//                                        select_product_ids[name]=[]
                                    }
                                    console.log ("\n \n2select_combo_categ", select_combo_categ)
                                    console.log ("\n \n2select_product_ids", select_product_ids)
                                }
                            }
                            if (result.optional){
                                for(var i=0; i<result.keys.length; i++){
                                    var name=result.keys[i]
                                    for(var k=0; k<result.optional[name].length;k++)
                                    {
                                        result.optional[name][k].push(window.location.origin + '/web/image?model=product.product&field=image_medium&id='+result.optional[name][k][0])
                                    }
                                }
                            }
                            if (result.required){
                                for (var i=0; i<result.required.length; i++){
                                    if (!select_product_ids['required']){
                                        select_product_ids['required'] = [result.required[i][0]]
                                    }
                                    else{
                                        if (!select_product_ids['required'].includes(result.required[i][0])){
                                            select_product_ids['required'].push(result.required[i][0])
                                        }
                                    }
                                }
                                for(var j=0; j<result.required.length; j++){
                                    result.required[j].push(window.location.origin + '/web/image?model=product.product&field=image_medium&id='+result.required[j][0])
                                }
                            }
                            var dialog=new Dialog(this, {
                                title: "Combo Products",
                                size: 'medium',
                                dialogClass: 'combo_dailog',
                                $content:QWeb.render('sale_combo_image', {
                                    src: result
                                }),
                                buttons: [{
                                    text:'Confirm',
                                    classes : "btn-primary",
                                    click: function () {
                                        var params = {
                                            model: 'sale.order.line',
                                            method: 'combo_product',
                                            args: [{'combo_product': select_product_ids, 'combo_sequence': combo_seq, 'order_line': record.data.id}],
                                        }
                                        rpc.query(params, {async: false}).then(function(result){});
//                                        if (record.data.id){
//                                            setTimeout(function () {
//                                                location.reload();
//                                            });
//                                        }
                                    },
                                    close:true,
                                }, {
                                    text: ("Cancel"),
                                    close: true,
                                }],
                            });
                            dialog.opened().then(function () {
                                console.log("\n \norder_line123456", record)
                                dialog.$('.product_remove').on('click', function (event) {
                                    if (result.categ){
                                        var category = $(event.currentTarget).parent().find('span').data('categ-id')
                                        result[category] = result[category] - 1
                                    }
                                    $(event.currentTarget).next().removeClass('selected')
                                    var removeItem = $(event.currentTarget).next().find('span').data('product-id');
                                    var select_product_id = select_product_ids[$(event.currentTarget).next().find('span').data('categ-id')].includes($(event.currentTarget).next().find('span').data('product-id'))
                                    var combo_select = select_combo_categ[$(event.currentTarget).next().find('span').data('categ-id')].includes($(event.currentTarget).next().find('span').data('product-id'))
                                    if (select_product_id){
                                        select_product_ids[$(event.currentTarget).next().find('span').data('categ-id')] = jQuery.grep(select_product_ids[$(event.currentTarget).next().find('span').data('categ-id')], function(value) {
                                            return value != removeItem;
                                        });
                                    }
                                    if (combo_select){
                                        select_combo_categ[$(event.currentTarget).next().find('span').data('categ-id')] = jQuery.grep(select_combo_categ[$(event.currentTarget).next().find('span').data('categ-id')], function(value) {
                                            return value != removeItem;
                                        });
                                    }
                                });

                                dialog.$('.column').on('click', function (event) {
                                    if (result.categ){
                                        var categ_name = $(event.currentTarget).find('span').data('categ-id')
                                        if (result[categ_name] < $(event.currentTarget).find('span').data('categ-name')){
                                            result[categ_name] = result[categ_name] + 1
                                            $(event.currentTarget).addClass('selected');
                                            var product_id = select_product_ids[categ_name].includes($(event.currentTarget).find('span').data('product-id'))
                                            if (!product_id){
                                                select_product_ids[$(event.currentTarget).find('span').data('categ-id')].push($(event.currentTarget).find('span').data('product-id'))
                                                select_combo_categ[$(event.currentTarget).find('span').data('categ-id')].push($(event.currentTarget).find('span').data('product-id'))
                                            }
                                        }
                                    }
                                    if (!result.categ){
                                        if (select_combo_categ[$(event.currentTarget).find('span').data('categ-id')].length + 1 <= $(event.currentTarget).find('span').data('categ-name')){
                                            $(event.currentTarget).addClass('selected');
                                            var product_id = select_product_ids[$(event.currentTarget).find('span').data('categ-id')].includes($(event.currentTarget).find('span').data('product-id'))
                                            if (!product_id){
                                                select_product_ids[$(event.currentTarget).find('span').data('categ-id')].push($(event.currentTarget).find('span').data('product-id'))
                                                select_combo_categ[$(event.currentTarget).find('span').data('categ-id')].push($(event.currentTarget).find('span').data('product-id'))
                                            }
                                        }
                                    }
                                });

                                dialog.$('.collaps_div').on('click',function(event){
                                    if($(event.currentTarget).hasClass('fix_products')){
                                        $('.row1').slideToggle('500');
                                        $(event.currentTarget).find('i').toggleClass('fa-angle-down fa-angle-up');
                                    }else if($(event.currentTarget).hasClass('selective_products')){
                                        $('.row').slideToggle('500');
                                        $(event.currentTarget).find('i').toggleClass('fa-angle-down fa-angle-up');
                                    }
                                })
                            });
                            dialog.open();
                        });

                    }
                    else{
                        alert("Please Save the Order Line first")
                    }
                    });
                return $button;
            }
            return state;
        },
    });
});
