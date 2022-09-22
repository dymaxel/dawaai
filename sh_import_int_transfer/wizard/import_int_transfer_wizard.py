# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, AccessError
import datetime
import csv
import base64
import io as StringIO
import xlrd
from odoo.tools import ustr


class import_int_transfer_wizard(models.TransientModel):
    _name = "import.int.transfer.wizard"
    _description = "Import Internal Transfer Wizard"       
    
    @api.model
    def _default_schedule_date(self):
        return datetime.datetime.now()

    def _get_picking_type(self):
        warehouse = self.env['stock.warehouse'].search([
                ('company_id', '=', self.env.user.company_id.id)
            ], limit=1)
        if warehouse:
            picking_type = self.env['stock.picking.type'].search([
                ('code', '=', 'internal'),
                ('warehouse_id', '=', warehouse.id)
                ], limit=1)
            return picking_type
        return False

    @api.model
    def _default_location_id(self):
        company_user = self.env.user.company_id
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', company_user.id)], limit=1)
        if warehouse:
            return warehouse.lot_stock_id.id
        else:
            raise UserError(_('You must define a warehouse for the company: %s.') % (company_user.name,))     
        
    scheduled_date = fields.Datetime(string="Scheduled Date", default=_default_schedule_date, required=True)
    location_id = fields.Many2one(
        'stock.location', "Source Location",
        required=True,
        default=_default_location_id)
    
    location_dest_id = fields.Many2one(
        'stock.location', "Destination Location",
        required=True,
        default=_default_location_id)
    
    product_by = fields.Selection([
        ('name', 'Name'),
        ('int_ref', 'Internal Reference'),
        ('barcode', 'Barcode')
        ], default="name", string="Product By", required=True) 
        
    file = fields.Binary(string="File", required=True)
    picking_type_id = fields.Many2one('stock.picking.type', default=_get_picking_type, required=True, domain="[('code', '=', 'internal')]")

    import_type = fields.Selection([
        ('csv', 'CSV File'),
        ('excel', 'Excel File')
        ], default="csv", string="Import File Type", required=True)

    @api.onchange('picking_type_id')
    def _onchnage_picking_type_id(self):
        if self.picking_type_id:
            self.location_id = self.picking_type_id.default_location_src_id.id
            self.location_dest_id = self.picking_type_id.default_location_dest_id.id

    def show_success_msg(self, counter, skipped_line_no):
        
        # to close the current active wizard        
        action = self.env.ref('sh_import_int_transfer.sh_import_int_transfer_action').read()[0]
        action = {'type': 'ir.actions.act_window_close'} 
        
        # open the new success message box    
        view = self.env.ref('sh_message.sh_message_wizard')
        view_id = view and view.id or False                                   
        context = dict(self._context or {})
        dic_msg = str(counter) + " Records imported successfully"
        if skipped_line_no:
            dic_msg = dic_msg + "\nNote:"
        for k, v in skipped_line_no.items():
            dic_msg = dic_msg + "\nRow No " + k + " " + v + " "
        context['message'] = dic_msg            
        
        return {
            'name': 'Success',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'sh.message.wizard',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'context': context,
            }   
    
    def import_int_transfer_apply(self):
        stock_picking_obj = self.env['stock.picking'].sudo()
        stock_move_obj = self.env['stock.move']
        # perform import lead
        if self and self.file and self.location_id and self.location_dest_id and self.scheduled_date:
            # For CSV
            field_nm = 'name'
            if self.product_by == 'name':
                field_nm = 'name'
            elif self.product_by == 'int_ref':
                field_nm = 'default_code'
            elif self.product_by == 'barcode':
                field_nm = 'barcode'

            if self.import_type == 'csv':
                counter = 1
                skipped_line_no = {}
                try:
                    file = str(base64.decodestring(self.file).decode('utf-8'))
                    myreader = csv.reader(file.splitlines()) 
                    skip_header = True   
                    skip_header1 = True
                    created_picking = False
                    
                    picking_vals = {}
                    if self.picking_type_id:
                        picking_vals.update({
                                'picking_type_code' : 'internal',
                                'location_id'       : self.location_id.id,
                                'location_dest_id'  : self.location_dest_id.id,
                                'scheduled_date'    : self.scheduled_date,
                                'picking_type_id'   : self.picking_type_id.id                         
                            })

                    is_all_valid = True
                    csv_data = []
                    for t_row in myreader:
                        if skip_header1:
                            skip_header1 = False
                            continue
                        csv_data.append({
                            'product_id': t_row[0],
                            'qty': t_row[1],
                            'uom': t_row[2],
                        })

                    for d in csv_data:
                        t_search_product = self.env['product.product'].search([(field_nm, '=', d['product_id'])], limit=1)
                        t_search_uom = self.env['uom.uom'].search([('name', '=', d['uom'])], limit=1)
                        if t_row != 0 and (not self.picking_type_id or not t_search_uom or not t_search_product or not t_search_product.type in ['product', 'consu']):
                            is_all_valid = False
                            break

                    if is_all_valid:
                        created_picking = stock_picking_obj.create(picking_vals)
       
                    for row in csv_data:
                        try:
                            if skip_header:
                                skip_header = False
                                counter = counter + 1

                            if row['product_id'] not in (None, ""): 
                                vals = {}
                                 
                                search_product = self.env['product.product'].search([(field_nm, '=', row['product_id'])], limit=1)
                                if search_product and search_product.type in ['product', 'consu']:
                                    search_uom = False
                                    vals.update({'product_id' : search_product.id})
                                    vals.update({'name' : search_product.name})                                     
                                    if row['qty'] not in (None, ""):
                                        vals.update({'product_uom_qty' : row['qty'] })
                                    else:
                                        vals.update({'product_uom_qty' : 0.0 })                                        
                                    if row['uom'].strip() not in (None, ""):
                                        search_uom = self.env['uom.uom'].search([('name', '=', row['uom'].strip())], limit=1)
                                        if search_uom:
                                            vals.update({'product_uom' : search_uom.id }) 
                                        else:
                                            skipped_line_no[str(counter)] = " - Unit of Measure not found. "                                         
                                            counter = counter + 1
                                            continue                                        
                                    elif search_product.uom_id:
                                        vals.update({'product_uom' : search_product.uom_id.id })                                         
                                    else:
                                        skipped_line_no[str(counter)] = " - Unit of Measure not defined for this product. "                                         
                                        counter = counter + 1
                                        continue                                               
                                    if created_picking:
                                        vals.update({
                                            'location_id'      : created_picking.location_id.id,
                                            'location_dest_id' : created_picking.location_dest_id.id,
                                            'picking_id'       : created_picking.id,
                                            'date_expected'    : created_picking.scheduled_date
                                        })
                                        created_stock_move = stock_move_obj.create(vals)
                                        if created_stock_move:
                                            created_stock_move.onchange_product_id()
                                            if search_uom:
                                                created_stock_move.write({'product_uom' : search_uom.id})
    
                                    else:
                                        skipped_line_no[str(counter)] = " - Internal Transfer Could not be created. "                                         
                                        counter = counter + 1
                                        continue    
                                         
                                    counter = counter + 1 
                                else:
                                    skipped_line_no[str(counter)] = " - Product not found or it's not a Stockable or Consumable Product. " 
                                    counter = counter + 1 
                                    continue                            
                            else:
                                skipped_line_no[str(counter)] = " - Product is empty. "  
                                counter = counter + 1      
                         
                        except Exception as e:
                            skipped_line_no[str(counter)] = " - Value is not valid " + ustr(e)   
                            counter = counter + 1 
                            continue          
                 
                except Exception as e:
                    raise UserError(_("Sorry, Your csv file does not match with our format " + ustr(e)))
                  
                if counter > 1:
                    completed_records = (counter - len(skipped_line_no)) - 2
                    res = self.show_success_msg(completed_records, skipped_line_no)
                    return res                
            
            # For Excel
            if self.import_type == 'excel':
                counter = 1
                skipped_line_no = {}                  
                try:
                    wb = xlrd.open_workbook(file_contents=base64.decodestring(self.file))
                    sheet = wb.sheet_by_index(0)     
                    skip_header = True   
                    created_picking = False
                    
                    picking_vals = {}
                    if self.picking_type_id:
                        picking_vals.update({
                            'picking_type_code' : 'internal',
                            'location_id'       : self.location_id.id,
                            'location_dest_id'  : self.location_dest_id.id,
                            'scheduled_date'    : self.scheduled_date,
                            'picking_type_id'   : self.picking_type_id.id                         
                        })

                    is_all_valid = True
                    for t_row in range(sheet.nrows):
                        t_search_product = self.env['product.product'].search([(field_nm, '=', sheet.cell(t_row, 0).value)], limit=1)
                        t_search_uom = self.env['uom.uom'].search([('name', '=', sheet.cell(t_row, 2).value.strip())], limit=1)
                        if t_row != 0 and (not self.picking_type_id or not t_search_uom or not t_search_product or not t_search_product.type in ['product', 'consu']):
                            is_all_valid = False
                            break

                    if is_all_valid:
                        created_picking = stock_picking_obj.create(picking_vals)

                    for row in range(sheet.nrows):
                        try: 
                            if skip_header:
                                skip_header = False
                                counter = counter + 1
                                continue
                             
                            if sheet.cell(row, 0).value not in (None, ""): 
                                vals = {}
                                 
                                search_product = self.env['product.product'].search([(field_nm, '=', sheet.cell(row, 0).value)], limit=1)
                                if search_product and search_product.type in ['product', 'consu']:
                                    search_uom = False
                                    vals.update({'product_id' : search_product.id})
                                    vals.update({'name' : search_product.name})                                     
                                    if sheet.cell(row, 1).value not in (None, ""):
                                        vals.update({'product_uom_qty' : sheet.cell(row, 1).value })
                                    else:
                                        vals.update({'product_uom_qty' : 0.0 })                                        
                                         
                                    if sheet.cell(row, 2).value.strip() not in (None, ""):
                                        search_uom = self.env['uom.uom'].search([('name', '=', sheet.cell(row, 2).value.strip())], limit=1)
                                        if search_uom:
                                            vals.update({'product_uom' : search_uom.id }) 
                                        else:
                                            skipped_line_no[str(counter)] = " - Unit of Measure not found. "                                         
                                            counter = counter + 1
                                            continue                                        
                                    elif search_product.uom_id:
                                        vals.update({'product_uom' : search_product.uom_id.id })                                         
                                    else:
                                        skipped_line_no[str(counter)] = " - Unit of Measure not defined for this product. "                                         
                                        counter = counter + 1
                                        continue                                               
                                     
                                    if created_picking:
                                        vals.update({
                                            'location_id'      : created_picking.location_id.id,
                                            'location_dest_id' : created_picking.location_dest_id.id,
                                            'picking_id'       : created_picking.id,
                                            'date_expected'    : created_picking.scheduled_date
                                        })
                                        created_stock_move = stock_move_obj.create(vals)
                                        if created_stock_move:
                                            created_stock_move.onchange_product_id()
                                            if search_uom:
                                                created_stock_move.write({'product_uom' : search_uom.id})
    
                                    else:
                                        skipped_line_no[str(counter)] = " - Internal Transfer Could not be created. "                                         
                                        counter = counter + 1
                                        continue    
                                         
                                    counter = counter + 1 
                                else:
                                    skipped_line_no[str(counter)] = " - Product not found or it's not a Stockable or Consumable Product. " 
                                    counter = counter + 1 
                                    continue                            
                            else:
                                skipped_line_no[str(counter)] = " - Product is empty. "  
                                counter = counter + 1      
                         
                        except Exception as e:
                            skipped_line_no[str(counter)] = " - Value is not valid " + ustr(e)   
                            counter = counter + 1 
                            continue          

                except Exception as e:
                    raise UserError(_("Sorry, Your excel file does not match with our format " + ustr(e)))
                  
                if counter > 1:
                    completed_records = (counter - len(skipped_line_no)) - 2
                    res = self.show_success_msg(completed_records, skipped_line_no)
                    return res
