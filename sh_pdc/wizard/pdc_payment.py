# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, AccessError

class Attachment(models.Model):
    _inherit = 'ir.attachment'

    pdc_id = fields.Many2one('pdc.wizard')
    
class PDC_wizard(models.Model):
    _name = "pdc.wizard"
    _description = "PDC Wizard"
    
    def open_attachments(self):
        [action] = self.env.ref('base.action_attachment').read()
        ids = self.env['ir.attachment'].search([('pdc_id','=',self.id)])
        id_list = []
        for pdc_id in ids:
            id_list.append(pdc_id.id)
        action['domain'] = [('id', 'in', id_list)]
        return action
    
    def open_journal_items(self):
        [action] = self.env.ref('account.action_account_moves_all').read()
        ids = self.env['account.move.line'].search([('pdc_id','=',self.id)])
        id_list = []
        for pdc_id in ids:
            id_list.append(pdc_id.id)
        action['domain'] = [('id', 'in', id_list)]
        return action
    
    def open_journal_entry(self):
        [action] = self.env.ref('sh_pdc.sh_pdc_action_move_journal_line').read()
        ids = self.env['account.move'].search([('pdc_id','=',self.id)])
        id_list = []
        for pdc_id in ids:
            id_list.append(pdc_id.id)
        action['domain'] = [('id', 'in', id_list)]
        return action
    
            
    @api.model
    def default_get(self, fields):
        rec = super(PDC_wizard, self).default_get(fields)
        active_ids = self._context.get('active_ids')
        active_model = self._context.get('active_model')

        # Check for selected invoices ids
        if not active_ids or active_model != 'account.move':
            return rec
        invoices = self.env['account.move'].browse(active_ids)
        if invoices:
            invoice = invoices[0]
            if invoice.type in ('out_invoice','out_refund'):
                rec.update({'payment_type':'receive_money'})
            elif invoice.type in ('in_invoice','in_refund'):
                rec.update({'payment_type':'send_money'})
                
            rec.update({'partner_id':invoice.partner_id.id,
                        'payment_amount':invoice.amount_residual,
                        'invoice_id':invoice.id,
                        'due_date':invoice.invoice_date_due,
                        'memo':invoice.name})
        
        return rec
    
    
    name = fields.Char("Name",default='New',readonly=1)
    payment_type = fields.Selection([('receive_money','Receive Money'),('send_money','Send Money')],string="Payment Type",default='receive_money')
    partner_id = fields.Many2one('res.partner',string="Partner")
    payment_amount = fields.Monetary("Payment Amount")
    currency_id = fields.Many2one('res.currency',string="Currency",default=lambda self:self.env.user.company_id.currency_id)
    reference = fields.Char("Cheque Reference")
    journal_id = fields.Many2one('account.journal',string="Payment Journal",domain=[('type','=','bank')],required=1)
    payment_date = fields.Date("Payment Date",default=fields.Date.today(),required=1)
    due_date = fields.Date("Due Date",required=1)
    memo = fields.Char("Memo")
    agent = fields.Char("Agent")
    bank_id = fields.Many2one('res.bank',string="Bank")
    invoice_id = fields.Many2one('account.move',string="Invoice/Bill")
    state = fields.Selection([('draft','Draft'),('registered','Registered'),('returned','Returned'),
                              ('deposited','Deposited'),('bounced','Bounced'),('done','Done'),('cancel','Cancelled')],string="State",default='draft')
    
    attachment_ids = fields.One2many('ir.attachment','pdc_id',string="Attachments")
    
    # Register pdc payment
    def button_register(self):
        self.write({'state':'registered'})
        if self.invoice_id:
            self.invoice_id.sudo().write({'amount_residual_signed':0.0,'amount_residual':0.0})
            self.invoice_id._compute_amount()
#     
    def action_register(self):
        self.check_payment_amount()
        self.write({'state':'registered'})
    
    def check_payment_amount(self):
        if self.payment_amount <= 0.0:
            raise UserError("Amount must be greater than zero!")
        
    def check_pdc_account(self):
        if self.payment_type == 'receive_money':
            if not self.env.user.company_id.pdc_customer:
                raise UserError("Please Set PDC payment account for Customer !")
            else:
                return self.env.user.company_id.pdc_customer.id
            
        else:
            if not self.env.user.company_id.pdc_vendor:
                raise UserError("Please Set PDC payment account for Supplier !")
            else:
                return self.env.user.company_id.pdc_vendor.id
            
    def get_partner_account(self):
        if self.payment_type == 'receive_money':
            return self.partner_id.property_account_receivable_id.id
        else:
            return self.partner_id.property_account_payable_id.id
        
    def action_returned(self):
        self.check_payment_amount()
        self.write({'state':'returned'})
        
    def get_credit_move_line(self,account):
        return   {
                'pdc_id':self.id,
                'partner_id':self.partner_id.id,
                'account_id':account,
                'credit':self.payment_amount,
                'ref':self.memo,
                'date':self.payment_date,
                'date_maturity':self.due_date,
            }
        
    def get_debit_move_line(self,account):
        return {
            'pdc_id':self.id,
            'partner_id':self.partner_id.id,
                'account_id':account,
                'debit':self.payment_amount,
                'ref':self.memo,
                'date':self.payment_date,
                'date_maturity':self.due_date,
            } 
        
    def get_move_vals(self,debit_line,credit_line):
        return {
            'pdc_id':self.id,
            'date':self.payment_date,
                    'journal_id':self.journal_id.id,
                    'partner_id':self.partner_id.id,
                    'ref':self.memo,
                    'line_ids':[(0,0,debit_line),
                                (0,0,credit_line)]
                     }
        
    def action_deposited(self):
        move = self.env['account.move']
        
        self.check_payment_amount() # amount must be positive
        pdc_account = self.check_pdc_account()
        partner_account = self.get_partner_account()
        
        # Create Journal Item
        move_line_vals_debit = {}
        move_line_vals_credit = {}
        if self.payment_type=='receive_money':
            move_line_vals_debit = self.get_debit_move_line(pdc_account)
            move_line_vals_credit = self.get_credit_move_line(partner_account)
        else:
            move_line_vals_debit = self.get_debit_move_line(partner_account)
            move_line_vals_credit = self.get_credit_move_line(pdc_account)
        
        #create move and post it
        move_vals = self.get_move_vals(move_line_vals_debit, move_line_vals_credit)
        move_id = move.create(move_vals)
        move_id.action_post()
        self.write({'state':'deposited'})
        
    def action_bounced(self):
        move = self.env['account.move']
        
        self.check_payment_amount() # amount must be positive
        pdc_account = self.check_pdc_account()
        partner_account = self.get_partner_account()
        
        # Create Journal Item
        move_line_vals_debit = {}
        move_line_vals_credit = {}
        
        if self.payment_type=='receive_money':
            move_line_vals_debit = self.get_debit_move_line(partner_account)
            move_line_vals_credit = self.get_credit_move_line(pdc_account)
        else:
            move_line_vals_debit = self.get_debit_move_line(pdc_account)
            move_line_vals_credit = self.get_credit_move_line(partner_account)
            
        if self.memo:
            move_line_vals_debit.update({'name':'PDC Payment :'+self.memo})
            move_line_vals_credit.update({'name':'PDC Payment :'+self.memo})
        else:
            move_line_vals_debit.update({'name':'PDC Payment'})
            move_line_vals_credit.update({'name':'PDC Payment'})
        #create move and post it
        move_vals = self.get_move_vals(move_line_vals_debit, move_line_vals_credit)
        move_id = move.create(move_vals)
        move_id.action_post()
        
        self.write({'state':'bounced'})
        
    def action_done(self):
        move = self.env['account.move']
        
        self.check_payment_amount() # amount must be positive
        pdc_account = self.check_pdc_account()
        bank_account = self.journal_id.default_debit_account_id.id or self.journal_id.default_credit_account_id.id
        
        # Create Journal Item
        move_line_vals_debit = {}
        move_line_vals_credit = {}
        if self.payment_type=='receive_money':
            move_line_vals_debit = self.get_debit_move_line(bank_account)
            move_line_vals_credit = self.get_credit_move_line(pdc_account)
        else:
            move_line_vals_debit = self.get_debit_move_line(pdc_account)
            move_line_vals_credit = self.get_credit_move_line(bank_account)
        
        if self.memo:
            move_line_vals_debit.update({'name':'PDC Payment :'+self.memo})
            move_line_vals_credit.update({'name':'PDC Payment :'+self.memo})
        else:
            move_line_vals_debit.update({'name':'PDC Payment'})
            move_line_vals_credit.update({'name':'PDC Payment'})
            
        #create move and post it
        move_vals = self.get_move_vals(move_line_vals_debit, move_line_vals_credit)
        move_id = move.create(move_vals)
        move_id.action_post()
        self.write({'state':'done'})
        
    def action_cancel(self):
        self.write({'state':'cancel'})
    
    @api.model
    def create(self, vals):
        if vals.get('payment_type')=='receive_money':
            vals['name'] = self.env['ir.sequence'].next_by_code('pdc.payment.customer')
        elif vals.get('payment_type')=='send_money':
            vals['name'] = self.env['ir.sequence'].next_by_code('pdc.payment.vendor')
                
        return super(PDC_wizard,self).create(vals)