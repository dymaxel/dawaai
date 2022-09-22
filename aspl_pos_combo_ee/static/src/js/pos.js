odoo.define('aspl_pos_combo_ee.pos', function (require) {
"use strict";

	var models = require('point_of_sale.models');
	var gui = require('point_of_sale.gui');
	var screens = require('point_of_sale.screens');
	var PopupWidget = require('point_of_sale.popups');

	models.load_fields("product.product", ['is_combo','product_combo_ids']);

	models.PosModel.prototype.models.push({
        model:  'product.combo',
        loaded: function(self,product_combo){
            self.product_combo = product_combo;
        },
    });

	var _super_Order = models.Order.prototype;
	models.Order = models.Order.extend({
		add_product: function(product, options){
        	var self = this;
        	_super_Order.add_product.call(self, product, options);
        	if(product.is_combo && product.product_combo_ids.length > 0 && self.pos.config.enable_combo){
        		self.pos.gui.show_popup('combo_product_popup',{
        			'product':product
        		});
        	}
		},
		build_line_resume: function(){
        	var self = this;
            var resume = {};

            this.orderlines.each(function(line){
                if (line.mp_skip) {
                    return;
                }
                var line_hash = line.get_line_diff_hash();
                var qty  = Number(line.get_quantity());
                var note = line.get_note();
                var product_id = line.get_product().id;

                if (typeof resume[line_hash] === 'undefined') {
                    var combo_info = false;
                    if(line.combo_prod_info && line.combo_prod_info.length > 0){
                        combo_info = line.combo_prod_info;
                    }
                    resume[line_hash] = {
                        qty: qty,
                        note: note,
                        product_id: product_id,
                        product_name_wrapped: line.generate_wrapped_product_name(),
                        combo_info: combo_info || false,
                    };
                } else {
                    resume[line_hash].qty += qty;
                    resume[line_hash].combo_info = combo_info;
                }
            });
            return resume;
        },
        computeChanges: function(categories){
            var current_res = this.build_line_resume();
            var old_res     = this.saved_resume || {};
            var json        = this.export_as_JSON();
            var add = [];
            var rem = [];
            var line_hash;

            for ( line_hash in current_res) {
                var curr = current_res[line_hash];
                var old  = old_res[line_hash];

                if (typeof old === 'undefined') {
                    add.push({
                        'id':       curr.product_id,
                        'name':     this.pos.db.get_product_by_id(curr.product_id).display_name,
                        'name_wrapped': curr.product_name_wrapped,
                        'note':     curr.note,
                        'qty':      curr.qty,
                        'combo_info': curr.combo_info,
                    });
                } else if (old.qty < curr.qty) {
                    add.push({
                        'id':       curr.product_id,
                        'name':     this.pos.db.get_product_by_id(curr.product_id).display_name,
                        'name_wrapped': curr.product_name_wrapped,
                        'note':     curr.note,
                        'qty':      curr.qty - old.qty,
                        'combo_info': curr.combo_info,
                    });
                } else if (old.qty > curr.qty) {
                    rem.push({
                        'id':       curr.product_id,
                        'name':     this.pos.db.get_product_by_id(curr.product_id).display_name,
                        'name_wrapped': curr.product_name_wrapped,
                        'note':     curr.note,
                        'qty':      old.qty - curr.qty,
                        'combo_info': curr.combo_info,
                    });
                }
            }

            for (line_hash in old_res) {
                if (typeof current_res[line_hash] === 'undefined') {
                    var old = old_res[line_hash];
                    if(old){
                    	rem.push({
                            'id':       old.product_id,
                            'name':     this.pos.db.get_product_by_id(old.product_id).display_name,
                            'name_wrapped': old.product_name_wrapped,
                            'note':     old.note,
                            'qty':      old.qty,
                            'combo_info': old.combo_info,
                        });
                    }
                }
            }

            if(categories && categories.length > 0){
                // filter the added and removed orders to only contains
                // products that belong to one of the categories supplied as a parameter

                var self = this;

                var _add = [];
                var _rem = [];

                for(var i = 0; i < add.length; i++){
                    if(self.pos.db.is_product_in_category(categories,add[i].id)){
                        _add.push(add[i]);
                    }
                }
                add = _add;

                for(var i = 0; i < rem.length; i++){
                    if(self.pos.db.is_product_in_category(categories,rem[i].id)){
                        _rem.push(rem[i]);
                    }
                }
                rem = _rem;
            }

            var d = new Date();
            var hours   = '' + d.getHours();
                hours   = hours.length < 2 ? ('0' + hours) : hours;
            var minutes = '' + d.getMinutes();
                minutes = minutes.length < 2 ? ('0' + minutes) : minutes;

            return {
                'new': add,
                'cancelled': rem,
                'table': json.table || false,
                'floor': json.floor || false,
                'name': json.name  || 'unknown order',
                'time': {
                    'hours':   hours,
                    'minutes': minutes,
                },
            };

        },
	});

	var _super_orderline = models.Orderline.prototype;
    models.Orderline = models.Orderline.extend({
    	initialize: function(attr,options){
            this.combo_prod_info = false;
            _super_orderline.initialize.call(this, attr, options);
        },
        init_from_JSON: function(json) {
        	var self = this;
        	_super_orderline.init_from_JSON.apply(this,arguments);
			var new_combo_data = [];
			if(json.combo_ext_line_info && json.combo_ext_line_info.length > 0){
				json.combo_ext_line_info.map(function(combo_data){
					if(combo_data[2].product_id){
						var product = self.pos.db.get_product_by_id(combo_data[2].product_id);
						if(product){
							new_combo_data.push({
								'product':product,
								'price':combo_data[2].price,
								'qty':combo_data[2].qty,
								'id':combo_data[2].id,
							});
						}
					}
				});
			}
			self.set_combo_prod_info(new_combo_data);
        },
        set_combo_prod_info: function(combo_prod_info){
        	this.combo_prod_info = combo_prod_info;
        	this.trigger('change',this);
        },
        get_combo_prod_info: function(){
        	return this.combo_prod_info;
        },
        export_as_JSON: function(){
            var self = this;
            var json = _super_orderline.export_as_JSON.call(this,arguments);
            var combo_ext_line_info = [];
            if(this.product.is_combo && this.combo_prod_info.length > 0){
                _.each(this.combo_prod_info, function(item){
                	combo_ext_line_info.push([0, 0, {
                		'product_id':item.product.id, 
                		'qty':item.qty, 
                		'price':item.price,
                		'id':item.id,
                	}]);
                });
            }
            json.combo_ext_line_info = this.product.is_combo ? combo_ext_line_info : [];
            return json;
        },
        can_be_merged_with: function(orderline){
        	var result = _super_orderline.can_be_merged_with.call(this,orderline);
        	if(orderline.product.id == this.product.id && this.get_combo_prod_info()){
        		return false;
        	}
        	return result;
        },
        export_for_printing: function(){
            var lines = _super_orderline.export_for_printing.call(this);
            lines.combo_prod_info = this.get_combo_prod_info();
            return lines;
        },
    });

// 	var POSComboProductPopup = PopupWidget.extend({
//         template: 'POSComboProductPopup',
//         events: _.extend({}, PopupWidget.prototype.events, {
//     		'click .collaps_div': 'collaps_div',
//     		'click .product.selective_product': 'select_product',
//     	}),
//         show: function(options){
//         	var self = this;
//             this._super(options);
//             this.product = options.product || false;
//             this.combo_product_info = options.combo_product_info || false;
//             var combo_products_details = [];
//             this.new_combo_products_details = [];
//             this.scroll_position = 0;
//             this.product.product_combo_ids.map(function(id){
//             	var record = _.find(self.pos.product_combo, function(data){
//             		return data.id === id;
//             	});
//             	combo_products_details.push(record);
//             });
//             combo_products_details.map(function(combo_line){
//         		var details = [];
//         		if(combo_line.product_ids.length > 0){
//         			combo_line.product_ids.map(function(product_id){
//         				if(combo_line.require){
//         					var data = {
//                         		'no_of_items':combo_line.no_of_items,
//                         		'product_id':product_id,
//                         		'category_id':combo_line.pos_category_id[0] || false,
//                         		'used_time':combo_line.no_of_items,
//                         	}
//             				details.push(data);
//         				}else{
//                             var data = {
//                                 'no_of_items':combo_line.no_of_items,
//                                 'product_id':product_id,
//                                 'category_id':combo_line.pos_category_id[0] || false,
//                                 'used_time':0
//                             }
//                             if(self.combo_product_info){
//                                 self.combo_product_info.map(function(line){
//                                     if(combo_line.id == line.id && line.product.id == product_id){
//                                         data['used_time'] =  line.qty;
//                                     }
//                                 });
//                             }
//                             details.push(data);
//         				}
//         			});
//         			self.new_combo_products_details.push({
//         				'id':combo_line.id,
//         				'no_of_items':combo_line.no_of_items,
//         				'pos_category_id':combo_line.pos_category_id,
//         				'product_details':details,
//         				'product_ids':combo_line.product_ids,
//         				'require':combo_line.require,
//         			});
//         		}
//             });
//             this.renderElement();
//         },
//         collaps_div: function(event){
//         	if($(event.currentTarget).hasClass('fix_products')){
//         		$('.combo_header_body').slideToggle('500');
//         		$(event.currentTarget).find('i').toggleClass('fa-angle-down fa-angle-up');
//         	}else if($(event.currentTarget).hasClass('selective_products')){
//         		$('.combo_header2_body').slideToggle('500');
//         		$(event.currentTarget).find('i').toggleClass('fa-angle-down fa-angle-up');
//         	}
//         },
//         select_product: function(event){
//         	var self = this;
//         	var $el = $(event.currentTarget);
//         	var product_id = Number($el.data('product-id'));
//         	var category_id = Number($el.data('categ-id'));
//         	var line_id = Number($el.data('line-id'));
//         	self.scroll_position = Number(self.$el.find('.combo_header2_body').scrollTop()) || 0;
//         	if($(event.target).hasClass('fa-times') || $(event.target).hasClass('product-remove')){
//         		if($el.hasClass('selected')){
//         			self.new_combo_products_details.map(function(combo_line){
//                 		if(!combo_line.require){
//                 			if(combo_line.id == line_id && combo_line.pos_category_id[0] == category_id && (_.contains(combo_line.product_ids, product_id))){
//                 				combo_line.product_details.map(function(product_detail){
//                 					if(product_detail.product_id == product_id){
//                 						product_detail.used_time = 0;
//                 					}
//                 				});
//                 			}
//                 		}
//                 	});
//             	}
//         	}else{
//             	self.new_combo_products_details.map(function(combo_line){
//             		if(!combo_line.require){
//             			if(combo_line.id == line_id && combo_line.pos_category_id[0] == category_id && (_.contains(combo_line.product_ids, product_id))){
//             				var added_item = 0;
//             				combo_line.product_details.map(function(product_detail){
//             					added_item += product_detail.used_time;
//             				});
//             				combo_line.product_details.map(function(product_detail){
//             					if(product_detail.product_id == product_id){
//             						if(product_detail.no_of_items > product_detail.used_time && product_detail.no_of_items > added_item){
//             							product_detail.used_time += 1;
//             						}
//             					}
//             				});
//             			}
//             		}
//             	});
//         	}
//         	self.renderElement();
//         },
//         click_confirm: function(){
//             var self = this;
//             var order = self.pos.get_order();
// //            var total_amount = 0;
//             var products_info = [];
//             var pricelist = self.pos.gui.screen_instances.products.product_list_widget._get_active_pricelist();
//             self.new_combo_products_details.map(function(combo_line){
//             	if(combo_line.product_details.length > 0){
//             		combo_line.product_details.map(function(prod_detail){
//             			if(prod_detail.used_time){
//             				var product = self.pos.db.get_product_by_id(prod_detail.product_id);
//                 			if(product){
// //                				total_amount = self.product.get_price(pricelist, 1);
//                 				products_info.push({
//                 					"product":product, 
//                 					'qty':prod_detail.used_time,
//                 					'price':product.get_price(pricelist, 1),
//                 					'id':combo_line.id,
//                 				});
//                 			}
//             			}
//             		});
//             	}
//             });
//             var selected_line = order.get_selected_orderline();
//             if(products_info.length > 0){
//             	if(selected_line){
// //            		selected_line.set_unit_price(total_amount);
//             		selected_line.set_combo_prod_info(products_info);
//             		// Code Change for Print Combo in Kitchen Screen
//             		var combo_order_line = selected_line;
//             		order.remove_orderline(selected_line);
//             		var combo_product = self.pos.db.get_product_by_id(Number(combo_order_line.product.id));
//                     order.add_product(combo_product, {
//                         quantity: combo_order_line.quantity,
//                     });
//                     var new_line = order.get_selected_orderline();
//                     new_line.set_combo_prod_info(combo_order_line.combo_prod_info);
//             	}else{
//             		alert("Selected line not found!");
//             	}
//             }else{
//             	if(selected_line && !selected_line.get_combo_prod_info()){
//             		order.remove_orderline(selected_line);
//             	}
//             }
//             self.gui.close_popup();
//         },
//         click_cancel: function(){
//         	var order = this.pos.get_order();
//         	var selected_line = order.get_selected_orderline();
//         	if(selected_line && !selected_line.get_combo_prod_info()){
//         		order.remove_orderline(selected_line);
//         	}
//         	this.gui.close_popup();
//         },
//         renderElement: function(){
//         	this._super();
//         	this.$el.find('.combo_header2_body').scrollTop(this.scroll_position);
//         },
//     });
//     gui.define_popup({name:'combo_product_popup', widget: POSComboProductPopup});

    var POSComboProductPopup = PopupWidget.extend({
        template: 'POSComboProductPopup',
        events: _.extend({}, PopupWidget.prototype.events, {
            'click .collaps_div': 'collaps_div',
            'click .product.selective_product': 'select_product',
        }),
        show: function(options){
            var self = this;
            this._super(options);
            this.product = options.product || false;
            this.combo_product_info = options.combo_product_info || false;
            var combo_products_details = [];
            this.new_combo_products_details = [];
            this.scroll_position = 0;
            this.display_item = 0;
            this.selected_product_qty = [];
            this.product.product_combo_ids.map(function(id){
                var record = _.find(self.pos.product_combo, function(data){
                    return data.id === id;
                });
                combo_products_details.push(record);
            });
            combo_products_details.map(function(combo_line){
                var details = [];
                if(combo_line.product_ids.length > 0){
                    combo_line.product_ids.map(function(product_id){
                        if(combo_line.require){
                            var data = {
                                'no_of_items':combo_line.no_of_items,
                                'product_id':product_id,
                                'category_id':combo_line.category_id[0] || false,
                                'used_time':combo_line.no_of_items,
                            }
                            details.push(data);
                        }else{
                            var data = {
                                'no_of_items':combo_line.no_of_items,
                                'product_id':product_id,
                                'category_id':combo_line.category_id[0] || false,
                                'used_time':0
                            }
                            if(self.combo_product_info){
                                self.combo_product_info.map(function(line){
                                    if(combo_line.id == line.id && line.product.id == product_id){
                                        data['used_time'] =  line.qty;
                                        self.display_item += line.qty;
                                    }
                                });
                            }
                            details.push(data);
                        }
                    });
                    self.new_combo_products_details.push({
                        'id':combo_line.id,
                        'no_of_items':combo_line.no_of_items,
                        'category_id':combo_line.category_id,
                        'product_details':details,
                        'product_ids':combo_line.product_ids,
                        'require':combo_line.require,                        
                    });
                }
            });
            this.new_combo_products_details.map(function(combo_line){
                var total_qty = 0
                combo_line.product_details.map(function(product_detail){
                    total_qty += product_detail.used_time
                }); 
                combo_line['display_item'] = total_qty
            });
            this.renderElement();
        },
        collaps_div: function(event){
            if($(event.currentTarget).hasClass('fix_products')){
                $('.combo_header_body').slideToggle('500');
                $(event.currentTarget).find('i').toggleClass('fa-angle-down fa-angle-up');
            }else if($(event.currentTarget).hasClass('selective_products')){
                $('.combo_header2_body').slideToggle('500');
                $(event.currentTarget).find('i').toggleClass('fa-angle-down fa-angle-up');
            }
        },
        select_product: function(event){
            var self = this;
            var $el = $(event.currentTarget);
            var product_id = Number($el.data('product-id'));
            var category_id = Number($el.data('categ-id'));
            var line_id = Number($el.data('line-id'));
            self.scroll_position = Number(self.$el.find('.combo_header2_body').scrollTop()) || 0;
            if($(event.target).hasClass('fa-times') || $(event.target).hasClass('product-remove')){
                if($el.hasClass('selected')){
                    self.new_combo_products_details.map(function(combo_line){
                        if(!combo_line.require){
                            if(combo_line.id == line_id && combo_line.category_id[0] == category_id && (_.contains(combo_line.product_ids, product_id))){
                                combo_line.product_details.map(function(product_detail){
                                    if(product_detail.product_id == product_id){
                                        combo_line['display_item'] = combo_line['display_item'] - product_detail.used_time
                                        product_detail.used_time = 0;
                                    }
                                });
                            }
                        }
                    });
                }
            }else{
                self.new_combo_products_details.map(function(combo_line){
                    if(!combo_line.require){
                        if(combo_line.id == line_id && combo_line.category_id[0] == category_id && (_.contains(combo_line.product_ids, product_id))){
                            var added_item = 0;
                            combo_line.product_details.map(function(product_detail){
                                added_item += product_detail.used_time;
                            });
                            combo_line.product_details.map(function(product_detail){
                                if(product_detail.product_id == product_id){
                                    if(product_detail.no_of_items > product_detail.used_time && product_detail.no_of_items > added_item){                                        
                                        combo_line['display_item'] = added_item + 1;                                        
                                        product_detail.used_time += 1;                                        
                                    }
                                }
                            });
                        }
                    }
                    self.selected_product_qty.push(combo_line)
                });
            }
            self.renderElement();
        },
        click_confirm: function(){
            var self = this;
            var order = self.pos.get_order();
//            var total_amount = 0;
            var products_info = [];
            var pricelist = self.pos.gui.screen_instances.products.product_list_widget._get_active_pricelist();
            self.new_combo_products_details.map(function(combo_line){
                if(combo_line.product_details.length > 0){
                    combo_line.product_details.map(function(prod_detail){
                        if(prod_detail.used_time){
                            var product = self.pos.db.get_product_by_id(prod_detail.product_id);
                            if(product){
//                              total_amount = self.product.get_price(pricelist, 1);
                                products_info.push({
                                    "product":product, 
                                    'qty':prod_detail.used_time,
                                    'price':product.get_price(pricelist, 1),
                                    'id':combo_line.id,
                                });
                            }
                        }
                    });
                }
            });
            var selected_line = order.get_selected_orderline();
            if(products_info.length > 0){
                if(selected_line){
//                  selected_line.set_unit_price(total_amount);
                    selected_line.set_combo_prod_info(products_info);
                    // Code Change for Print Combo in Kitchen Screen
                    var combo_order_line = selected_line;
                    order.remove_orderline(selected_line);
                    var combo_product = self.pos.db.get_product_by_id(Number(combo_order_line.product.id));
                    order.add_product(combo_product, {
                        quantity: combo_order_line.quantity,
                    });
                    var new_line = order.get_selected_orderline();
                    new_line.set_combo_prod_info(combo_order_line.combo_prod_info);
                }else{
                    alert("Selected line not found!");
                }
            }else{
                if(selected_line && !selected_line.get_combo_prod_info()){
                    order.remove_orderline(selected_line);
                }
            }
            self.gui.close_popup();
        },
        click_cancel: function(){
            var order = this.pos.get_order();
            var selected_line = order.get_selected_orderline();
            if(selected_line && !selected_line.get_combo_prod_info()){
                order.remove_orderline(selected_line);
            }
            this.gui.close_popup();
        },
        renderElement: function(){
            this._super();
            this.$el.find('.combo_header2_body').scrollTop(this.scroll_position);
        },
    });
    gui.define_popup({name:'combo_product_popup', widget: POSComboProductPopup});

    screens.OrderWidget.include({
        render_orderline: function(orderline){
            var self = this;
            var el_node = this._super(orderline);
            var el_combo_icon = el_node.querySelector(' .combo-popup-icon');
            if(el_combo_icon){
                el_combo_icon.addEventListener('click',(function(){
                    var product = orderline.get_product();
                    if(product.is_combo && product.product_combo_ids.length > 0 && self.pos.config.enable_combo){
                        self.pos.gui.show_popup('combo_product_popup',{
                            'product':product,
                            'combo_product_info': orderline.get_combo_prod_info(),
                        });
                    }
                }.bind(this)));
            }
            if(self.pos.config.edit_combo){
                if(el_node){
                    el_node.addEventListener('click',(function(){
                        var product = orderline.get_product();
                        if(product.is_combo && product.product_combo_ids.length > 0 && self.pos.config.enable_combo){
                            self.pos.gui.show_popup('combo_product_popup',{
                                'product':product,
                                'combo_product_info': orderline.get_combo_prod_info(),
                            });
                        }
                    }.bind(this)));
                }
            }
            return el_node;
        },
    });

});