from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, FloatField, TextAreaField, DateTimeField, BooleanField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, Length, NumberRange, Optional

class ContactForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    message = TextAreaField('Message', validators=[DataRequired(), Length(min=10)])
    submit = SubmitField('Send Message')

class DonationForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    amount = FloatField('Amount', validators=[DataRequired(), NumberRange(min=1)])
    payment_method = SelectField('Payment Method', 
                               choices=[('credit', 'Credit Card'), 
                                        ('paypal', 'PayPal'), 
                                        ('bank', 'Bank Transfer')],
                               validators=[DataRequired()])
    is_anonymous = BooleanField('Donate Anonymously')
    submit = SubmitField('Donate Now')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')

class AdminEventForm(FlaskForm):
    title = StringField('Event Title', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    date = DateTimeField('Event Date', format='%Y-%m-%d %H:%M', validators=[DataRequired()])
    location = StringField('Location', validators=[DataRequired()])
    submit = SubmitField('Create Event')