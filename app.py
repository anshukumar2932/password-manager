from flask import Flask, render_template, request, redirect, url_for, session, flash,get_flashed_messages
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from db import init_db, create_user, get_user_by_userid, get_user_data, update_password, add_user_data
from datetime import timedelta

app = Flask(__name__)
app.secret_key = "supersecretkey"
app.permanent_session_lifetime = timedelta(minutes=30)

# Initialize Flask-Login
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Initialize the database
init_db()

# User model
class User(UserMixin):
    def __init__(self, user_id):
        self.id = user_id

@login_manager.user_loader
def load_user(user_id):
    user_data = get_user_by_userid(user_id)
    return User(user_data['user']) if user_data else None

@app.before_request
def redirect_authenticated_user():
    """Redirect authenticated users to their protected page."""
    if current_user.is_authenticated and request.endpoint in ['login', 'signup']:
        return redirect(url_for('protected', username=current_user.id))

@app.route('/')
def home():
    """Home route redirects to login or protected page based on authentication."""
    return redirect(url_for('login') if not current_user.is_authenticated else url_for('protected', username=current_user.id))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login."""
    session.clear()  # Clear previous session data
    if request.method == 'POST':
        user = request.form['user']
        password = request.form['password']

        user_data = get_user_by_userid(user)
        if user_data and check_password_hash(user_data['password'], password):
            login_user(User(user))
            session.permanent = True
            return redirect(url_for('protected', username=current_user.id))

        flash("Invalid credentials")
    return render_template('login_signup.html', mode="login")

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """Handle user registration."""
    if request.method == 'POST':
        user = request.form['user']
        password = request.form['password']

        if get_user_by_userid(user):
            flash("User already exists")
        else:
            create_user(user, generate_password_hash(password, method='pbkdf2:sha256'))
            flash("Signup successful. Please log in.")
            return redirect(url_for('login'))

    return render_template('login_signup.html', mode="signup")

@app.route('/protected/<username>')
@login_required
def protected(username):
    """Protected route accessible only to authenticated users."""
    if username != current_user.id:
        return "Unauthorized", 403
    return render_template('index.html', username=current_user.id)

@app.route('/logout', methods=['POST'])
@login_required
def logout():
    """Handle user logout."""
    logout_user()
    session.clear()
    flash("Logged out successfully")
    return redirect(url_for('login'))

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Handle password recovery process."""
    if request.method == 'POST':
        username = request.form.get('username')
        new_password = request.form.get('new_password')

        if username:
            user_data = get_user_by_userid(username)
            if not user_data:
                flash("User does not exist!")
            elif new_password:
                reset_session_username = reset_session.pop('user', None)
                if reset_session_username:
                    update_password(reset_session_username, generate_password_hash(new_password, method='pbkdf2:sha256'))
                    flash("Password updated successfully!")
                    return redirect(url_for('login'))
                flash("Session expired, please start over.")
                return render_template('forgot_password.html', email_form=False)
            else:
                reset_session['user'] = username
                return render_template('forgot_password.html', email_form=False)

        flash("An error occurred. Please try again.")
    return render_template('forgot_password.html', email_form=True)

@app.route('/protected/add_password', methods=['GET', 'POST'])
@login_required
def add_password():
    """Allow users to add password-protected data."""
    if request.method == 'POST':
        user = request.form.get('user')
        password = request.form.get('password')
        if add_user_data(current_user.id, user, password):
            flash("Successfully added data")
        else:
            flash("An error occurred.")
    return render_template('index.html', username=current_user.id, mode="Add")

@app.route('/protected/view_password', methods=['GET'])
@login_required
def view_password():
    """Allow users to view their saved password-protected data."""
    credentials = get_user_data(current_user.id)
    return render_template('index.html', username=current_user.id, mode="View", credentials=credentials)

if __name__ == "__main__":
    app.run(debug=True)
