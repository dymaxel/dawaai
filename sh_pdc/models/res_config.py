# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import api, fields, models, _

class ResCompany(models.Model):
    _inherit = 'res.company'

    pdc_customer = fields.Many2one('account.account',string="PDC Account for customer")
    
    pdc_vendor = fields.Many2one('account.account',string="PDC Account for Vendor")
    

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    pdc_customer = fields.Many2one('account.account',string="PDC Account for customer",
                                             related='company_id.pdc_customer',readonly=False)
    
    pdc_vendor = fields.Many2one('account.account',string="PDC Account for Vendor",
                                             related='company_id.pdc_vendor',readonly=False)
    