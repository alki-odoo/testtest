# -*- coding: utf-8 -*-
#dummy edit for test purpose

from odoo import models, fields, api

import pandas as pd

import logging
from datetime import timedelta
from datetime import datetime
import pytz

class Ride(models.Model):
	_name="ride"
	_description="taxi rides"
	_rec_name='ride_ref'
	
	_sql_constraints = [
        ('unicity', 'unique(ride_ref)', "La référence des courses doit être unique !"),
    ]
    
	#field about the ride
	ishandycab = fields.Boolean(default=False,string='handycab')
	billing_type=fields.Selection(string='Type de service',selection=[('billable','A facturer'),('voucher','Chèque')],default='billable',required=True)
	ride_ref=fields.Char(required=True,default='/',string='n° course')
	
	#fields related to voucher
	voucher_id=fields.Many2one(comodel_name='taxivoucher',domain=[('ride','=',False)],string='n° chèque')
	
	#generic fields
	ride_dt=fields.Datetime(required=True,string='d/h course')
	ops_date=fields.Date(compute='_compute_ops_date',store=True,string='date ops')
	origin=fields.Char(string='départ')
	destination=fields.Char(string='destination')
	#currency_id=fields.Many2one('res.currency')
	#price=fields.Monetary(string='Prix',currency_field=currency_id)
	price=fields.Float(default=0,string='prix')
	reviewed_price=fields.Float(default=0,string='prix final')
	ride_info=fields.Text(string='info course')
	incident_info=fields.Text(string='incident')
	
	#fields about the billing process
	state=fields.Selection(selection=[('downloaded','Téléchargée'),('checked','Vérifiée'),('to_check','A vérifier')],default='to_check',required=True,string='statut')
	billable=fields.Boolean(default=True,required=True,string='facturable')
	billed=fields.Boolean(default=False,required=True,string='facturée')
	buyable=fields.Boolean(default=True,required=True,string='achetable')
	published2subscriber=fields.Boolean(default=False,required=True,string='publiée adhérent')
	bought=fields.Boolean(default=False,required=True,string='achetée')
	
	#fields about the sale
	client_id=fields.Many2one(comodel_name='res.partner',domain=['|',('category_id.name','=','vouchers'),('category_id.name','=','billed_services')],compute='_compute_client',inverse='_set_client',store=True,required=True,string='client')
	#invoice=fields.Many2one(comodel_name='account.move',domain=[('move_type','=','out_invoice')])
	
	#fields about the purchase
	subscriber_id=fields.Many2one(comodel_name='res.partner',domain=[('category_id.name','=','subscriber')],compute='_compute_subscriber',inverse='_set_subscriber',store=True,required=True,string='fournisseur')
	#purchase_order=fields.Many2one(comodel_name='purchase.order')
	
	#fields about the subscriber
	subscriber_ref=fields.Integer(required=True,string='c.société')
	driver_ref=fields.Integer(string='c.chauffeur')
	driver_name=fields.Char(string='chauffeur')
	taxi_ref=fields.Integer(string='c.radio')

	#fields about the client
	client_passengers=fields.Char(string='passager')
	client_company_ref=fields.Char(string='c.abonné')
	client_company_dpt_ref=fields.Char(string='c.service')
	client_company_dpt_name=fields.Char(string='abonné')
	client_internal_ref=fields.Char(string='ref.')
	
	#field for STIB
	final_comment=fields.Char(string='commentaire')
	
	@api.model
	def create(self,vals):
		
		#this is to get the default ref for the ride
		if vals['ride_ref']=='/':
			vals['ride_ref']=self.env['ir.sequence'].get('number_rides')
		
		if 'client_company_ref' in vals:
			akos_result=self.env['res.partner'].search([('billed_client_akostaxikey','=',vals['client_company_ref'])])
			if akos_result:
				vals['client_id']=akos_result[0].id
				
		if 'subscriber_ref' in vals:
			subscriber_result=self.env['res.partner'].search([('subscriber_ref','=',vals['subscriber_ref'])])
			if subscriber_result:
				vals['subscriber_id']=subscriber_result[0].id
		
		if not 'reviewed_price' in vals:
			vals['reviewed_price']=vals['price']
		
		obj=super(Ride,self).create(vals)

		if obj.voucher_id:
			voucher_result=self.sudo(True).env['taxivoucher'].search([('serial','=',obj.voucher_id.serial)])
			if voucher_result:
				voucher_result[0].ride=obj.id
				self.client_id=voucher_result[0].client_id

		return obj
		
	def write (self, vals):
		obj=super(Ride,self).write(vals)
		#this is when we update the voucher ref
		if self.voucher_id:
			voucher_result=self.sudo(True).env['taxivoucher'].search([('serial','=',self.voucher_id.serial)])
			if voucher_result:
				voucher_result[0].ride=self.id
		return obj
	
	@api.depends('client_company_ref','voucher_id')
	def _compute_client(self):
		for record in self:
			if record.voucher_id:
				voucher_result=self.sudo(True).env['taxivoucher'].search([('serial','=',record.voucher_id.serial)])
				if voucher_result:
					voucher_result[0].ride=obj.id
					record.client_id=voucher_result[0].client_id
			if record.client_company_ref:
				akos_result=self.env['res.partner'].search([('billed_client_akostaxikey','=',record.client_company_ref)])
				if akos_result:
					record.client_id=akos_result[0]
					
	def _set_client(self):
		pass
		
	@api.depends('ride_dt')
	def _compute_ops_date(self):
		local = pytz.timezone("Europe/Brussels")
		for record in self:
			my_ride_dt=pytz.utc.localize(record.ride_dt)
			local_ride_dt=my_ride_dt.astimezone(local)
			if local_ride_dt.hour>=12:
				record.ops_date = local_ride_dt.date()
			else:
				record.ops_date = (local_ride_dt-timedelta(days=1)).date()
					
	@api.depends('subscriber_ref')
	def _compute_subscriber(self):
		for record in self:
			if record.subscriber_ref:
				subscriber_result=self.env['res.partner'].search(domain=[('category_id.name','=','subscriber')])	
				if subscriber_result:
					record.subscriber_id=subscriber_result[0]
	
	def _set_subscriber(self):
		pass
		
	@api.model
	def bill_rides(self):
	
		VENCO_id=self.env['account.journal'].search([('code','=','VENCO')])[0].id
		AFAC_id=self.env['product.product'].search([('default_code','=','AFAC')])[0].id
		BCV_id=self.env['product.product'].search([('default_code','=','BCV')])[0].id
				
		#we fetch the id of HANDY to bill to that company when the flag is true
		HANDY_id=self.env['res.partner'].search([('billed_client_akostaxikey','=','HANDYCAB')])[0]
		
		billable_rides=pd.DataFrame(columns=['id','client_ref','client_company_dpt_name','client_id','client_internal_ref','subscriber_ref','subscriber_id','price','reviewed_price','billable','billed','buyable','bought','state','ride_dt','ride_reference','client_passengers','origin','destination','taxi_ref','ride_ref','billing_type','client_id_int'])
		voucher_rides=pd.DataFrame(columns=['id','client_id','subscriber_ref','subscriber_id','reviewed_price','billable','billed','buyable','bought','state','ride_dt','ride_ref','voucher_ref','ride_info','client_id_int'])
		
		end_dt=pd.to_datetime(datetime.today().strftime('%Y-%m-%d'+' 00:00:00'))
		
		for record in self:
			logging.info('on boucle sur les records')
			if (record.billable & (~(record.billed)) & (~(record.state=='to_check'))& (record['ride_dt']<=end_dt)):
				if(record.ishandycab):
					temp_client_id=HANDY_id
				else:
					temp_client_id=record.client_id
					
				logging.info('ride_ref'+record.ride_ref)
				
				if(record['billing_type']=='billable'):	
					billable_rides=billable_rides.append({	'id':record.id,
								'client_company_dpt_name':record.client_company_dpt_name,
								'client_id':temp_client_id,
								'client_internal_ref':record.client_internal_ref,
								'subscriber_ref':record.subscriber_ref,
								'subscriber_id':record.subscriber_id,
								'price':record.price,
								'reviewed_price':record.reviewed_price,
								'billable':record.billable,
								'billed':record.billed,
								'buyable':record.buyable,
								'bought':record.bought,
								'state':record.state,
								'ride_dt':record.ride_dt,
								'ride_reference':record.ride_ref,
								'client_passengers':record.client_passengers,
								'origin':record.origin,
								'destination':record.destination,
								'taxi_ref':record.taxi_ref,
								'ride_ref':record.ride_ref,
								'client_id_int':temp_client_id.id
							},ignore_index=True)
							
				if(record['billing_type']=='voucher'):
					logging.info('found a voucher !')
					logging.info('le client id est : ')
					logging.info(temp_client_id.id)
					voucher_rides=voucher_rides.append({
								'id':record.id,
								'client_id':temp_client_id,
								'subscriber_ref':record.subscriber_ref,
								'subscriber_id':record.subscriber_id,
								'reviewed_price':record.reviewed_price,
								'billable':record.billable,
								'billed':record.billed,
								'buyable':record.buyable,
								'bought':record.bought,
								'state':record.state,
								'ride_dt':record.ride_dt,
								'ride_ref':record.ride_ref,
								'voucher_id':record.voucher_id,
								'ride_info':record.ride_info,
								'client_id_int':temp_client_id.id
							},ignore_index=True)
							
		#billable_rides['client_id_int'] = billable_rides['client_id'].apply(lambda x: x.id)
		#voucher_rides['client_id_int'] = voucher_rides['client_id'].apply(lambda x: x.id)
		
		billable_clients=set([*(billable_rides['client_id_int']),*(voucher_rides['client_id_int'])])
		billable_clients=pd.DataFrame(billable_clients,columns=['client_id'])
		billable_clients['group_rides']=billable_clients['client_id'].apply(lambda x: self.env['res.partner'].search([('id','=',x)]).group_rides)
		
		billable_rides.sort_values(by=['client_company_dpt_name','ride_dt'],inplace=True)
		voucher_rides.sort_values(by=['ride_dt'],inplace=True)

		for idx,client in billable_clients.iterrows():
			#we identify the record of the partner to be billed. Exception handling for Handy rides
			invoice_line_ids=[]
			
			if(client['group_rides']):#if this is a client where we can group rides
				#grouping rides
				for index,record in billable_rides[billable_rides['client_id_int']==client['client_id']].iterrows():
					if ((record['billable']) & (~(record['billed']))):
						if ((record['destination'] != '') &(~pd.isnull(record['destination']))):
							infodest='\n'+'Dest. : '+record['destination']
						else:
							infodest=''
						invoice_line_ids.append(
									(0,0,{	'product_id':AFAC_id,
										'name':'Département : '+record['client_company_dpt_name']+'\nDate : '+record['ride_dt'].strftime('%d-%m-%Y')+' - Réf. : '+record['ride_ref']+'\n'+'Passagers : '+record['client_passengers']+'\n'+'Orig. : '+record['origin']+infodest,
										'quantity':1,
										'tax_ids':[(6,0,[71])],
										'price_unit':record['reviewed_price']})
												)
						updated_record=self.env['ride'].search([('id','=',record['id'])])
						updated_record.billed=True
				#grouping vouchers
				for index,record in voucher_rides[voucher_rides['client_id_int']==client['client_id']].iterrows():
					if ((record['billable']) & (~(record['billed']))):
						voucher_ref=self.env['taxivoucher'].search([('id','=',record['voucher_id'].id)])[0].serial
						if record['ride_info']:
							passenger_ref = '\n'+'Référence Passagers : '+str(record['ride_info'])
						else:
							passenger_ref = ''
						invoice_line_ids.append(
									(0,0,{	'product_id':BCV_id,
										'name':'Date : '+record['ride_dt'].strftime('%d-%m-%Y')+' - Réf. : '+str(voucher_ref)+passenger_ref,
										'quantity':1,
										'tax_ids':[(6,0,[71])],
										'price_unit':record['reviewed_price']})
												)
						updated_record=self.env['ride'].search([('id','=',record['id'])])
						updated_record.billed=True
				
				#issuing the invoice
				self.env['account.move'].create({
        	                                'move_type': 'out_invoice',
        	                                'date': fields.Datetime.today(),
        	                                'partner_id': client['client_id'],
        	                                'invoice_date': fields.Datetime.today(),
        	                                'journal_id':VENCO_id,
          	                                #'currency_id': self.currency_data['currency'].id,
        	                                #'invoice_payment_term_id': self.pay_terms_a.id,
        	                                'invoice_line_ids': invoice_line_ids
        	                                        })
			else:#if this is a client where we need to issue one ride per bill
				#going through rides
				for index,record in billable_rides[billable_rides['client_id_int']==client['client_id']].iterrows():
					invoice_line_ids=[]
					if ((record['billable']) & (~(record['billed']))):
						if ((record['destination'] != '') &(~pd.isnull(record['destination']))):
							infodest='\n'+'Dest. : '+record['destination']
						else:
							infodest=''
						invoice_line_ids.append(
									(0,0,{	'product_id':AFAC_id,
										'name':'Département : '+record['client_company_dpt_name']+'\nDate : '+record['ride_dt'].strftime('%d-%m-%Y')+' - Réf. : '+record['ride_ref']+'\n'+'Passagers : '+record['client_passengers']+'\n'+'Orig. : '+record['origin']+infodest,
										'quantity':1,
										'tax_ids':[(6,0,[71])],
										'price_unit':record['reviewed_price']})
												)
						
						updated_record=self.env['ride'].search([('id','=',record['id'])])
						updated_record.billed=True
					self.env['account.move'].create({
        	                                'move_type': 'out_invoice',
        	                                'date': fields.Datetime.today(),
        	                                'partner_id': client['client_id'],
        	                                'invoice_date': fields.Datetime.today(),
        	                                'journal_id':VENCO_id,
        	                                'ref':record['client_internal_ref'],
        	                                #'currency_id': self.currency_data['currency'].id,
        	                                #'invoice_payment_term_id': self.pay_terms_a.id,
        	                                'invoice_line_ids': invoice_line_ids
        	                                        })
        		#going through vouchers
				for index,record in voucher_rides[voucher_rides['client_id_int']==client['client_id']].iterrows():
					invoice_line_ids=[]
					if ((record['billable']) & (~(record['billed']))):
						voucher_ref=self.env['taxivoucher'].search([('id','=',record['voucher_id'].id)])[0].serial
						if record['ride_info']:
							passenger_ref = '\n'+'Référence Passagers : '+str(record['ride_info'])
						else:
							passenger_ref = ''
						invoice_line_ids.append(
									(0,0,{	'product_id':BCV_id,
										'name':'Date : '+record['ride_dt'].strftime('%d-%m-%Y')+' - Réf. : '+str(voucher_ref)+passenger_ref,
										'quantity':1,
										'tax_ids':[(6,0,[71])],
										'price_unit':record['reviewed_price']})
												)
						updated_record=self.env['ride'].search([('id','=',record['id'])])
						updated_record.billed=True
				
				
					self.env['account.move'].create({
        	                                'move_type': 'out_invoice',
        	                                'date': fields.Datetime.today(),
        	                                'partner_id': client['client_id'],
        	                                'invoice_date': fields.Datetime.today(),
        	                                'journal_id':VENCO_id,
        	                                'ref':record['ride_info'],
        	                                #'currency_id': self.currency_data['currency'].id,
        	                                #'invoice_payment_term_id': self.pay_terms_a.id,
        	                                'invoice_line_ids': invoice_line_ids
        	                                        })
        		

		
##########################################################################################
	@api.model
	def publish_rides_subscribers(self):
	
		VENCO_id=self.env['account.journal'].search([('code','=','VENCO')])[0].id
		AFAC_id=self.env['product.product'].search([('default_code','=','AFAC')])[0].id
		BCV_id=self.env['product.product'].search([('default_code','=','BCV')])[0].id	
	
		billable_rides=pd.DataFrame(columns=['id','client_ref','client_company_dpt_name','client_id','subscriber_ref','subscriber_id','price','reviewed_price','billable','billed','buyable','bought','state','ride_dt','ride_reference','client_passengers','origin','destination','taxi_ref','ride_ref','billing_type','subscriber_id_int'])
		
		end_dt=pd.to_datetime(datetime.today().strftime('%Y-%m-%d'+' 00:00:00'))
		
		for record in self:
			if (record.buyable & (~(record.bought)) & (~(record.state=='to_check')) & (~(record.published2subscriber)) & (record['ride_dt']<=end_dt)):				
				if(record['billing_type']=='billable'):
					billable_rides=billable_rides.append({	'id':record.id,
								'client_company_dpt_name':record.client_company_dpt_name,
								'client_id':record.client_id,
								'subscriber_ref':record.subscriber_ref,
								'subscriber_id':record.subscriber_id,
								'price':record.price,
								'reviewed_price':record.reviewed_price,
								'billable':record.billable,
								'billed':record.billed,
								'buyable':record.buyable,
								'bought':record.bought,
								'state':record.state,
								'ride_dt':record.ride_dt,
								'ride_reference':record.ride_ref,
								'client_passengers':record.client_passengers,
								'origin':record.origin,
								'destination':record.destination,
								'taxi_ref':record.taxi_ref,
								'ride_ref':record.ride_ref,
								'subscriber_id_int':record.subscriber_id.id
							},ignore_index=True)
							
		
		subscribers=set([*(billable_rides['subscriber_id_int'])])
		
		billable_rides.loc[billable_rides['price']!=0.0,'buy_price']=billable_rides[['price','reviewed_price']].min(axis=1)
		billable_rides.loc[billable_rides['price']==0.0,'buy_price']=billable_rides['reviewed_price']
		
		billable_rides.sort_values(by=['taxi_ref','ride_dt','ride_reference'],inplace=True)
		
		for subscriber in subscribers:
			purchase_order_lines=[]
			for index,record in billable_rides[billable_rides['subscriber_id_int']==subscriber].iterrows():
				if((record['buyable']) & (~(record['bought']))):
					if ((record['destination'] != '') &(~pd.isnull(record['destination']))):
							infodest='\n'+'Dest. : '+record['destination']
					else:
						infodest=''
					purchase_order_lines.append(
									(0,0,{'date_planned':fields.Datetime.today(),'product_id':AFAC_id,'product_qty':1,
										'name':'Voiture : '+str(record['taxi_ref'])+'\nDate : '+record['ride_dt'].strftime('%d-%m-%Y')+' - Réf. : '+record['ride_reference']+'\n'+'Orig. : '+record['origin']+infodest,
										'price_unit':record['buy_price']})
								)
					updated_record=self.env['ride'].search([('id','=',record['id'])])
					updated_record.published2subscriber=True
			
			self.env['purchase.order'].create({
												'partner_id': subscriber,
												'order_line':purchase_order_lines,
												'state':'sent'
											})
											

				
##########################################################################################	
	@api.model
	def purchase_rides(self):
	
		VENCO_id=self.env['account.journal'].search([('code','=','VENCO')])[0].id
		AFAC_id=self.env['product.product'].search([('default_code','=','AFAC')])[0].id
		BCV_id=self.env['product.product'].search([('default_code','=','BCV')])[0].id
			
		temp_PO=self.env['purchase.order'].search([('state','=','sent')])
		
		logging.info(temp_PO)
		
		for PO in temp_PO:
			PO.button_cancel()
	
		billable_rides=pd.DataFrame(columns=['id','client_ref','client_company_dpt_name','client_id','subscriber_ref','subscriber_id','price','reviewed_price','billable','billed','buyable','bought','state','ride_dt','ride_reference','client_passengers','origin','destination','taxi_ref','ride_ref','billing_type','subscriber_id_int'])
		voucher_rides=pd.DataFrame(columns=['id','client_id','subscriber_ref','subscriber_id','reviewed_price','billable','billed','buyable','bought','state','ride_dt','ride_ref','voucher_ref','ride_info','subscriber_id_int'])
		
		end_dt=pd.to_datetime(datetime.today().strftime('%Y-%m-%d'+' 00:00:00'))
		
		for record in self:
			if (record.buyable & (~(record.bought)) & (~(record.state=='to_check')) & (record['ride_dt']<=end_dt)):				
				if(record['billing_type']=='billable'):
					billable_rides=billable_rides.append({	'id':record.id,
								'client_company_dpt_name':record.client_company_dpt_name,
								'client_id':record.client_id,
								'subscriber_ref':record.subscriber_ref,
								'subscriber_id':record.subscriber_id,
								'price':record.price,
								'reviewed_price':record.reviewed_price,
								'billable':record.billable,
								'billed':record.billed,
								'buyable':record.buyable,
								'bought':record.bought,
								'state':record.state,
								'ride_dt':record.ride_dt,
								'ride_reference':record.ride_ref,
								'client_passengers':record.client_passengers,
								'origin':record.origin,
								'destination':record.destination,
								'taxi_ref':record.taxi_ref,
								'ride_ref':record.ride_ref,
								'subscriber_id_int':record.subscriber_id.id
							},ignore_index=True)
							
				if(record['billing_type']=='voucher'):
					voucher_rides=voucher_rides.append({
								'id':record.id,
								'client_id':record.client_id,
								'subscriber_ref':record.subscriber_ref,
								'subscriber_id':record.subscriber_id,
								'reviewed_price':record.reviewed_price,
								'billable':record.billable,
								'billed':record.billed,
								'buyable':record.buyable,
								'bought':record.bought,
								'state':record.state,
								'ride_dt':record.ride_dt,
								'ride_ref':record.ride_ref,
								'voucher_id':record.voucher_id,
								'ride_info':record.ride_info,
								'subscriber_id_int':record.subscriber_id.id
							},ignore_index=True)
							
		#billable_rides['subscriber_id_int'] = billable_rides['subscriber_id'].apply(lambda x: x.id)
		#voucher_rides['subscriber_id_int'] = voucher_rides['subscriber_id'].apply(lambda x: x.id)
		
		subscribers=set([*(billable_rides['subscriber_id_int']),*(voucher_rides['subscriber_id_int'])])
		
		billable_rides.loc[billable_rides['price']!=0.0,'buy_price']=billable_rides[['price','reviewed_price']].min(axis=1)
		billable_rides.loc[billable_rides['price']==0.0,'buy_price']=billable_rides['reviewed_price']
		
		billable_rides.sort_values(by=['taxi_ref','ride_dt','ride_reference'],inplace=True)
		voucher_rides.sort_values(by=['ride_dt','voucher_ref'],inplace=True)
		
		for subscriber in subscribers:
			purchase_order_lines=[]
			for index,record in billable_rides[billable_rides['subscriber_id_int']==subscriber].iterrows():
				if((record['buyable']) & (~(record['bought']))):
					if ((record['destination'] != '') &(~pd.isnull(record['destination']))):
						infodest='\n'+'Dest. : '+record['destination']
					else:
						infodest=''
					purchase_order_lines.append(
									(0,0,{'date_planned':fields.Datetime.today(),'product_id':AFAC_id,'product_qty':1,
										'name':'Voiture : '+str(record['taxi_ref'])+'\nDate : '+record['ride_dt'].strftime('%d-%m-%Y')+' - Réf. : '+record['ride_reference']+'\n'+'Orig. : '+record['origin']+infodest,
										'price_unit':0.98*record['buy_price']})
								)
					updated_record=self.env['ride'].search([('id','=',record['id'])])
					updated_record.bought=True
			for index,record in voucher_rides[voucher_rides['subscriber_id_int']==subscriber].iterrows():
				if((record['buyable']) & (~(record['bought']))):
					#voucher=self.env['taxivoucher'].search([('id','=',record['voucher_id'])])[0]
					voucher_type=dict(record['voucher_id']._fields['type'].selection).get(record['voucher_id'].type)
					voucher_ref=record['voucher_id'].serial
					purchase_order_lines.append(
												(0,0,{	'date_planned':fields.Datetime.today(),
														'product_id':BCV_id,
														'product_qty':1,
														'name':'Date : '+record['ride_dt'].strftime('%d-%m-%Y')+'\n'+voucher_type +' - Réf. : '+voucher_ref,
														'price_unit':0.98*record['reviewed_price']})
												)
					updated_record=self.env['ride'].search([('id','=',record['id'])])
					updated_record.bought=True
			
			self.env['purchase.order'].create({
												'partner_id': subscriber,
												'order_line':purchase_order_lines,
												'state':'purchase'
											})

				
	@api.onchange('reviewed_price')
	def onchange_price(self):
		for record in self:
			record.state='checked'

	@api.onchange('subscriber_ref')
	def onchange_subscriber_ref(self):
		result=self.env['res.partner'].search([('subscriber_ref','=',self.subscriber_ref)])
		if result:
			self.subscriber_id=result[0].id
		else:
			self.subscriber_id=None
	
	@api.onchange('voucher_id')
	def onchange_voucher_id(self):
		voucher_result=self.sudo(True).env['taxivoucher'].search([('serial','=',self.voucher_id.serial)])
		if voucher_result:
			self.billing_type='voucher'
			self.client_id=voucher_result[0].client_id
			self.billable=voucher_result[0].billable
			self.buyable=voucher_result[0].buyable
		else:
			self.client_id=None
			self.client_company_ref='inconnu'
				
		#This is to free the ride field of the voucher if the ride is assigned a different voucher ref
		orig_voucher_result=self._origin.sudo(True).env['taxivoucher'].search([('serial','=',self._origin.voucher_id.serial)])
		if orig_voucher_result:
			orig_voucher_result[0].ride=None
