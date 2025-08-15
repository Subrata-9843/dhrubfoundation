from flask import render_template, flash, redirect, url_for
from flask_login import login_required, current_user
from app.routes import admin_bp
from app.models import Donation, User
from app.forms import AdminEventForm

@admin_bp.route('/')
@login_required
def dashboard():
    if not current_user.is_admin:
        flash('Access denied', 'danger')
        return redirect(url_for('main.home'))
    
    donations = Donation.query.order_by(Donation.date.desc()).limit(10).all()
    return render_template('admin/dashboard.html', donations=donations)

@admin_bp.route('/create-event', methods=['GET', 'POST'])
@login_required
def create_event():
    form = AdminEventForm()
    if form.validate_on_submit():
        # Save event logic
        flash('Event created successfully!', 'success')
        return redirect(url_for('admin.dashboard'))
    return render_template('admin/create_event.html', form=form)