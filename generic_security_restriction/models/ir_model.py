from odoo import api, models, fields
from odoo.models import BaseModel


class IrModel(models.Model):
    _inherit = 'ir.model'

    field_security_ids = fields.One2many(
        'generic.security.restriction.field', 'model_id',
        index=True, string='Security Fields')

class BaseModel(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def check_access_rights(self, operation, raise_exception=True):
        if operation in ('create', 'write') and self._name in self.env.user.model_ids.mapped('model'):
            return False
        return self.env['ir.model.access'].check(self._name, operation, raise_exception)
