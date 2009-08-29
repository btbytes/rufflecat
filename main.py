#!/usr/bin/env python

import os 
import time       
import random
import functools
import wsgiref.handlers               
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.api import users
from sessions import Session

class MyRequestHandler(webapp.RequestHandler):    
    def __init__(self,**kw):
        webapp.RequestHandler.__init__(MyRequestHandler, **kw)
        self.session = Session()
        
    def render(self, tmpl, **kw):
        template_values = dict(**kw)
        template_values.update({'user': users.get_current_user()})
        template_values.update({'users': users})
        path = os.path.join(os.path.dirname(__file__), 'templates', tmpl)
        self.response.out.write(template.render(path, template_values))
       
def logged_in(method):
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        user = users.get_current_user()
        if not user:
            if self.request.method == "GET":
                self.redirect(users.create_login_url(self.request.uri))
                return
            else:      
                names = get_names(self.request)
                self.session['names'] = self.session.get('names', names)
                self.session['ruffled'] = self.session.get('ruffled', [])
                self.redirect(users.create_login_url(self.request.uri))
                return
        else:
            return method(self, *args, **kwargs)
    return wrapper

def get_names(request):
    text = request.get("names")
    names = text.split('\n')[:10] # limit to 10
    return names


        
class Names(db.Model):
    author = db.UserProperty(required=True)
    title = db.StringProperty(required=True)
    names = db.StringListProperty()
    ruffled =  db.StringListProperty()
    created = db.DateTimeProperty(auto_now_add=True) 

class SaveHandler(MyRequestHandler):
    @logged_in
    def get(self):               
        entries = self.session.get('names')
        self.render('save.html', entries=entries)
                   
    @logged_in    
    def post(self):
        alt =  time.strftime("%a, %d %b %Y") # Fri, 28 Aug 2008
        title = self.request.get('title', 'x') 
        entry = Names(author=users.get_current_user(),
            title=title,
            names=self.session.get('names'),
            ruffled=self.session.get('ruffled'),
        ) 
        entry.save()
        self.redirect('/')

class FavHandler(MyRequestHandler):
    def get(self, slug):
        item = Names.get(slug)
        if item:
            self.render("single.html", item=item)
        else:
            self.render("404.html") 

class DelHandler(MyRequestHandler):
    def post(self, slug):
        item = Names.get(slug)
        if item and item.author==users.get_current_user():
            item.delete()
            self.redirect('/f')
        else:
            self.render("404.html") 

class ListFavsHandler(MyRequestHandler):
    def get(self):
        favs = Names.all().filter('author  = ',users.get_current_user()).order('-created')
        self.render("favs.html", favs=favs)
        
class MainHandler(MyRequestHandler):
    def get(self):
        text = '\n'.join(self.session.get('names', []))
        restart = self.request.get('r')
        if restart:
            self.session.flush() 
            self.redirect('/')
        else:
            self.render("index.html", text=text)
        
    def post(self):                                
        names = get_names(self.request) 
        ruffled = random.sample(names, len(names))
        self.session['names'] = names
        self.session['ruffled'] = ruffled
        self.render("results.html", entries=ruffled)
        

def main():
    application = webapp.WSGIApplication([('/', MainHandler),
        ('/s', SaveHandler),       
        ('/f', ListFavsHandler),       
        ('/f/([^/]+)', FavHandler),
        ('/d/([^/]+)', DelHandler),
        
        ], debug=True)
    wsgiref.handlers.CGIHandler().run(application)


if __name__ == '__main__':
    main()
