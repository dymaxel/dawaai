from odoo import api, fields, models

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    class_id = fields.Many2one('product.classification', string="Product Classification")
    sku = fields.Char('SKU', copy=False)
    expiry_validation = fields.Integer('Expiry Validation', copy=False)
    pack_size = fields.Char('Pack Size', copy=False)
    strip_size = fields.Char('Strip Size', copy=False)

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    customer_type = fields.Many2one('customer.type', string="Order Type", copy=False)

class StockLocation(models.Model):
    _inherit = 'stock.location'

    location_type = fields.Many2one('location.type', string="Location Type", copy=False)

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    hide_check_availability = fields.Boolean(compute='_compute_hide_check_availability')

    def _compute_hide_check_availability(self):
        for picking in self:
            if picking.picking_type_id.code == 'internal' and picking.location_id.location_type.is_shelving:
                picking.hide_check_availability = True
            else:
                picking.hide_check_availability = False
