# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import json

class ResPartner(models.Model):
    _inherit = 'res.partner'

    platform_id = fields.Char('Platform ID', copy=False)

class AccountPayment(models.Model):
    _inherit = 'account.payment'

    platform_id = fields.Char('Partner Platform ID', copy=False)

    @api.model
    def create(self, vals):
        if 'platform_id' in vals and vals.get('platform_id') and self.env.context.get('import_file'):
            partner_id = self.env['res.partner'].sudo().search([('platform_id', '=', vals.get('platform_id'))], limit=1)
            vals.update({'partner_id': partner_id and partner_id.id})
        return super(AccountPayment, self).create(vals)

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    platform_id = fields.Char('Partner Platform ID', copy=False)

    @api.model_create_multi
    def create(self, vals):
        for val in vals:
            if 'platform_id' in val and val.get('platform_id') and self.env.context.get('import_file'):
                partner_id = self.env['res.partner'].sudo().search([('platform_id', '=', val.get('platform_id'))], limit=1)
                val.update({'partner_id': partner_id and partner_id.id})
        return super(AccountMoveLine, self).create(vals)

class ResPartnerQueue(models.Model):
    _name = 'res.partner.queue'
    _order = 'create_date desc'
    _description = "Customer Queue"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Name')
    state = fields.Selection([('draft', 'Draft'), ('failed', 'Failed'), ('done', 'Done'), ('cancel', 'Cancelled')], tracking=True, default='draft')
    log_ids = fields.One2many('res.partner.log', 'partner_queue_id')
    company_type = fields.Char('Company Type')
    email = fields.Char('Email')
    is_company = fields.Char('Is Company')
    mobile = fields.Char('Mobile')
    phone = fields.Char('Phone')
    property_supplier_payment_term_id = fields.Char('Payment Terms')
    street = fields.Char('Street')
    street2 = fields.Char('Street2')
    vat = fields.Char('VAT')
    website = fields.Char('Website')
    ex_partner_id = fields.Char('Platform ID', readonly=True)
    odoo_record_id = fields.Many2one('res.partner', readonly=True)

    def prepare_partner_data(self):
        return {
            'name': self.name,
            'company_type': self.company_type,
            'ex_partner_id': self.ex_partner_id,
            'email': self.email,
            'is_company': self.is_company,
            'mobile': self.mobile,
            'phone': self.phone,
            'customer_rank': 1,
            'street': self.street,
            'street2': self.street2,
            'vat': self.vat,
            'website': self.website,
            'property_supplier_payment_term_id': int(self.property_supplier_payment_term_id) or False,
        }

    @api.model
    def create(self, vals):
        if 'id' in vals:
            vals.update({'ex_partner_id': vals.get('id')})
        rec=super(ResPartnerQueue, self).create(vals)
        rec.action_run_queue_mannually()
        return rec

    def check_payment_terms(self):
        if self.property_supplier_payment_term_id and not self.env['account.payment.term'].sudo().search([('id', '=', self.property_supplier_payment_term_id)]):
            self.write({'state': 'failed'})
            self.env['res.partner.log'].sudo().create({'partner_queue_id': self.id, 'name': 'Payment Terms does not exist with ID '+self.property_supplier_payment_term_id})
            return False
        return True

    def action_force_done(self):
        """
        Cancels all draft and failed queue lines.
        """
        self.env['res.partner.log'].sudo().create({'partner_queue_id': self.id, 'name': 'Queue is cancelled by ' + self.env.user.name})
        self.write({'state': 'cancel'})

    def action_run_queue_mannually(self):
        partner_data = self.prepare_partner_data()
        partner = self.env['res.partner'].sudo().search([('ex_partner_id', '=', self.ex_partner_id)], limit=1)
        if not partner:
            try:
                if not self.check_payment_terms():
                    return
                partner_id = self.env['res.partner'].sudo().create(partner_data)
                if partner_id:
                    self.write({'odoo_record_id': partner_id, 'state': 'done'})
                    self.odoo_record_id = partner_id.id
            except ValueError as ve:
                self.write({'state': 'failed'})
                self.env['res.partner.log'].sudo().create({'partner_queue_id': self.id, 'name': ve})
        else:
            try:
                if not self.check_payment_terms():
                    return
                partner.sudo().write(partner_data)
                self.write({'odoo_record_id': partner.id, 'state': 'done'})
            except ValueError as ve:
                self.write({'state': 'failed'})
                self.env['res.partner.log'].sudo().create({'partner_queue_id': self.id, 'name': ve})

        return True

    def run_customer_queue(self):
        for queue in self.search([('state', '=', 'draft')]).sorted('id'):
            queue.action_run_queue_mannually()

class ResPartnerLog(models.Model):
    _name = 'res.partner.log'
    _order = 'create_date desc'

    partner_queue_id = fields.Many2one('res.partner.queue')
    name = fields.Char('Description')
