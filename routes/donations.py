from flask import render_template, request, flash, redirect, url_for
from dhrubfoundation.routes import donatations_bp
from dhrubfoundation.models import Donation
from dhrubfoundation.forms import DonationForm

@donations_bp.route('/donate', methods=['GET', 'POST'])
def donate():
    form = DonationForm()
    if form.validate_on_submit():
        # Process donation
        donation = Donation(
            amount=form.amount.data,
            donor_name=form.name.data,
            email=form.email.data,
            payment_method=form.payment_method.data
        )
        db.session.add(donation)
        db.session.commit()
        flash('Thank you for your donation!', 'success')
        return redirect(url_for('donations.thank_you'))
    return render_template('donations/donate.html', form=form)

@donations_bp.route('/thank-you')
def thank_you():
    return render_template('donations/thank_you.html')