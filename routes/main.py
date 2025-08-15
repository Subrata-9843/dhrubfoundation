from flask import render_template, request, flash, redirect, url_for
from dhrubfoundation.routes import main_bp
from dhrubfoundation.models import Donation, Event
from dhrubfoundation.forms import ContactForm

@main_bp.route('/')
def home():
    return render_template('index.html')

@main_bp.route('/about')
def about():
    return render_template('about.html')

@main_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    form = ContactForm()
    if form.validate_on_submit():
        # Process form data
        flash('Your message has been sent!', 'success')
        return redirect(url_for('main.home'))
    return render_template('contact.html', form=form)

@main_bp.route('/events')
def events():
    events = Event.query.filter(Event.date >= datetime.utcnow()).order_by(Event.date.asc()).all()
    return render_template('events.html', events=events)