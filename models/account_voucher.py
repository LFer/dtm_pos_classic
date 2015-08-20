from openerp import models, fields, _, api
import logging
import ipdb as pdb

_logger = logging.getLogger(__name__)


class account_voucher(models.Model):
    _inherit = 'account.voucher'

    @api.model
    def create(self, vals):
#        pdb.set_trace()
        _logger.warning("VOUCHER CREATE: {0}".format(vals))
        return super(account_voucher, self).create(vals)


class account_move(models.Model):
    _inherit = 'account.move'

    @api.model
    def create(self, vals):
#        pdb.set_trace()
        _logger.warning("VOUCHER CREATE: {0}".format(vals))
        return super(account_move, self).create(vals)
