from openerp import models, fields, _, api
import logging
_logger = logging.getLogger(__name__)

class account_bank_statement_line(models.Model):
    _inherit = 'account.bank.statement.line'
