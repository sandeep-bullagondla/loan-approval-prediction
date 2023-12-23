# Flask
from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy 
from flask_migrate import Migrate 
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user, current_user 
from werkzeug.security import generate_password_hash, check_password_hash 
from sqlalchemy import CheckConstraint
# Data manipulation
import pandas as pd
# Matrices manipulation
import numpy as np
# Script logging
import logging
# ML model
import joblib
# JSON manipulation
import json
# Utilities
import sys
import os 


# Current directory
current_dir = os.path.dirname(__file__)

# Flask app
app = Flask(__name__, static_folder = 'static', template_folder = 'template')

# Logging
app.logger.addHandler(logging.StreamHandler(sys.stdout))
app.logger.setLevel(logging.ERROR)
##################################################################
basedir = os.path.abspath(os.path.dirname(__file__)) 
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'data.sqlite') 
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'mykey' 

db = SQLAlchemy(app) 

Migrate(app, db) 

login_manager = LoginManager()
login_manager.init_app(app) 
login_manager.login_view = 'login' 

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

class User(db.Model, UserMixin): 
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key = True) 
    username = db.Column(db.String(12), unique = True, nullable = False) 
    password_hash = db.Column(db.String(64)) 
    name = db.Column(db.Text)
    __table_args__ = (
        CheckConstraint('LENGTH(username) >= 8 AND LENGTH(username)<=12'),
    )

    def __init__(self, username, password, name): 
        self.username = username 
        self.password_hash= generate_password_hash(password) 
        self.name = name
    
    def check_password(self, password): 
        return check_password_hash(self.password_hash, password)



# Function
def ValuePredictor(data = pd.DataFrame):
	# Model name
	model_name = 'bin/xgboostModel.pkl'
	# Directory where the model is stored
	model_dir = os.path.join(current_dir, model_name)
	# Load the model
	loaded_model = joblib.load(open(model_dir, 'rb'))
	# Predict the data
	result = loaded_model.predict(data)
	return result[0]

# Home page
@app.route('/')
def home():
	return render_template('index.html') 

@app.route('/register', methods = ['GET', 'POST'])
def register(): 
	if request.method == 'POST':
		name = request.form.get('name')
		username = request.form.get('username')
		password = request.form.get('password')
		confirm_password = request.form.get('confirm_password') 
		if len(username)>= 8 and len(username) <= 12: 
			if password == confirm_password: 
				if not User.query.filter_by(username = username).first(): 
					user = User(username,password, name)
					db.session.add(user)
					db.session.commit()
					return redirect(url_for('login')) 
				else: 
					return render_template('register.html', username_exists = username) 
			else: 
				return render_template('register.html', password = password) 
		elif password is not confirm_password: 
			return render_template('register.html', username = username, password = password) 
		return render_template('register.html', username = username)
	return render_template('register.html')

@app.route('/login', methods = ['GET', 'POST'])
def login(): 
	if request.method == 'POST': 
		username = request.form.get('username')
		password = request.form.get('password') 
		user = User.query.filter_by(username = username).first() 
		if user is not None and user.check_password(password): 
			login_user(user)
			next = request.args.get('next')
			if next == None or not next[0] == '/': 
				return render_template('index.html', name = user.name)
			return redirect(next) 
		else:
			return render_template('login.html', credentials = user)
		
	return render_template('login.html')


# Prediction page
@app.route('/prediction', methods = ['POST'])
@login_required
def predict():
	if request.method == 'POST':
		# Get the data from form
		name = request.form['name']
		gender = request.form['gender']
		education = request.form['education']
		self_employed = request.form['self_employed']
		marital_status = request.form['marital_status']
		dependents = request.form['dependents']
		applicant_income = request.form['applicant_income']
		coapplicant_income = request.form['coapplicant_income']
		loan_amount = request.form['loan_amount']
		loan_term = request.form['loan_term']
		credit_history = request.form['credit_history']
		property_area = request.form['property_area']

		# Load template of JSON file containing columns name
		# Schema name
		schema_name = 'data/columns_set.json'
		# Directory where the schema is stored
		schema_dir = os.path.join(current_dir, schema_name)
		with open(schema_dir, 'r') as f:
			cols =  json.loads(f.read())
		schema_cols = cols['data_columns']

		# Parse the categorical columns
		# Column of dependents
		try:
			col = ('Dependents_' + str(dependents))
			if col in schema_cols.keys():
				schema_cols[col] = 1
			else:
				pass
		except:
			pass
		# Column of property area
		try:
			col = ('Property_Area_' + str(property_area))
			if col in schema_cols.keys():
				schema_cols[col] = 1
			else:
				pass
		except:
			pass

		# Parse the numerical columns
		schema_cols['ApplicantIncome'] = applicant_income
		schema_cols['CoapplicantIncome'] = coapplicant_income
		schema_cols['LoanAmount'] = loan_amount
		schema_cols['Loan_Amount_Term'] = loan_term
		schema_cols['Gender_Male'] = gender
		schema_cols['Married_Yes'] = marital_status
		schema_cols['Education_Not Graduate'] = education
		schema_cols['Self_Employed_Yes'] = self_employed
		schema_cols['Credit_History_1.0'] = credit_history

		# Convert the JSON into data frame
		df = pd.DataFrame(
				data = {k: [v] for k, v in schema_cols.items()},
				dtype = float
			)

		# Create a prediction
		print(df.dtypes)
		result = ValuePredictor(data = df)

		# Determine the output
		if int(result) == 1:
			prediction = 'Dear Mr/Mrs/Ms {name}, your loan is approved!'.format(name = name)
		else:
			prediction = 'Sorry Mr/Mrs/Ms {name}, your loan is rejected!'.format(name = name)

		# Return the prediction
		return render_template('prediction.html', prediction = prediction)
	
	# Something error
	else:
		# Return error
		return render_template('error.html', prediction = prediction)

if __name__ == '__main__':
    app.run(debug = True)