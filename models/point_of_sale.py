from openerp import models, fields, _, api, exceptions
import time
import logging
import ipdb as pdb
_logger = logging.getLogger(__name__)


class pos_order(models.Model):
    _inherit = 'pos.order'

    def _get_default_partner(self):
        return self.env.ref('dtm_pos_classic.partner_pos_generic').id

    def _get_default_partner_id(self):
        return self.env.ref('dtm_pos_classic.partner_id').id

    salesman_id = fields.Many2one(comodel_name='res.partner',
                                  string='Salesman',
                                  )#default=lambda self: self.env.partner,

    partner_id = fields.Many2one(comodel_name='res.partner',
                                 string='Customer',
                                 states={'draft': [('readonly', False)], 'paid': [('readonly', False)]},
                                 default=_get_default_partner)

    payment_term_id = fields.Many2one(comodel_name='account.payment.term',
                                      string='Payment Term')

    @api.multi
    def refund_classic(self):
        result = super(pos_order, self).refund()

        _logger.warning("REFUND CLASSIC CTX: {0}".format(self.env.context))

        pos_classic_form = self.env.ref('dtm_pos_classic.view_pos_classic_form')

        if self.session_id.config_id.pos_default == 'classic':
            result.update({
                'views': [(pos_classic_form.id, 'form',)],
                'view_id': pos_classic_form.id,
                'context': self.env.context
            })

        _logger.warning("REFUND RESULT: {0}".format(result))

        return result

    @api.constrains('statement_ids')
    def check_statements(self):
        paid_amount = 0.0
        total_amount = 0.0

        for statement_id in self.statement_ids:
            paid_amount += statement_id.amount

        for line_id in self.lines:
            _logger.warning("LINE: {0} {1}".format(line_id, line_id.qty))
            total_amount += line_id.price_subtotal_incl

        _logger.warning("TOTAL: {0} PAID: {1}".format(self.amount_total, paid_amount))

        if total_amount - ( paid_amount - self . rounding ) != 0:
            _logger.warning("ERROR PAY!!!")
        else:
            _logger.warning("SUCESS")

    def action_invoice ( self ):
        # import pdb; pdb . set_trace ( )
        res = super ( pos_order, self ) . action_invoice ( )
        return res

    @api.multi
    def process_full_order(self):
#        pdb.set_trace()
        # Check for the payments

        paid_amount = 0.0
        total_amount = 0.0

        for statement_id in self.statement_ids:
            paid_amount += statement_id.amount

        for line_id in self.lines:
            _logger.warning("LINE: {0} {1}".format(line_id, line_id.qty))
            total_amount += line_id.price_subtotal_incl

        _logger.warning("(PROCESS) TOTAL: {0} PAID: {1}".format(self.amount_total, paid_amount))

        if float ( "%.2f" % ( paid_amount - ( total_amount + self . rounding ) ) ) != 0.0:
            raise exceptions.ValidationError( _ ( "Needs to pay {0} before to make the payment." ) . format ( float ( "%.2f" % ( paid_amount - ( total_amount + self . rounding ) ) ) ) )

        # Make the payments and change the state

        if self.test_paid():
            self.signal_workflow('paid')

        # Create invoice
        invoice_id = self.action_invoice()

        account_invoice_obj = self.env['account.invoice']

        _logger.warning("INVOICE_ID : {0}".format(invoice_id))

        if 'res_id' in invoice_id:
            invoice = account_invoice_obj.browse([invoice_id['res_id']])

            # Change Payment Term
            invoice.payment_term = self.payment_term_id

            # Open invoice (validate)
            invoice.signal_workflow('invoice_open')

        # Pay invoice
        if self.session_id.config_id.invoice_pay:
#            pdb.set_trace()
            account_voucher_obj = self.env['account.voucher']
            invoice = account_invoice_obj.browse([invoice_id['res_id']])
            res_partner_obj = self.env['res.partner']

            new_context = {
                'payment_expected_currency': invoice.currency_id.id,
                'default_partner_id': res_partner_obj._find_accounting_partner(invoice.partner_id).id,
                'default_amount': invoice.type in ('out_refund', 'in_refund') and -invoice.residual or invoice.residual,
                'default_reference': invoice.name,
                'close_after_process': True,
                'invoice_type': invoice.type,
                'invoice_id': invoice.id,
                'default_type': invoice.type in ('out_invoice', 'out_refund') and 'receipt' or 'payment',
                'type': invoice.type in ('out_invoice', 'out_refund') and 'receipt' or 'payment',
                'uid': self.env.user.id,
                'search_disable_custom_filters': True,
                'lang': 'es_UY',
                'tz': 'Europe/Brussels',
                'active_model': 'account.invoice',
                'active_id': invoice.id,
                'active_ids': [invoice.id],
            }

            voucher_fields = account_voucher_obj.with_context(new_context).default_get([
                'period_id',
                'partner_id',
                'journal_id',
                'currency_id',
                'reference',
                'narration',
                'amount',
                'type',
                'state',
                'pay_now',
                'name',
                'date',
                'company_id',
                'tax_id',
                'payment_option',
                'comment',
                'payment_rate',
                'payment_rate_currency_id',
            ])

#            voucher_fields['journal_id'] = self . session_id . config_id . journal_default . id

            voucher_fields . update (
                account_voucher_obj . with_context ( new_context ) . onchange_date (
                    voucher_fields['date'],
                    voucher_fields['partner_id'],#agrege este
                    voucher_fields['currency_id'],
                    voucher_fields['payment_rate_currency_id'],
                    voucher_fields['amount'],
                    voucher_fields['company_id'], context = new_context
                ) . get ( 'value', {} )
            )
            voucher_fields . update (
                account_voucher_obj . with_context ( new_context ) . onchange_partner_id (
                    voucher_fields['partner_id'],
                    voucher_fields['journal_id'],
                    voucher_fields['amount'],
                    voucher_fields['currency_id'],
                    voucher_fields['type'],
                    voucher_fields['date'], context = new_context
                ) . get ( 'value', {} )
            )
            voucher_fields . update (
                account_voucher_obj . with_context ( new_context ) . onchange_amount (
                    voucher_fields['amount'],
                    voucher_fields['payment_rate'],
                    voucher_fields['partner_id'],
                    voucher_fields['journal_id'],
                    voucher_fields['currency_id'],
                    voucher_fields['type'],
                    voucher_fields['date'],
                    voucher_fields['payment_rate_currency_id'],
                    voucher_fields['company_id'], context = new_context
                ) . get ( 'value', {} )
            )
            voucher_fields . update (
                account_voucher_obj . with_context ( new_context ) . onchange_journal (
                    voucher_fields['journal_id'],
                    voucher_fields['tax_id'],
                    voucher_fields['partner_id'],
                    voucher_fields['date'],
                    voucher_fields['amount'],
                    voucher_fields['type'],
                    voucher_fields['company_id'], context = new_context
                ) . get ( 'value', {} )
            )

            # Change format
            line_cr_ids = voucher_fields['line_cr_ids']
            line_dr_ids = voucher_fields['line_dr_ids']

            _logger.warning("VOUCHER AMOUNT: {0}".format(voucher_fields['amount']))

            voucher_fields['line_cr_ids'] = []
            voucher_fields['line_dr_ids'] = [] #agregado

            """
            i = 0
            for line_cr in line_cr_ids:
                voucher_fields['line_cr_ids'].append([i, False, line_cr])
                i += 1

            for line_cr in line_dr_ids:
                voucher_fields['line_dr_ids'].append([i, False, line_cr])

            """
            i = 0
            for line_cr in line_cr_ids:
                voucher_fields['line_cr_ids'].append([0, False, line_cr])
                # i += 1

            for line_cr in line_dr_ids:
                voucher_fields['line_dr_ids'].append([0, False, line_cr])


            _logger.warning("VOUCHER_FIELDS NEW: {0}".format(voucher_fields))

            voucher_result = account_voucher_obj.with_context(new_context).create(voucher_fields)

            _logger.warning("CREATED!! {0}".format(voucher_result.id))

            voucher_result.signal_workflow('proforma_voucher')

        # Return to a new order form if there was sucessful

        pos_classic_form = self.env.ref('dtm_pos_classic.view_pos_classic_form')

        # Put the POS Classic flag in the context
        newctx = {}
        newctx.update(self.env.context)
        newctx['active_pos'] = 'classic'

        return {
            'name': _('POS Classic'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'pos.order',
            'views': [(pos_classic_form.id, 'form',)],
            'view_id': pos_classic_form.id,
            'context': newctx,
        }

    @api.model
    def create(self, vals):
        _logger.warning("CREATE CTX: {0}".format(self.env.context))
        _logger.warning("CREATE, Vals<{0}>".format(vals))

        if self.env.context.get('active_pos', 'default') == 'classic':
            self.update_new_statement(vals, create_now=True)

        _logger.warning("CREATE2, Vals<{0}>".format(vals))

        return super(pos_order, self).create(vals)

    @api.multi
    def write(self, vals):
        _logger.warning("WRITE CTX: {0}".format(self.env.context))
        _logger.warning("WRITE, Id<{1}>, Vals<{0}>".format(vals, self.id))

        if self.env.context.get('active_pos', 'default') == 'classic':
            self.update_new_statement(vals, create_now=False)

        _logger.warning("WRITE2: {0}".format(vals))

        return super(pos_order, self).write(vals)

    @api.model
    def update_new_statement(self, vals, create_now=True):
        # Objects
        res_partner_obj = self.env['res.partner']
        property_obj = self.env['ir.property']
        journal_obj = self.env['account.journal']
        pos_session_obj = self.env['pos.session']
        refs = {}

        _logger.warning("UPDATE NEW STATEMENT, CreateNow<{0}> Vals<{1}>".format(create_now, vals))

        refs.update(vals)

        if create_now:
            refs.update(self.default_get(['user_id', 'state', 'name', 'date_order', 'nb_print', 'sequence_number', 'session_id', 'company_id', 'pricelist_id']))

            if refs.get('session_id'):
                # set name based on the sequence specified on the config
                session = self.env['pos.session'].browse([refs['session_id']])
                refs['name'] = session.config_id.sequence_id._next()
            else:
                # fallback on any pos.order sequence
                refs['name'] = self.env['ir.sequence'].get_id('pos.order', 'code', context=self.env.context)
        else:
            refs.update({
                'user_id': self.user_id,
                'state': self.state,
                'name': self.name,
                'date_order': self.date_order,
                'nb_print': self.nb_print,
                'sequence_number': self.sequence_number,
                'session_id': self.session_id.id,
                'company_id': self.company_id.id,
                'pricelist_id': self.pricelist_id.id,
                'partner_id': self.partner_id.id,
            })

        if pos_session_obj.browse(refs['session_id']).config_id.pos_default == 'default':
            return vals

        if vals.get('statement_ids', False):
            for statement_obj in vals['statement_ids']:

                if statement_obj[1]:
                    break

                statement_dict = statement_obj[2]
                company_ctx = dict(self.env.context, force_company=journal_obj.browse([statement_dict['journal_id']]).company_id.id)
                account_def = property_obj.get('property_account_receivable', 'res.partner', context=company_ctx)

                partner = res_partner_obj.browse([refs['partner_id']])
                session = pos_session_obj.browse([refs['session_id']])

                statement_dict['name'] = refs['name'] + ': ' + str(time.strftime('%Y-%m-%d %H:%M:%S'))
                statement_dict['partner_id'] = partner.id and res_partner_obj._find_accounting_partner(partner).id or False
                statement_dict['account_id'] = (partner.id and partner.property_account_receivable  and partner.property_account_receivable.id) or (account_def and account_def.id) or False
                statement_dict['ref'] = session.name

                if not statement_dict.get('account_id', False):
                    if statement_dict['partner_id']:
                        msg = _('There is no receivable account defined to make payment.')
                    else:
                        msg = _('There is no receivable account defined to make payment for the partner: "%s" (id:%d).') % (pos_order_obj.partner_id.name, pos_order_obj.partner_id.id,)
                    raise exceptions.except_orm(_('Configuration Error!'), msg)

                for statement in session.statement_ids:
                    _logger.warning("STAT JOURNAL: {0}, {1}".format(statement.journal_id.id, statement.journal_id.name))
                    if statement.journal_id.id == statement_dict['journal_id']:
                        statement_dict['statement_id'] = statement.id
                        break

                if not statement_dict.get('statement_id', False):
                    raise exceptions.except_orm(_('Error!'), _('You have to open at least one cashbox.'))

        if create_now:
            vals.update(self.default_get(['user_id', 'state', 'name', 'date_order', 'nb_print', 'sequence_number', 'session_id', 'company_id', 'pricelist_id']))
            vals.update({'name': refs['name']})

        _logger.warning("UPDATE STATEMENT NEW VALS: {0}".format(vals))

        return vals


class pos_config(models.Model):
    _inherit = 'pos.config'

    pos_default = fields.Selection(selection=[('classic', 'Classic POS'), ('default', 'Default POS')],
                                   string='Default POS', required=True, default='classic')
    journal_default = fields.Many2one(comodel_name='account.journal', string='Default journal to pay', required=True)

    invoice_pay = fields.Boolean(string='Make payments of the invoice', default=False)


class pos_session(models.Model):
    _inherit = 'pos.session'

    @api.multi
    def open_cb(self):
        # super(pos_session, self).open_cb(cr, uid, ids, context)

        self.signal_workflow('open')
        self.with_context({'active_id': self.id})

        if self.config_id.pos_default == 'classic':
                pos_classic_form = self.env.ref('dtm_pos_classic.view_pos_classic_form')

                # Put the POS Classic flag in the context
                newctx = {}
                newctx.update(self.env.context)
                newctx['active_pos'] = 'classic'

                return {
                    'name': _('POS Classic'),
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'pos.order',
                    'views': [(pos_classic_form.id, 'form',)],
                    'view_id': pos_classic_form.id,
                    'context': newctx,
                }

        return {
            'type': 'ir.actions.act_url',
            'url':   '/pos/web/',
            'target': 'self',
        }

    @api.multi
    def open_frontend_cb(self):
        # super(pos_session, self).open_frontend_cb()

        for session in self.browse(self.ids):
            if session.user_id != self.env.user:
                raise exceptions.except_orm(
                        _('Error!'),
                        _("You cannot use the session of another users. This session is owned by %s. Please first close this one to use this point of sale." % session.user_id.name))

        self.with_context({'active_id': self.id})

        if self.config_id.pos_default == 'classic':
                pos_classic_form = self.env.ref('dtm_pos_classic.view_pos_classic_form')

                # Put the POS Classic flag in the context
                newctx = {}
                newctx.update(self.env.context)
                newctx['active_pos'] = 'classic'

                return {
                    'name': _('POS Classic'),
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'pos.order',
                    'views': [(pos_classic_form.id, 'form',)],
                    'view_id': pos_classic_form.id,
                    'context': newctx,
                }

        return {
            'type': 'ir.actions.act_url',
            'url':   '/pos/web/',
            'target': 'self',
        }
