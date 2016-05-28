# all import
import os
from sqlite3 import dbapi2 as sqlite3
from flask import Flask,request,session,g,redirect,url_for,abort,render_template,flash,send_from_directory
from contextlib import closing
from werkzeug import check_password_hash, generate_password_hash, secure_filename

#create our little application
app = Flask(__name__)

# Load default config and override config from an environment variable
app.config.update(dict(DATABASE = os.path.join(app.root_path,'flaskr.db'),
DEBUG = True,
SECRET_KEY = 'development key',
UPLOAD_FOLDER = os.path.join(app.root_path,'file'),
ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif']),
MAX_CONTENT_LENGTH = 16*1024*1024)
)
app.config.from_envvar('FLASKR_SETTING', silent=True)

#connect to the specific database
def connect_db():
	rv = sqlite3.connect(app.config['DATABASE'])
	rv.row_factory = sqlite3.Row
	return rv

def get_db():
	"""Opens a new database connection if there is none yet for the
    current application context.
    """
	if not hasattr(g,'sqlite_db'):
		g.sqlite_db = connect_db()
	return g.sqlite_db

def init_db():
	db = get_db()
	with app.open_resource('schema.sql',mode='r') as f:
		db.cursor().executescript(f.read())
	db.commit()

def query_db(query, args=(),one=False):
	cur = get_db().execute(query,args)
	rv = cur.fetchall()
	return (rv[0] if rv else None) if one else rv

def allowed_file(filename):
	return '.' in filename and filename.rsplit('.',1)[1] in app.config['ALLOWED_EXTENSIONS'] 

@app.cli.command('initdb')
def initdb():
	'''Create the database tables.'''
	init_db()
	print('Initialize the database')

@app.teardown_appcontext
def close_db(error):
	if hasattr(g,'sqlite_db'):
		g.sqlite_db.close()


@app.before_request
def before_request():
	g.user = None
	if('user_id' in session):
		g.user = query_db('select * from user where user_id = ?',[session['user_id']],one=True)
			

@app.route('/')
def show_entries():
	if not g.user:
		return redirect(url_for('public_entries'))
	return render_template('show_entries.html', entries=query_db('''
		select message.*, user.* from message, user
        where message.author_id = user.user_id and 
            user.user_id = ? limit 30''',
        [session['user_id']]))


@app.route('/public')
def public_entries():
	return render_template('show_entries.html',entries=query_db('''
		select message.*, user.* from message, user
        where message.author_id = user.user_id limit 30'''))


@app.route('/add',methods=['POST'])
def add_entries():
	if 'user_id' not in session:
		abort(401)
	db=get_db()
	db.execute('insert into message (author_id, title, text) values (?, ?, ?)',
		[session['user_id'], request.form['title'], request.form['text']])
	db.commit()
	file = request.files['file']
	if file and allowed_file(file.filename):
		filename = secure_filename(file.filename)
		file.save(os.path.join(app.config['UPLOAD_FOLDER'],filename))
		return redirect(url_for('uploaded_file',filename=filename))
	flash('New entry was successfully posted')
	return redirect(url_for('show_entries'))


@app.route('/uploads/<filename>')
def uploaded_file(filename):
	return send_from_directory(app.config['UPLOAD_FOLDER'],filename)


@app.route('/register',methods=['GET','POST'])
def register():
	error = None
	if request.method == 'POST':
		if not request.form['username']:
			error = 'You have to enter a username'
		elif not request.form['password']:
			error = 'You have to enter a password'
		elif request.form['password']!=request.form['password2']:
			error = 'two passwords must be same'
		else:
			db = get_db()
			db.execute('''insert into user (username, pw_hash) values (?,?)''',
				[request.form['username'],generate_password_hash(request.form['password'])])
			db.commit()
			flash('You have registered successfully')
			return redirect(url_for('login'))
	return render_template('register.html',error=error)


@app.route('/login',methods=['GET','POST'])
def login():
	error = None
	if request.method == 'POST':
		user = query_db('select * from user where username = ?',[request.form['username']],one=True)
		if user is None:
			error = 'Invalid username'
		elif not check_password_hash(user['pw_hash'],request.form['password']):
			error = 'Invalid password'
		else:
			session['logged_in'] = True
			session['user_id'] = user['user_id']
			flash('You were logged in')
			return redirect(url_for('show_entries'))
	return render_template('login.html',error=error)


@app.route('/logout')
def logout():
	session.pop('logged_in',None)
	flash('You were logged out')
	return redirect(url_for('public_entries'))
