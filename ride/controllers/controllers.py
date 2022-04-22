# -*- coding: utf-8 -*-
# from odoo import http


# class Addons/ecurie(http.Controller):
#     @http.route('/addons/ecurie/addons/ecurie/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/addons/ecurie/addons/ecurie/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('addons/ecurie.listing', {
#             'root': '/addons/ecurie/addons/ecurie',
#             'objects': http.request.env['addons/ecurie.addons/ecurie'].search([]),
#         })

#     @http.route('/addons/ecurie/addons/ecurie/objects/<model("addons/ecurie.addons/ecurie"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('addons/ecurie.object', {
#             'object': obj
#         })
