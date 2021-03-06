# -*- coding: utf-8 -*-
# © 2004-2010 OpenERP SA
# © 2014 Angel Moya <angel.moya@domatix.com>
# © 2015 Pedro M. Baeza <pedro.baeza@tecnativa.com>
# © 2016 Carlos Dauden <carlos.dauden@tecnativa.com>
# Copyright 2016-2017 LasLabs Inc.
# Copyright 2017 Pesol (<http://pesol.es>)
# Copyright 2017 Angel Moya <angel.moya@pesol.es>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, models
from odoo.exceptions import ValidationError
from odoo.tools.translate import _


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    @api.model
    def _prepare_sale_line(self, line, order_id):
        sale_line = self.env['sale.order.line'].new({
            'order_id': order_id,
            'product_id': line.product_id.id,
            'proudct_uom_qty': line.quantity,
            'proudct_uom_id': line.uom_id.id,
        })
        # Get other invoice line values from product onchange
        sale_line.product_id_change()
        sale_line_vals = sale_line._convert_to_write(sale_line._cache)
        # Insert markers
        name = line.name
        contract = line.analytic_account_id
        if 'old_date' in self.env.context and 'next_date' in self.env.context:
            lang_obj = self.env['res.lang']
            lang = lang_obj.search(
                [('code', '=', contract.partner_id.lang)])
            date_format = lang.date_format or '%m/%d/%Y'
            name = self._insert_markers(
                line, self.env.context['old_date'],
                self.env.context['next_date'], date_format)
        sale_line_vals.update({
            'name': name,
            'discount': line.discount,
            'price_unit': line.price_unit,
        })
        return sale_line_vals

    @api.multi
    def _prepare_sale(self):
        self.ensure_one()
        if not self.partner_id:
            raise ValidationError(
                _("You must first select a Customer for Contract %s!") %
                self.name)
        sale = self.env['sale.order'].new({
            'partner_id': self.partner_id,
            'date_order': self.recurring_next_date,
            'origin': self.name,
            'company_id': self.company_id.id,
            'user_id': self.partner_id.user_id.id,
            'project_id': self.id
        })
        # Get other invoice values from partner onchange
        sale.onchange_partner_id()
        return sale._convert_to_write(sale._cache)

    @api.multi
    def _create_invoice(self):
        self.ensure_one()
        if self.type == 'invoice':
            return super(AccountAnalyticAccount, self)._create_invoice()
        else:
            sale_vals = self._prepare_sale()
            sale = self.env['sale.order'].create(sale_vals)
            for line in self.recurring_invoice_line_ids:
                sale_line_vals = self._prepare_sale_line(line, sale.id)
                self.env['sale.order.line'].create(sale_line_vals)
            if self.sale_autoconfirm:
                sale.action_confirm()
            return sale
