from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, ValidationError, FloatField, IntegerField
from wtforms.validators import DataRequired, Length, Email, EqualTo

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=30)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6, max=128)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    emailId = StringField('Email', validators=[DataRequired(), Email(), Length(max=50)])
    name = StringField('Name', validators=[DataRequired(), Length(max=50)])
    address = StringField('Address', validators=[DataRequired(), Length(max=100)])
    pincode = StringField('Pincode', validators=[DataRequired(), Length(max=10)])
    submit = SubmitField('Register')

    def validate_username(self, username):
        from parkingManagement.modals import User
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username already exists. Please choose a different one.')

    def validate_emailId(self, emailId):
        from parkingManagement.modals import User
        user = User.query.filter_by(emailId=emailId.data).first()
        if user:
            raise ValidationError('Email already registered. Please use a different email.')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class ParkingLotForm(FlaskForm):
    prime_location = StringField('Prime Location', validators=[DataRequired(), Length(max=100)])
    address = StringField('Address', validators=[DataRequired(), Length(max=100)])
    pincode = StringField('Pincode', validators=[DataRequired(), Length(max=10)])
    price_per_hour = FloatField('Price Per Hour', validators=[DataRequired()])
    max_spots = IntegerField('Max Spots', validators=[DataRequired()])
    submit = SubmitField('Create')