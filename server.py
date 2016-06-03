from flask import Flask, request, redirect, render_template, flash, session
# Need MySQLConnector to connect to database!
from mysqlconnection import MySQLConnector
# Need Bcrypt to crypt passwords generated
from flask.ext.bcrypt import Bcrypt
import re
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9\.\+_-]+@[a-zA-Z0-9\._-]+\.[a-zA-Z]*$')
app = Flask(__name__)
bcrypt = Bcrypt(app)
app.secret_key = "lkjf83kd"
# 'wall' is name of database which I've already created with tables
mysql = MySQLConnector(app, 'wall')


# Root page, which will display login/registration forms
@app.route('/')
def index(): 
	return render_template('index.html')

# Action to register - validates user input
@app.route('/register', methods=['POST'])
def validate(): 
	first_name = request.form['first_name']
	last_name = request.form['last_name']
	email = request.form['email']
	password = request.form['password']
	password_confirmation = request.form['password_confirmation']
	# NEED this line to crypt passwords before adding to DB
	pw_hash = bcrypt.generate_password_hash(password)

	#validations..
	if len(first_name) < 1: 
		flash('First Name cannot be empty!')
	elif len(last_name) < 1: 
		flash('Last Name cannot be empty!')
	elif not EMAIL_REGEX.match(email): 
		flash("Email is not valid!")
	elif len(password) < 8: 
		flash("Password must be at least 8 characters!")
	elif password != password_confirmation: 
		flash("Passwords do not match!")
	# if all validations pass... add to db
	else: 
		query = "INSERT INTO users (first_name, last_name, email, password, created_at, updated_at) VALUES (:first_name, :last_name, :email, :password, NOW(), NOW())"
		data = {
			'first_name': first_name, 
			'last_name': last_name, 
			'email': email, 
			'password': pw_hash
		}
		mysql.query_db(query, data)
		flash('Successfully registered new user!  Please login to access THE WALL!')
	# whether successful or not, redirect back to main page!
	return redirect('/')

# Action to login - validates user input to db
@app.route('/login', methods=['POST'])
def login(): 
	email = request.form['email']
	password = request.form['password']
	#query to find matching email
	query = "SELECT * FROM users WHERE email = :email LIMIT 1"
	data = {
		'email': email
	}
	user = mysql.query_db(query, data)
	# Once the email is found in DB.. 
	if bcrypt.check_password_hash(user[0]['password'], password): 
		# if password matches, set session for id
		session['id'] = user[0]['id']
		# then direct to 'dashboard' action
		return redirect('/dashboard')
	else: 
		#flash error message and redirect to main
		flash('Email/Password do not match! Try again!')
		return redirect('/')

# Action to load User's unique dashboard 
@app.route('/dashboard', methods=['GET'])
def dashboard(): 
	# THIS query sets session for user logging in
	query = "SELECT * FROM users WHERE id = :id LIMIT 1"
	data = {
		'id': session['id']
	}
	user = mysql.query_db(query, data)
	# THIS query joins Messages & Users table, and pulls out data I will display on dashboard, and order by newest posts first
	mquery = "SELECT first_name, last_name, users.id AS user_id, message, messages.created_at AS posted_date, messages.id AS message_id, messages.user_id AS mu_id FROM users LEFT JOIN messages ON users.id = messages.user_id ORDER BY posted_date DESC"
	messages = mysql.query_db(mquery)

	# THIS query joins messages, users, & comments table to display comments associated with messags, and order by newest comments first
	cquery = "SELECT first_name, last_name, messages.id AS message_id, comment, comments.created_at as comment_date FROM comments LEFT JOIN messages on comments.message_ID = messages.id LEFT JOIN users on comments.user_id = users.id ORDER BY comment_date DESC"
	comments = mysql.query_db(cquery) 

	return render_template('dashboard.html', user=user, messages = messages, comments = comments)

# Action to Logout User (clear session)
@app.route('/logout')
def logout(): 
	session.clear()
	return redirect('/')

# Action to add posted message to database
@app.route('/post_message', methods=['POST'])
def message(): 
	message = request.form['message']
	user_id = request.form['user_id']
	query = "INSERT INTO messages (message, created_at, updated_at, user_id) VALUES (:message, NOW(), NOW(), :user_id)" 
	data = {
		'message': message, 
		'user_id': user_id
	}
	mysql.query_db(query, data)
	# once the post has been added, refresh back to dashboard
	return redirect('/dashboard')

# Action to add comments to messages in DB
@app.route('/post_comment', methods=['POST'])
def comment():
	comment = request.form['comment']
	user_id = request.form['user_id']
	message_id = request.form['message_id']
	query = "INSERT INTO comments (comment, created_at, updated_at, message_id, user_id) VALUES (:comment, NOW(), NOW(), :message_id, :user_id)"
	data = {
		'comment': comment, 
		'message_id': message_id,
		'user_id': user_id
	}
	mysql.query_db(query, data)
	# once the comment has been added to message, refresh dashboard
	return redirect('/dashboard')



app.run(debug = True)