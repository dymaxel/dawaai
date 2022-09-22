# -*- coding: utf-8 -*-
"""
Main Controller.
"""
import logging
from odoo import http
from odoo.http import request
import json

_logger = logging.getLogger("Woo")


class Webhook(http.Controller):

    def push_partner_data(self, data):
        print('DDDDDDDDDDDdd', data)
        line_data = data.get('data')
        for line in line_data:
            line['partner_data'] = json.dumps(line)
            del line['company_type']
            del line['mobile']
            del line['phone']
        vals = {'queue_line_ids': [(0, 0, line) for line in line_data]}
        return request.env['res.partner.queue'].sudo().create(vals)

    @http.route('/odoo_api/import_partner_data', type='json', auth='public', csrf=False)
    def import_partner_data(self, **post):
        data = request.jsonrequest
        record_id = False
        print('DDDDDDDDDDdd', data)
        if data:
            record_id = self.push_partner_data(data).id
        return {"response": record_id}
