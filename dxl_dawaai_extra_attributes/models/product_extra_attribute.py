# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class ProductClassification(models.Model):
    _name = 'product.classification'
    _description = "Product Classification"

    name = fields.Char(string="Name", required=True, copy=False,)

class CustomerType(models.Model):
	_name = 'customer.type'

	name = fields.Char(string="Name", copy=False)

class LocationType(models.Model):
	_name = 'location.type'

	name = fields.Char(string="Name", copy=False)
	is_shelving = fields.Boolean('Is Shelving')
