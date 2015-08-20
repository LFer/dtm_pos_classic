from openerp import models, fields, _ , api


class pos_session_opening(models.TransientModel):
    _inherit = 'pos.session.opening'

    @api.multi
    def open_ui(self):

        context = dict(self.env.context or {})
        context['active_id'] = self.pos_session_id.id

        self.with_context(context)

        if self.pos_config_id.pos_default == 'classic':
                pos_classic_form = self.env.ref('dtm_pos_classic.view_pos_classic_form')

                # Put the POS Classic flag in the context
                newctx = {}
                newctx.update(context)
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