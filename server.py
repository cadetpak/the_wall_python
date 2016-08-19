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
	mquery = "SELECT first_name, last_name, users.id AS user_id, message, messages.created_at AS posted_date, messages.updated_at AS updated_date, messages.id AS message_id, messages.user_id AS mu_id FROM users JOIN messages ON users.id = messages.user_id ORDER BY posted_date DESC"
	messages = mysql.query_db(mquery)

	# THIS query joins messages, users, & comments table to display comments associated with messags, and order by oldest comments first
	cquery = "SELECT first_name, last_name, messages.id AS message_id, comment, comments.created_at as comment_date, comments.updated_at as comment_update, comments.user_id as user_id, comments.id AS comment_id FROM comments LEFT JOIN messages on comments.message_ID = messages.id LEFT JOIN users on comments.user_id = users.id ORDER BY comment_date ASC"
	comments = mysql.query_db(cquery) 

	lquery = "SELECT first_name, message, users.id AS user_id, messages.id AS message_id FROM likes LEFT JOIN users on likes.user_id = users.id LEFT JOIN messages on likes.message_id = messages.id"
	likes = mysql.query_db(lquery)

	coquery = "SELECT messages.id AS co_message_id, users.id AS co_user_id, COUNT(*) as counter FROM likes LEFT JOIN messages on likes.message_id = messages.id LEFT JOIN users on likes.user_id = users.id GROUP BY co_message_id"
	co = mysql.query_db(coquery)



	return render_template('dashboard.html', user=user, messages = messages, comments = comments, likes=likes, co=co)

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
	query = "INSERT INTO messages (message, created_at, user_id) VALUES (:message, NOW(), :user_id)" 
	data = {
		'message': message, 
		'user_id': user_id
	}
	mysql.query_db(query, data)
	# once the post has been added, refresh back to dashboard
	return redirect('/dashboard')

#Action to delete post from database
@app.route('/delete_message', methods=['POST'])
def delete():
	cquery = "DELETE FROM comments WHERE message_id = :m_id"
	cdata = {
		'm_id': request.form['message_id']
	}
	mysql.query_db(cquery, cdata)

	query = "DELETE FROM messages WHERE user_id = :id"
	data = {
		'id': request.form['user_id']
	}
	mysql.query_db(query, data)
	return redirect('/dashboard')

#Action to delete comment from databse
@app.route('/delete_comment', methods=['POST'])
def delete_comment():
	cquery = "DELETE FROM comments WHERE comments.id = :id"
	cdata = {
		'id': request.form['comment_id']
	}
	mysql.query_db(cquery, cdata)
	return redirect('/dashboard')


# Action to add comments to messages in DB
@app.route('/post_comment', methods=['POST'])
def comment():
	comment = request.form['comment']
	user_id = request.form['user_id']
	message_id = request.form['message_id']
	query = "INSERT INTO comments (comment, created_at, message_id, user_id) VALUES (:comment, NOW(), :message_id, :user_id)"
	data = {
		'comment': comment, 
		'message_id': message_id,
		'user_id': user_id
	}
	mysql.query_db(query, data)
	# once the comment has been added to message, refresh dashboard
	return redirect('/dashboard')

# Action to 'LIKE' a post
@app.route('/like', methods=['POST'])
def like():
	user_id = request.form['user_id']
	message_id = request.form['message_id']
	query = "INSERT INTO likes (user_id, message_id) VALUES (:user_id, :message_id)"
	data = {
		'user_id': user_id,
		'message_id': message_id,
	}
	mysql.query_db(query, data)
	return redirect('/dashboard')

@app.route('/edit/<id>', methods=['GET'])
def edit(id):
	# THIS query sets session for user logging in
	query = "SELECT * FROM users WHERE id = :id LIMIT 1"
	data = {
		'id': session['id']
	}
	user = mysql.query_db(query, data)
	
	mquery = "SELECT * FROM messages WHERE messages.id = :id"
	mdata = {
		'id': id, 
	}
	message = mysql.query_db(mquery, mdata)
	return render_template('edit.html', message = message, user=user)

@app.route('/edit_comment/<id>', methods=['GET'])
def editcomment(id):
	cquery = "SELECT * FROM comments WHERE comments.id = :id"
	cdata = {
		'id': id, 
	}
	comment = mysql.query_db(cquery, cdata)
	return render_template('editc.html', comment = comment)

@app.route('/update', methods=['POST'])
def update():

	message = request.form['message']
	message_id = request.form['message_id']
	query = "UPDATE messages SET message = :message, updated_at = NOW() WHERE messages.id = :message_id"	
	data = {
		'message': message,
		'message_id': message_id,
	}

	mysql.query_db(query, data)
	return redirect('/dashboard')

@app.route('/update_comment', methods=['POST'])
def updatec():
	comment = request.form['message']
	comment_id = request.form['comment_id']
	query = "UPDATE comments SET comment = :comment, updated_at = NOW() WHERE comments.id = :comment_id"
	data = {
		'comment': comment,
		'comment_id': comment_id,
	}
	mysql.query_db(query, data)
	return redirect('/dashboard')



app.run(debug = True)