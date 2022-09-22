from odoo import models, fields, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    hidden_menu_ids = fields.Many2many(
        'ir.ui.menu', 'ir_ui_menu_res_users_hidden_rel',
        'user_id', 'menu_id', string='Hidden menus')
    model_ids = fields.Many2many('ir.model', 'ir_model_res_users_hidden_rel', 'user_id', 'model_id', string="Models")

    @api.model
    def create(self, values):
        self.env['ir.ui.menu'].clear_caches()
        return super(ResUsers, self).create(values)

    def write(self, values):
        self.env['ir.ui.menu'].clear_caches()
        return super(ResUsers, self).write(values)
