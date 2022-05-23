from msilib.schema import LockPermissions
from flask import Flask, flash, render_template , request, session, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from datetime import datetime 
import json
import os
from werkzeug.utils import secure_filename
import math

                          
with open("config.json", "r") as config :           #opening configuration file of json as config 
    params = json.load(config)["parameters"]        #parsing and loading the key i.e., parameters of json file into variable params in py file 
    
local_server = params['local_server']     

app = Flask(__name__)
app.secret_key = 'super-secret-key'
app.config.update(          #SMTP
    MAIL_SERVER = 'smtp.gmail.com',         
    MAIL_PORT = '465',
    MAIL_USE_SSL = True,
    MAIL_USERNAME = params['gmail-user'],
    MAIL_PASSWORD=  params['gmail-password']
)
app.config['UPLOAD_FOLDER'] = params['upload_location']
mail = Mail(app)


if local_server == True :
    app.config['SQLALCHEMY_DATABASE_URI'] = params['local_URI'] 
else :
    app.config['SQLALCHEMY_DATABASE_URI'] = params['prod_URI']  #contains username and password of database present in configuration file

db = SQLAlchemy(app)    #initialisation

class Contacts(db.Model):
    ''' table contacts and its fields :
        sno name email phone_num msg date
    '''
    sno = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=False, nullable=False)  #null is True by default
    email = db.Column(db.String(120), unique=False, nullable=False)
    phone_num = db.Column(db.String(120), unique=False, nullable=False)
    msg = db.Column(db.String(120), unique=False, nullable=False)
    date = db.Column(db.String(120), unique=False, nullable=False)

class Posts(db.Model):
    ''' table posts and its fields :
        sno title sub_title slug content date
    '''
    sno = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80), unique=False, nullable=False)  
    tagline = db.Column(db.String(80), unique=False, nullable=False)
    slug = db.Column(db.String(25), unique=False, nullable=False)
    content= db.Column(db.String(120), unique=False, nullable=False)
    date = db.Column(db.String(12), unique=False, nullable=False)
    img_file = db.Column(db.String(12), nullable=True)
    
    
@app.route("/")
def home():

    '''Pagination logic
    First Page
        prev = #
        next =  page+1
    Second Page
        prev = page - 1
        next =  page + 1
    Third Page
        prev = page - 1
        next =  #
    '''

    posts = Posts.query.filter_by().all()                                          #[0:params['no_of_post']]                                 #all() returns list, we can use python slicing 
    last = math.ceil(len(posts)/int(params['no_of_posts']))                        #returns the smallest integer greater than or equal to x
    page= request.args.get('page')
    if(not str(page).isnumeric()) :
        page=1
    page=int(page)
    posts = posts[(page-1)*int(params['no_of_posts']):(page-1)*int(params['no_of_posts'])+ int(params['no_of_posts'])] #slicing posts according to req posts in one page
    if page==1:
        prev = "#"
        next = "/?page="+ str(page+1)
    elif page==last:
        prev = "/?page="+ str(page-1)
        next = "#"
    else:
        prev = "/?page="+ str(page-1)
        next = "/?page="+ str(page+1)

    return render_template('index.html',params=params,posts=posts, prev=prev, next=next)              #lhs params for using in html to access parameters from json via params variable in py file

@app.route("/about")
def about():
    return render_template('about.html',params=params)

@app.route("/dashboard", methods=["GET","POST"])
def dashboard():

    #if already logged in
    if 'user' in session and session['user'] == params['admin_user'] :  
        posts= Posts.query.all()
        return render_template("dashboard.html", params=params, posts=posts)

    # For REDIRECTECTING TO ADMIN PANEL after logging in
    if request.method=="POST":
        username= request.form.get('uname')
        userpass= request.form.get('pass')
        if username==params['admin_user'] and userpass==params['admin_password']:
            # set the session variable
            session['user'] = username
            posts= Posts.query.all()
            return render_template("dashboard.html", params=params, posts=posts)
        else:
            return render_template("login.html", params=params)

    else:
        return render_template("login.html", params=params)

@app.route("/logout")
def logout():
    session.pop('user')
    return redirect('/dashboard')


@app.route("/edit/<string:sno>" , methods=['GET', 'POST'])
def edit(sno):
    if "user" in session and session['user']==params['admin_user']:
        if request.method=="POST":
            box_title = request.form.get('title')
            tline = request.form.get('tline')
            slug = request.form.get('slug')
            content = request.form.get('content')
            img_file = request.form.get('img_file')
            date = datetime.now()
        
            if sno=='0':
                post = Posts(title=box_title, slug=slug, content=content, tagline=tline, img_file=img_file, date=date)
                db.session.add(post)
                db.session.commit()
               
            else:
                post = Posts.query.filter_by(sno=sno).first()
                post.box_title = box_title
                post.tline = tline
                post.slug = slug
                post.content = content
                post.img_file = img_file
                post.date = date
                db.session.commit()
                return redirect('/edit/'+ sno)

        post = Posts.query.filter_by(sno=sno).first()
        return render_template('edit.html', params=params, post=post, sno=sno)

@app.route("/delete/<string:sno>" , methods=['GET', 'POST'])
def delete(sno):
    if "user" in session and session['user']==params['admin_user']:
        post=Posts.query.filter_by(sno=sno).first()
        db.session.delete(post)
        db.session.commit()
        return redirect('/dashboard')



@app.route("/uploader", methods=['GET',"POST"])
def uploader() :
    if "user" in session and session['user']==params['admin_user']:
        if request.method == 'POST':
            f= request.files['file1']
            f.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(f.filename)))
            return "uploaded successfully"

@app.route("/post/<string:post_slug>", methods=['GET'])
def post_route(post_slug):
    post = Posts.query.filter_by(slug=post_slug).first()  
    return render_template('post.html', params=params,post=post )

@app.route("/contact", methods=["GET","POST"]) 
def contact():
    if(request.method =='POST'):
        '''adding entry to db
        fetching what we entered in the form in different labels accordingly'''
        name = request.form.get('name')  
        email = request.form.get('email')
        phone = request.form.get('phone')
        message = request.form.get('message')
        entry = Contacts(name=name, email=email, phone_num=phone, msg=message , date=datetime.now())
        mail.send_message('New Message from '+ name,
         sender = email, 
         recipients = [params['gmail-user']],
         body = message + "\n" + phone + "\n" + email
         )
        db.session.add(entry)
        db.session.commit()
    return render_template('contact.html',params=params)




app.run(debug=True)
