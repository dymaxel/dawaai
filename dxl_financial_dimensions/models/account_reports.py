# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class AccountReport(models.AbstractModel):
    _inherit = 'account.report'

    @api.model
    def _init_filter_analytic(self, options, previous_options=None):
        options['user_bu'] = self.env.user.bu.ids or []
        if self.user_has_groups('analytic.group_analytic_accounting'):
            # BU
            options['bu'] = previous_options and previous_options.get('bu') or []
            selected_bu = [int(bu) for bu in options['bu']]
            selected_bu = selected_bu and self.env['account.analytic.group'].browse(selected_bu) or self.env['account.analytic.group']
            options['selected_bu'] = selected_bu.mapped('name')

            # Mode of Business
            options['mob'] = previous_options and previous_options.get('mob') or []
            selected_mob = [int(mob) for mob in options['mob']]
            selected_mob = selected_mob and self.env['account.analytic.group'].browse(selected_mob) or self.env['account.analytic.group']
            options['selected_mob'] = selected_mob.mapped('name')

            # Type of Customer
            options['toc'] = previous_options and previous_options.get('toc') or []
            selected_toc = [int(toc) for toc in options['toc']]
            selected_toc = selected_toc and self.env['account.analytic.group'].browse(selected_toc) or self.env['account.analytic.group']
            options['selected_toc'] = selected_toc.mapped('name')

            # Product Category
            options['pc'] = previous_options and previous_options.get('pc') or []
            selected_pc = [int(pc) for pc in options['pc']]
            selected_pc = selected_pc and self.env['account.analytic.group'].browse(selected_pc) or self.env['account.analytic.group']
            options['selected_pc'] = selected_pc.mapped('name')

            # Location
            options['loc'] = previous_options and previous_options.get('loc') or []
            selected_loc = [int(loc) for loc in options['loc']]
            selected_loc = selected_loc and self.env['account.analytic.group'].browse(selected_loc) or self.env['account.analytic.group']
            options['selected_loc'] = selected_loc.mapped('name')

            # Function
            options['fun'] = previous_options and previous_options.get('fun') or []
            selected_fun = [int(fun) for fun in options['fun']]
            selected_fun = selected_fun and self.env['account.analytic.group'].browse(selected_fun) or self.env['account.analytic.group']
            options['selected_fun'] = selected_fun.mapped('name')

            level = self.env['analytic.account.level'].sudo().search([('name', '=', 'BU')])
            options['bu_ids'] = level.ids or []
        super(AccountReport, self)._init_filter_analytic(options, previous_options)

    @api.model
    def _get_options_analytic_domain(self, options):
        domain = super(AccountReport, self)._get_options_analytic_domain(options=options)
        if options['fun']:
            domain.append(('fun', 'in', options['fun']))
        elif options['loc']:
            domain.append(('loc', 'in', options['loc']))
        elif options['pc']:
            domain.append(('pc', 'in', options['pc']))
        elif options['toc']:
            domain.append(('toc', 'in', options['toc']))
        elif options['mob']:
            domain.append(('mob', 'in', options['mob']))
        elif options['bu']:
            domain.append(('bu', 'in', options['bu']))
        else:
            return domain
        # group_ids = options['fun'] or options['loc'] or options['pc'] or options['toc'] or options['mob'] or options['bu']
        # if group_ids:
        #     analytic_account_ids = self.env['account.analytic.account'].search(['|', ('group_id', 'in', group_ids), ('group_id', 'child_of', group_ids)])
        #     if analytic_account_ids:
        #         domain.append(('analytic_account_id', 'in', analytic_account_ids.ids))
        return domain

    def _set_context(self, options):
        ctx = self.env.context.copy()
        if options.get('date') and options['date'].get('date_from'):
            ctx['date_from'] = options['date']['date_from']
        if options.get('date'):
            ctx['date_to'] = options['date'].get('date_to') or options['date'].get('date')
        if options.get('all_entries') is not None:
            ctx['state'] = options.get('all_entries') and 'all' or 'posted'
        if options.get('journals'):
            ctx['journal_ids'] = [j.get('id') for j in options.get('journals') if j.get('selected')]
        company_ids = []
        if options.get('multi_company'):
            company_ids = [c.get('id') for c in options['multi_company'] if c.get('selected')]
            company_ids = company_ids if len(company_ids) > 0 else [c.get('id') for c in options['multi_company']]
        ctx['company_ids'] = len(company_ids) > 0 and company_ids or [self.env.company.id]

        if options.get('analytic_accounts'):
            ctx['analytic_account_ids'] = self.env['account.analytic.account'].browse([int(acc) for acc in options['analytic_accounts']])
        if options.get('analytic_tags'):
            ctx['analytic_tag_ids'] = self.env['account.analytic.tag'].browse([int(t) for t in options['analytic_tags']])

        if options.get('partner_ids'):
            ctx['partner_ids'] = self.env['res.partner'].browse([int(partner) for partner in options['partner_ids']])

        if options.get('bu'):
            ctx['bu'] = self.env['account.analytic.group'].browse([int(bu) for bu in options['bu']])

        if options.get('mob'):
            ctx['mob'] = self.env['account.analytic.group'].browse([int(mob) for mob in options['mob']])

        if options.get('toc'):
            ctx['toc'] = self.env['account.analytic.group'].browse([int(toc) for toc in options['toc']])

        if options.get('pc'):
            ctx['pc'] = self.env['account.analytic.group'].browse([int(pc) for pc in options['pc']])

        if options.get('loc'):
            ctx['loc'] = self.env['account.analytic.group'].browse([int(loc) for loc in options['loc']])

        if options.get('fun'):
            ctx['fun'] = self.env['account.analytic.group'].browse([int(fun) for fun in options['fun']])

        if options.get('partner_categories'):
            ctx['partner_categories'] = self.env['res.partner.category'].browse([int(category) for category in options['partner_categories']])
        return ctx

    def get_report_informations(self, options):
        '''
        return a dictionary of informations that will be needed by the js widget, manager_id, footnotes, html of report and searchview, ...
        '''
        options = self._get_options(options)

        searchview_dict = {'options': options, 'context': self.env.context}
        # Check if report needs analytic
        if options.get('analytic_accounts') is not None:
            options['selected_analytic_account_names'] = [self.env['account.analytic.account'].browse(int(account)).name for account in options['analytic_accounts']]
        if options.get('analytic_tags') is not None:
            options['selected_analytic_tag_names'] = [self.env['account.analytic.tag'].browse(int(tag)).name for tag in options['analytic_tags']]
        if options.get('partner'):
            options['selected_partner_ids'] = [self.env['res.partner'].browse(int(partner)).name for partner in options['partner_ids']]
            options['selected_partner_categories'] = [self.env['res.partner.category'].browse(int(category)).name for category in (options.get('partner_categories') or [])]

        if options.get('bu'):
            options['selected_bu'] = [self.env['account.analytic.group'].browse(int(bu)).name for bu in options['bu']]

        if options.get('mob'):
            options['selected_mob'] = [self.env['account.analytic.group'].browse(int(mob)).name for mob in options['mob']]

        if options.get('toc'):
            options['selected_toc'] = [self.env['account.analytic.group'].browse(int(toc)).name for toc in options['toc']]

        if options.get('pc'):
            options['selected_pc'] = [self.env['account.analytic.group'].browse(int(pc)).name for pc in options['pc']]

        if options.get('loc'):
            options['selected_loc'] = [self.env['account.analytic.group'].browse(int(loc)).name for loc in options['loc']]

        if options.get('fun'):
            options['selected_fun'] = [self.env['account.analytic.group'].browse(int(fun)).name for fun in options['fun']]

        # Check whether there are unposted entries for the selected period or not (if the report allows it)
        if options.get('date') and options.get('all_entries') is not None:
            date_to = options['date'].get('date_to') or options['date'].get('date') or fields.Date.today()
            period_domain = [('state', '=', 'draft'), ('date', '<=', date_to)]
            options['unposted_in_period'] = bool(self.env['account.move'].search_count(period_domain))

        if options.get('journals'):
            journals_selected = set(journal['id'] for journal in options['journals'] if journal.get('selected'))
            for journal_group in self.env['account.journal.group'].search([('company_id', '=', self.env.company.id)]):
                if journals_selected and journals_selected == set(self._get_filter_journals().ids) - set(journal_group.excluded_journal_ids.ids):
                    options['name_journal_group'] = journal_group.name
                    break

        report_manager = self._get_report_manager(options)
        info = {'options': options,
                'context': self.env.context,
                'report_manager_id': report_manager.id,
                'footnotes': [{'id': f.id, 'line': f.line, 'text': f.text} for f in report_manager.footnotes_ids],
                'buttons': self._get_reports_buttons_in_sequence(),
                'main_html': self.get_html(options),
                'searchview_html': self.env['ir.ui.view'].render_template(self._get_templates().get('search_template', 'account_report.search_template'), values=searchview_dict),
                }
        return info

