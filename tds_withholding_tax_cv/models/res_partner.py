# -*- coding: utf-8 -*-
# This module and its content is copyright of Technaureus Info Solutions Pvt. Ltd.
# - © Technaureus Info Solutions Pvt. Ltd 2020. All rights reserved.

from odoo import fields, models, _

class ResPartner(models.Model):
    _inherit = 'res.partner'
    
    tds_threshold_check = fields.Boolean(string='Check TDS Threshold', default=False)
    wht_id = fields.Many2one('account.tax', copy=False)
