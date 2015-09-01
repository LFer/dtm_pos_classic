from openerp import models, fields, _, api
import logging
import ipdb as pdb
_logger = logging.getLogger(__name__)

class account_bank_statement_line(models.Model):
    _inherit = 'account.bank.statement.line'

    def _get_default_partner(self):
#        pdb.set_trace()
        pos_obj = self.env['pos.order']
        cliente_obj = pos_obj.partner_id
        return cliente_obj


    partner_id = fields.Many2one(comodel_name='res.partner', string='Cliente')#, default=_get_default_partner)
"""
    @api.one
    @api.onchange('amount', 'pos_statement_id')
    def onchange_customer_checks(self):
        for x in self.pos_statement_id:
#            pdb.set_trace()
            self.amount = x.amount_total
"""
