# -*- coding: utf-8 -*-

from odoo import models, fields, api

class Taxivoucher(models.Model):
	_name='taxivoucher'
	_rec_name='serial'
	_description="taxi vouchers"
	_sql_constraints = [
        ('unicity', 'unique(serial)', "La référence des chèques doit être unique !"),
    ]
    
	serial=fields.Char(required=True,default='/',string='n° chèque')
	type = fields.Selection(string='Type de chèque',selection=[('bluecabs','Chèque Taxis Bleus'),('municipal','Communal'),('regional','Régional')],default='bluecabs',required=True)
	client_id=fields.Many2one(comodel_name='res.partner',domain=[('category_id.name','=','vouchers')],required=True,string='client')
	batch=fields.Many2one(comodel_name='taxivoucherbatch',string='lot de chèques',ondelete='cascade')
	ride=fields.Many2one(comodel_name='ride',domain=[('billing_type','=','voucher')],string='course')
	billable=fields.Boolean(default=True,string='facturable')
	buyable=fields.Boolean(default=True,string='achetable')
	
	@api.model
	def create(self,vals):
		obj=super().create(vals)
		if obj.serial=='/':
			obj.serial=self.env['ir.sequence'].next_by_code('number_bcv22')
		return obj		
		
	@api.onchange('type')
	def onchange_type(self):
		if self.type=='bluecabs':
			self.billable=True
			self.buyable=True
		if self.type=='municipal':
			self.billable=False
			self.buyable=True
		if self.type=='regional':
			self.billable=False
			self.buyable=True
	
