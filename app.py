import os
import uuid
import io
import json
import qrcode
import pandas as pd
import logging
from datetime import datetime, timezone, timedelta
from contextlib import redirect_stderr

from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from flask_wtf import FlaskForm, CSRFProtect
from wtforms import StringField, PasswordField, BooleanField, SelectField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
from sqlalchemy.sql import func
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_wtf.file import FileField, FileRequired, FileAllowed

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure environment
from dotenv import load_dotenv
load_dotenv()

# Suppress WeasyPrint warnings
os.environ['GIO_EXTRA_MODULES'] = ''
os.environ['GIO_MODULE_DIR'] = ''
try:
    from weasyprint import HTML
except ImportError:
    raise ImportError(
        "WeasyPrint dependencies not installed. Please install them first:\n"
        "Windows: Download GTK3 Runtime from https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases\n"
        "Mac: brew install cairo pango gdk-pixbuf libffi\n"
        "Linux: sudo apt-get install libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev"
    )

# Create Flask app
app = Flask(__name__)

# --------------------------
# Configuration
# --------------------------
app.config.update({
    'SECRET_KEY': os.getenv('SECRET_KEY', 'change-me-to-a-random-secret'),
    'WTF_CSRF_SECRET_KEY': os.getenv('WTF_CSRF_SECRET_KEY', 'change-me-too'),
    'SQLALCHEMY_DATABASE_URI': os.getenv('DATABASE_URL', 'sqlite:///donations.db'),
    'SQLALCHEMY_TRACK_MODIFICATIONS': False,
    'UPLOAD_FOLDER': os.path.join('static', 'uploads'),
    'MAX_CONTENT_LENGTH': 100 * 1024 * 1024,  # 100MB
    'ALLOWED_EXTENSIONS': {'png', 'jpg', 'jpeg', 'gif', 'webp', 'mp4', 'webm', 'ogg'},
    'MAIL_SERVER': os.getenv('MAIL_SERVER', 'smtp.gmail.com'),
    'MAIL_PORT': int(os.getenv('MAIL_PORT', 587)),
    'MAIL_USE_TLS': os.getenv('MAIL_USE_TLS', 'True').lower() in ('1', 'true', 'yes'),
    'MAIL_USERNAME': os.getenv('MAIL_USERNAME'),
    'MAIL_PASSWORD': os.getenv('MAIL_PASSWORD'),
    'MAIL_DEFAULT_SENDER': os.getenv('MAIL_DEFAULT_SENDER', 'noreply@dhrubfoundation.org'),
    'SERVER_NAME': os.getenv('SERVER_NAME', 'dhrubfoundation.org'),
    'PREFERRED_URL_SCHEME': 'https',
    'SESSION_COOKIE_SECURE': True,
    'REMEMBER_COOKIE_SECURE': True,
    'SESSION_COOKIE_HTTPONLY': True,
    'SESSION_COOKIE_SAMESITE': 'Lax',
})

# File paths
INVOICE_DIR = os.path.join('static', 'donation_data', 'invoices')
QR_DIR = os.path.join('static', 'qr')
MEMBER_IMAGE_DIR = os.path.join('static', 'images', 'members')
MEMBERS_JSON = os.path.join('static', 'data', 'members.json')

# Initialize extensions
db = SQLAlchemy(app)
mail = Mail(app)
login_manager = LoginManager(app)
login_manager.login_view = 'admin_login'
csrf = CSRFProtect(app)

# Fix proxy headers
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# --------------------------
# Models
# --------------------------
class Admin(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default='viewer')
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.Integer, db.ForeignKey('admin.id'))
    created_at = db.Column(db.DateTime, server_default=func.now())
    reset_token = db.Column(db.String(200))
    reset_token_expires = db.Column(db.DateTime)
    creator = db.relationship('Admin', remote_side=[id])

class AdminActivity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('admin.id'))
    activity = db.Column(db.String(200))
    ip_address = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, server_default=func.now())
    admin = db.relationship('Admin', backref='activities')

class Donation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    provider = db.Column(db.String(50))
    account_number = db.Column(db.String(50))
    ifsc = db.Column(db.String(20))
    transaction_ref = db.Column(db.String(100))
    timestamp = db.Column(db.DateTime, server_default=func.now())
    invoice_path = db.Column(db.String(200))
    qr_path = db.Column(db.String(200))
    is_verified = db.Column(db.Boolean, default=False)
    verified_by = db.Column(db.Integer, db.ForeignKey('admin.id'))
    verified_at = db.Column(db.DateTime)

# --------------------------
# Forms
# --------------------------
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')

class AdminForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    role = SelectField('Role', choices=[('master','Master'),('manager','Manager'),('viewer','Viewer')])
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save')

class ForgotPasswordForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Request Reset Link')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('New Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Reset Password')

class UploadForm(FlaskForm):
    files = FileField('Select Images', validators=[
        FileRequired(),
        FileAllowed(['png', 'jpg', 'jpeg', 'gif', 'webp'], 'Images only!')
    ])
    category = SelectField('Category', choices=[
        ('gallery', 'Gallery'),
        ('events', 'Events'),
        ('team', 'Team'),
        ('projects', 'Projects')
    ])
    visibility = SelectField('Visibility', choices=[
        ('public', 'Public'),
        ('private', 'Private'),
        ('members', 'Members Only')
    ])
    submit = SubmitField('Upload')

# --------------------------
# Utilities
# --------------------------
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@login_manager.user_loader
def load_user(admin_id):
    try:
        return Admin.query.get(int(admin_id))
    except Exception:
        return None

def log_admin_activity(activity):
    try:
        if current_user.is_authenticated:
            db.session.add(AdminActivity(
                admin_id=current_user.id,
                activity=activity,
                ip_address=request.remote_addr
            ))
            db.session.commit()
    except Exception:
        app.logger.exception("Failed to log admin activity")

def has_permission(perm):
    permissions = {
        'master': ['view_dashboard', 'manage_donations', 'manage_admins', 'system_settings'],
        'manager': ['view_dashboard', 'manage_donations'],
        'viewer': ['view_dashboard']
    }
    return current_user.is_authenticated and (
        current_user.role == 'master' or perm in permissions.get(current_user.role, [])
    )

def get_members_data():
    try:
        with open(MEMBERS_JSON) as f:
            return json.load(f)
    except Exception:
        return {'founders': [], 'admin': []}

def generate_qr(amount):
    os.makedirs(QR_DIR, exist_ok=True)
    uri = f"upi://pay?pa=dhrub@upi&pn=Dhrub Foundation&am={amount}&cu=INR"
    img = qrcode.make(uri)
    fn = f"{uuid.uuid4().hex}_qr.png"
    qr_path = os.path.join(QR_DIR, fn)
    img.save(qr_path)
    return fn

def generate_invoice_pdf(data):
    os.makedirs(INVOICE_DIR, exist_ok=True)
    html = render_template('invoice_template.html', donation=data)
    fn = f"invoice_{uuid.uuid4().hex[:8]}.pdf"
    path = os.path.join(INVOICE_DIR, fn)
    # suppress stderr noise from WeasyPrint
    with redirect_stderr(io.StringIO()):
        HTML(string=html).write_pdf(path)
    return fn

# --------------------------
# Initialize DB and filesystem
# --------------------------
with app.app_context():
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(INVOICE_DIR, exist_ok=True)
    os.makedirs(QR_DIR, exist_ok=True)
    os.makedirs(MEMBER_IMAGE_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(MEMBERS_JSON), exist_ok=True)
    os.makedirs(os.path.join('static', 'donation_data'), exist_ok=True)
    db.create_all()
    if not Admin.query.first():
        master = Admin(
            username=os.getenv('DEFAULT_ADMIN_USER', 'admin'),
            email=os.getenv('DEFAULT_ADMIN_EMAIL', 'admin@dhrubfoundation.org'),
            password_hash=generate_password_hash(os.getenv('DEFAULT_ADMIN_PASSWORD', 'admin123')),
            role='master',
            is_active=True
        )
        db.session.add(master)
        db.session.commit()

# --------------------------
# Routes
# --------------------------
@app.route('/')
def home():
    upload_folder = app.config['UPLOAD_FOLDER']
    images = []
    if os.path.exists(upload_folder):
        images = [f for f in os.listdir(upload_folder) if allowed_file(f)]
    return render_template('home.html', featured_images=images[-3:])

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/programs')
def programs():
    return render_template('programs.html')

@app.route('/gallery')
def gallery():
    upload_folder = app.config['UPLOAD_FOLDER']
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)
        media_files = []
    else:
        media_files = [
            f for f in os.listdir(upload_folder)
            if os.path.isfile(os.path.join(upload_folder, f)) and allowed_file(f)
        ]
    images = [f for f in media_files if f.split('.')[-1].lower() in {'png', 'jpg', 'jpeg', 'gif', 'webp'}]
    videos = [f for f in media_files if f.split('.')[-1].lower() in {'mp4', 'webm', 'ogg'}]
    return render_template('gallery.html', images=images)

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/members')
def members():
    try:
        with open(MEMBERS_JSON) as f:
            members_data = json.load(f)
    except Exception as e:
        app.logger.exception("Error loading members data")
        members_data = {'founders': [], 'admin': []}
    return render_template('members.html',
                           founders=members_data.get('founders', []),
                           admin=members_data.get('admin', []))

@app.route('/donate', methods=['GET', 'POST'])
def donate():
    if request.method == 'POST':
        errors = {}
        name = request.form.get('name','').strip()
        email = request.form.get('email','').strip()
        amount = request.form.get('amount','').strip()
        provider = request.form.get('provider')
        acct = request.form.get('account_number','').strip()
        ifsc = request.form.get('ifsc','').strip()
        tref = request.form.get('transaction_id','').strip()

        if not name: errors['name'] = "Required"
        if not email: errors['email'] = "Required"
        try:
            amount = float(amount)
            if amount <= 0: errors['amount'] = "Must be > 0"
        except:
            errors['amount'] = "Invalid"

        if errors:
            return render_template('donate.html', error=errors, request=request)

        data = {
            'name': name,
            'email': email,
            'amount': amount,
            'provider': provider,
            'account_number': acct,
            'ifsc': ifsc,
            'transaction_id': tref,
            'date': datetime.now().strftime('%d-%m-%Y %H:%M')
        }

        qr_fn = generate_qr(amount)
        inv_fn = generate_invoice_pdf(data)

        donation = Donation(
            name=name,
            email=email,
            amount=amount,
            provider=provider,
            account_number=acct,
            ifsc=ifsc,
            transaction_ref=tref,
            qr_path=os.path.join('qr', qr_fn),
            invoice_path=os.path.join('donation_data', 'invoices', inv_fn)
        )
        db.session.add(donation)
        db.session.commit()

        qr_url = url_for('static', filename=f'qr/{qr_fn}')
        inv_url = url_for('static', filename=f'donation_data/invoices/{inv_fn}')
        upi_uri = f"upi://pay?pa=dhrub@upi&pn=Dhrub Foundation&am={amount}&cu=INR"
        deep = {
            'gpay': f"intent://{upi_uri[6:]}#Intent;package=com.google.android.apps.nbu.paisa.user;end",
            'phonepe': f"intent://{upi_uri[6:]}#Intent;package=com.phonepe.app;end"
        }.get(provider, upi_uri)

        return render_template('donate.html', qr_url=qr_url, invoice_url=inv_url, deep_link=deep, transaction_id=tref)

    return render_template('donate.html')

# --- Admin Routes ---
@app.route('/admin/login', methods=['GET','POST'])
def admin_login():
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        admin = Admin.query.filter_by(username=form.username.data).first()
        if admin and check_password_hash(admin.password_hash, form.password.data):
            if admin.is_active:
                login_user(admin, remember=form.remember.data)
                admin.last_login = datetime.now(timezone.utc)
                db.session.commit()
                log_admin_activity('Logged in')
                flash('Logged in successfully', 'success')
                return redirect(url_for('admin_dashboard'))
            flash('Account disabled', 'danger')
        else:
            flash('Invalid credentials', 'danger')
    return render_template('admin_login.html', form=form)

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if not has_permission('view_dashboard'):
        flash('Forbidden', 'danger'); return redirect(url_for('admin_login'))
    log_admin_activity('Viewed dashboard')
    total = Donation.query.count()
    total_amt = db.session.query(func.sum(Donation.amount)).scalar() or 0
    recent = Donation.query.order_by(Donation.timestamp.desc()).limit(5).all()
    activities = AdminActivity.query.order_by(AdminActivity.created_at.desc()).limit(5).all()
    return render_template('admin_dashboard.html', total_donations=total,
                           total_amount=total_amt, recent_donations=recent,
                           recent_activities=activities)

@app.route('/admin/donations')
@login_required
def view_donations():
    if not has_permission('manage_donations'):
        flash('Forbidden', 'danger'); return redirect(url_for('admin_dashboard'))
    log_admin_activity('Viewed donations')
    q = Donation.query
    f_email = request.args.get('email','').lower()
    if f_email: q = q.filter(Donation.email.ilike(f'%{f_email}%'))
    f_provider = request.args.get('provider','')
    if f_provider: q = q.filter(Donation.provider.ilike(f'%{f_provider}%'))
    start = request.args.get('start_date','')
    if start:
        try:
            dt = datetime.strptime(start, '%Y-%m-%d')
            q = q.filter(Donation.timestamp >= dt)
        except:
            flash('Bad start date', 'warning')
    end = request.args.get('end_date','')
    if end:
        try:
            dt2 = datetime.strptime(end, '%Y-%m-%d') + timedelta(days=1)
            q = q.filter(Donation.timestamp <= dt2)
        except:
            flash('Bad end date', 'warning')
    donations = q.order_by(Donation.timestamp.desc()).all()

    total = len(donations)
    verified_count = sum(1 for d in donations if d.is_verified)
    total_amt = sum(d.amount for d in donations)
    avg_amt = total_amt / total if total else 0
    recent = donations[:5]

    return render_template('view_donations.html', donations=donations,
                           summary={'total_donations': total, 'verified_count': verified_count,
                                    'total_amount': total_amt, 'average_amount': avg_amt,
                                    'recent_donations': recent},
                           email_filter=f_email, provider_filter=f_provider,
                           start_date=start, end_date=end)

@app.route('/admin/donations/verify/<int:id>', methods=['POST'])
@login_required
def verify_donation(id):
    if not has_permission('manage_donations'):
        flash('Forbidden', 'danger'); return redirect(url_for('view_donations'))
    d = Donation.query.get_or_404(id)
    d.is_verified = not d.is_verified
    d.verified_by = current_user.id
    d.verified_at = datetime.now(timezone.utc)
    db.session.commit()
    log_admin_activity(f"{'Verified' if d.is_verified else 'Unverified'} donation {id}")
    flash('Status updated', 'success')
    return redirect(url_for('view_donations'))

@app.route('/admin/donations/export/<format>')
@login_required
def export_donations(format):
    if not has_permission('manage_donations'):
        flash('Forbidden', 'danger'); return redirect(url_for('view_donations'))
    ds = Donation.query.all()
    if not ds:
        flash('No donations to export', 'info'); return redirect(url_for('view_donations'))
    df = pd.DataFrame([{
            'ID': d.id,
            'Name': d.name,
            'Email': d.email,
            'Amount': d.amount,
            'Provider': d.provider,
            'Date': d.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            'Verified': 'Yes' if d.is_verified else 'No'
        } for d in ds])
    fn = f"donations_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    if format=='excel':
        fn += '.xlsx'; path = os.path.join('static', 'donation_data', fn)
        df.to_excel(path, index=False); m='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    elif format=='csv':
        fn += '.csv'; path = os.path.join('static', 'donation_data', fn)
        df.to_csv(path, index=False); m='text/csv'
    else:
        flash('Invalid format', 'danger'); return redirect(url_for('view_donations'))
    send = send_file(path, as_attachment=True, mimetype=m)
    log_admin_activity(f"Exported donations as {format}")
    return send

@app.route('/admin/manage', methods=['GET'])
@login_required
def manage_admins():
    if not has_permission('manage_admins'):
        flash('Forbidden', 'danger'); return redirect(url_for('admin_dashboard'))
    log_admin_activity('Viewed admins')
    admins = Admin.query.all()
    return render_template('admin_management.html', admins=admins)

@app.route('/admin/create', methods=['GET','POST'])
@login_required
def create_admin():
    if not has_permission('manage_admins'):
        flash('Forbidden', 'danger'); return redirect(url_for('admin_dashboard'))
    form = AdminForm()
    if form.validate_on_submit():
        admin = Admin(username=form.username.data, email=form.email.data,
                      password_hash=generate_password_hash(form.password.data),
                      role=form.role.data, is_active=form.is_active.data,
                      created_by=current_user.id)
        db.session.add(admin); db.session.commit()
        log_admin_activity(f"Created admin {admin.username}")
        flash('Admin added', 'success')
        return redirect(url_for('manage_admins'))
    return render_template('edit_admin.html', form=form, is_new=True)

@app.route('/admin/edit/<int:aid>', methods=['GET','POST'])
@login_required
def edit_admin(aid):
    if not has_permission('manage_admins'):
        flash('Forbidden', 'danger'); return redirect(url_for('admin_dashboard'))
    admin = Admin.query.get_or_404(aid)
    form = AdminForm(obj=admin)
    if form.validate_on_submit():
        admin.username = form.username.data
        admin.email = form.email.data
        if form.password.data:
            admin.password_hash = generate_password_hash(form.password.data)
        admin.role = form.role.data
        admin.is_active = form.is_active.data
        db.session.commit()
        log_admin_activity(f"Updated admin {admin.username}")
        flash('Admin updated', 'success')
        return redirect(url_for('manage_admins'))
    return render_template('edit_admin.html', form=form, is_new=False)

@app.route('/admin/toggle/<int:aid>', methods=['POST'])
@login_required
def toggle_admin(aid):
    if not has_permission('manage_admins'):
        flash('Forbidden', 'danger'); return redirect(url_for('admin_dashboard'))
    admin = Admin.query.get_or_404(aid)
    if admin.id == current_user.id:
        flash('Cannot disable yourself', 'danger')
    else:
        admin.is_active = not admin.is_active
        db.session.commit()
        log_admin_activity(f"{'Enabled' if admin.is_active else 'Disabled'} admin {admin.username}")
        flash('Status changed', 'success')
    return redirect(url_for('manage_admins'))

@app.route('/admin/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if not has_permission('manage_donations'):
        flash('Forbidden', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    form = UploadForm()
    if form.validate_on_submit():
        files = request.files.getlist('files')
        category = form.category.data
        visibility = form.visibility.data
        
        upload_path = os.path.join(app.config['UPLOAD_FOLDER'], category)
        os.makedirs(upload_path, exist_ok=True)
        
        success_count = 0
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(f"{uuid.uuid4().hex}_{file.filename}")
                file.save(os.path.join(upload_path, filename))
                success_count += 1
        
        if success_count > 0:
            flash(f'Successfully uploaded {success_count} file(s)', 'success')
        else:
            flash('No valid files uploaded', 'error')
        
        return redirect(url_for('upload'))
    
    return render_template('uploads.html', form=form)

@app.route('/admin/delete-media/<fname>', methods=['POST'])
@login_required
def delete_media(fname):
    if not has_permission('manage_donations'):
        flash('Forbidden', 'danger'); return redirect(url_for('admin_dashboard'))
    
    upload_folder = app.config['UPLOAD_FOLDER']
    path = os.path.join(upload_folder, fname)
    
    if os.path.exists(path):
        os.remove(path)
        log_admin_activity(f"Deleted {fname}")
        flash('Deleted', 'success')
    else:
        flash('Not found', 'danger')
    return redirect(url_for('gallery'))

@app.route('/forgot-password', methods=['GET','POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard'))
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        admin = Admin.query.filter_by(email=form.email.data).first()
        if admin:
            serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
            token = serializer.dumps(admin.email, salt='password-reset')
            admin.reset_token = token
            admin.reset_token_expires = datetime.now(timezone.utc) + timedelta(hours=1)
            db.session.commit()
            urlt = url_for('reset_password', token=token, _external=True)
            msg = Message('Reset Your Password', recipients=[admin.email])
            msg.body = f"Click or visit {urlt}\nLink valid for 1 hour."
            try:
                mail.send(msg)
                flash('Reset link sent', 'info')
            except Exception:
                app.logger.exception("Failed to send reset email")
                flash('Failed to send email. Contact admin.', 'danger')
            return redirect(url_for('admin_login'))
        flash('No account found', 'warning')
    return render_template('forgot_password.html', form=form)

@app.route('/reset-password/<token>', methods=['GET','POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard'))
    admin = Admin.query.filter_by(reset_token=token).first()
    if not admin or admin.reset_token_expires < datetime.now(timezone.utc):
        flash('Invalid or expired link', 'danger'); return redirect(url_for('forgot_password'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        admin.password_hash = generate_password_hash(form.password.data)
        admin.reset_token = None
        admin.reset_token_expires = None
        db.session.commit()
        flash('Password updated', 'success')
        return redirect(url_for('admin_login'))
    return render_template('reset_password.html', form=form)

@app.route('/admin/logout')
@login_required
def admin_logout():
    log_admin_activity('Logged out')
    logout_user()
    flash('You have been logged out', 'success')
    return redirect(url_for('admin_login'))

@app.route('/privacy')
def privacy():
    return render_template('privacy.html', now=datetime.now(timezone.utc))

# Error handlers
@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(403)
def forbidden(e):
    return render_template('403.html'), 403

@app.errorhandler(500)
def internal_error(e):
    db.session.rollback()
    return render_template('500.html'), 500

# --------------------------
# Production Entry Point
# --------------------------
if __name__ == '__main__':
    # This will only run in development
    port = int(os.getenv('PORT', 8000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() in ('1', 'true', 'yes')
    app.run(host='0.0.0.0', port=port, debug=debug)
else:
    # This runs in production (Gunicorn)
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)