# -*- coding: utf-8 -*-

from odoo import models, fields, api, exceptions
import re
import logging

#TODO : ADD FIELDS:
#res.partner.name
#res.partner.street
#res.partner.zip
#res.partner.city
#res.partner.vat
#

class Taxivoucherbatch(models.Model):
	_name='taxivoucherbatch'
	_rec_name='serial'
	_description="taxi vouchers batches"
	_sql_constraints = [
        ('unicity', 'unique(serial)', "La référence des lots de chèques doit être unique !"),
    ]
	serial=fields.Char(required=True,default='/',string='n° lot de chèques')
	size=fields.Selection(required=True, string="Nombre de chèques",selection=[('25','25')],default='25')
	client_id=fields.Many2one(comodel_name='res.partner',domain=[('category_id.name','=','vouchers')],required=True,string='client')
	
	vouchers=fields.One2many(comodel_name='taxivoucher',inverse_name='batch')
	
	@api.model
	def create(self,vals):
		bcv21_batch_regex=re.compile(r'(\d\d\d\d\d\d\d)-(\d\d\d\d\d\d\d)')
		obj=super(Taxivoucherbatch,self).create(vals)
				
		test_regex=bcv21_batch_regex.search(obj.serial)
				
		size=int(obj.size)
		
		self.env.cr.commit()
		
		#if there is a range defined, we need to create vouchers of the old format
		if 'serial' in vals:
			if test_regex:
				if int(test_regex.group(2))-int(test_regex.group(1))==24:
					for i in range(0,size):
						voucher_vals={'serial':str(int(test_regex.group(1))+i),'type':'bluecabs','client_id':vals['client_id'],'batch':obj.id}
						voucher=self.sudo().env['taxivoucher'].create(voucher_vals)
				else:
					raise exceptions.UserError("""Le numéro du lot de chèques n'est pas multiple de 25""")
			else:
				if obj.serial=='/':
					voucher_vals={'serial':'/','type':'bluecabs','client_id':vals['client_id'],'batch':obj.id}
					start_serial=''
					end_serial=''
					for i in range(0,size):
						voucher=self.env['taxivoucher'].create(voucher_vals)
						self.env.cr.commit()
						if i==0:
							start_serial=voucher.serial
						if i==size-1:
							end_serial=voucher.serial
					obj.serial=start_serial+'-'+end_serial
				else:
					raise exceptions.UserError('Le numéro du lot de chèques doit être de la forme 2063201-2063225')
					
		return obj
		
	