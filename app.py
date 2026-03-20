from flask import Flask, render_template, url_for, flash, redirect, request, jsonify
from models import db, User, Category, Skill, Feedback, Comment, Like, ContactMessage
from forms import RegistrationForm, LoginForm, SkillForm, ContactForm, FeedbackForm, CommentForm, UpdateAccountForm
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, login_user, current_user, logout_user, login_required
from flask_wtf.csrf import CSRFProtect
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = '5791628bb0b13ce0c676dfde280ba245'
# Use an absolute path for SQLite to avoid confusion
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'site.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
bcrypt = Bcrypt(app)
csrf = CSRFProtect(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    """Load user by user_id."""
    return User.query.get(int(user_id))

# Initialize the database within app context
with app.app_context():
    db.create_all()
    # Populate categories if empty
    if not Category.query.first():
        categories = ['Programming', 'Design', 'Marketing', 'Writing', 'Music']
        for cat_name in categories:
            cat = Category(name=cat_name)
            db.session.add(cat)
        db.session.commit()
    
    # Ensure admin user exists
    admin_email = 'sanjeevadmin@gmail.com'
    if not User.query.filter_by(email=admin_email).first():
        hashed_pw = bcrypt.generate_password_hash('1234').decode('utf-8')
        admin_user = User(username='AdminSanjeev', email=admin_email, password=hashed_pw, is_admin=True)
        db.session.add(admin_user)
        db.session.commit()

@app.route("/")
@app.route("/home")
def home():
    """Render the landing page."""
    # Fetch the latest 6 skills to display on the home page
    skills = Skill.query.order_by(Skill.date_posted.desc()).limit(6).all()
    return render_template('index.html', skills=skills)

@app.route("/about")
def about():
    """Render the about page."""
    return render_template('about.html')

@app.route("/contact", methods=['GET', 'POST'])
def contact():
    """Render and handle the contact form."""
    form = ContactForm()
    if form.validate_on_submit():
        msg = ContactMessage(
            name=form.name.data,
            email=form.email.data,
            subject=form.subject.data,
            message=form.message.data
        )
        db.session.add(msg)
        db.session.commit()
        flash('Thank you for contacting us. We will get back to you shortly.', 'success')
        return redirect(url_for('home'))
    
    messages = []
    if current_user.is_authenticated and current_user.is_admin:
        messages = ContactMessage.query.order_by(ContactMessage.date_posted.desc()).all()
        
    return render_template('contact.html', form=form, messages=messages)

@app.route("/feedback", methods=['GET', 'POST'])
@login_required
def feedback():
    """Render and handle the feedback form."""
    form = FeedbackForm()
    if form.validate_on_submit():
        feedback_entry = Feedback(message=form.message.data, author=current_user)
        db.session.add(feedback_entry)
        db.session.commit()
        flash('Thank you for your feedback!', 'success')
        return redirect(url_for('feedback'))
    if current_user.is_admin:
        feedbacks = Feedback.query.order_by(Feedback.date_posted.desc()).all()
    else:
        feedbacks = Feedback.query.filter_by(user_id=current_user.id).order_by(Feedback.date_posted.desc()).all()
    return render_template('feedback.html', form=form, feedbacks=feedbacks)

@app.route("/register", methods=['GET', 'POST'])
def register():
    """Handle user registration."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = RegistrationForm()
    if form.validate_on_submit():
        # Hash the password for security
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

@app.route("/login", methods=['GET', 'POST'])
def login():
    """Handle user login."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        # Verify user and password
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)

@app.route("/logout")
def logout():
    """Log out the current user."""
    logout_user()
    return redirect(url_for('home'))

@app.route("/dashboard")
@login_required
def dashboard():
    """View user skills dashboard."""
    # Query all skills submitted by current user
    skills = Skill.query.filter_by(author=current_user).order_by(Skill.date_posted.desc()).all()
    return render_template('dashboard.html', title='Dashboard', skills=skills)

@app.route("/admin")
@login_required
def admin_panel():
    """Dedicated Admin Dashboard."""
    if not current_user.is_admin:
        flash('You do not have permission to access that page.', 'danger')
        return redirect(url_for('dashboard'))
    users = User.query.order_by(User.id).all()
    skills = Skill.query.order_by(Skill.date_posted.desc()).all()
    feedbacks = Feedback.query.order_by(Feedback.date_posted.desc()).all()
    return render_template('admin_dashboard.html', title='Admin Panel', users=users, skills=skills, feedbacks=feedbacks)

@app.route("/admin/user/<int:user_id>/delete", methods=['POST'])
@login_required
def admin_delete_user(user_id):
    """Admin function to delete a user and their skills."""
    if not current_user.is_admin:
        flash('You do not have permission to perform this action.', 'danger')
        return redirect(url_for('dashboard'))
    
    user = User.query.get_or_404(user_id)
    if user.is_admin:
        flash('Cannot delete an admin account.', 'danger')
        return redirect(url_for('admin_panel'))
        
    # Manually delete user's skills first to respect SQLite cascade limits
    for skill in user.skills:
        db.session.delete(skill)
        
    db.session.delete(user)
    db.session.commit()
    flash(f"User {user.username} has been deleted.", 'success')
    return redirect(url_for('admin_panel'))

@app.route("/search")
def search():
    """Handle search functionality for skills."""
    query = request.args.get('q', '')
    if query:
        # Search for titles or descriptions matching the query
        search_term = f"%{query}%"
        skills = Skill.query.filter(
            (Skill.title.ilike(search_term)) | 
            (Skill.description.ilike(search_term))
        ).order_by(Skill.date_posted.desc()).all()
    else:
        skills = []
    return render_template('search_results.html', title='Search Results', skills=skills, query=query)

@app.route("/user/<username>")
def user_profile(username):
    """View a user's profile and their skills."""
    user = User.query.filter_by(username=username).first_or_404()
    skills = Skill.query.filter_by(author=user).order_by(Skill.date_posted.desc()).all()
    return render_template('user_profile.html', user=user, skills=skills)

@app.route("/skill/<int:skill_id>", methods=['GET', 'POST'])
@login_required
def skill(skill_id):
    """View a skill and its comments, and allow adding comments."""
    skill = Skill.query.get_or_404(skill_id)
    form = CommentForm()
    if form.validate_on_submit():
        comment = Comment(content=form.content.data, author=current_user, skill=skill)
        db.session.add(comment)
        db.session.commit()
        flash('Your comment has been added!', 'success')
        return redirect(url_for('skill', skill_id=skill.id))
    comments = Comment.query.filter_by(skill_id=skill_id).order_by(Comment.date_posted).all()
    likes_count = Like.query.filter_by(skill_id=skill_id).count()
    user_liked = Like.query.filter_by(user_id=current_user.id, skill_id=skill_id).first() is not None
    return render_template('skill.html', skill=skill, comments=comments, form=form, likes_count=likes_count, user_liked=user_liked)

@app.route("/like/<int:skill_id>", methods=['POST'])
@login_required
def like_skill(skill_id):
    """Toggle like on a skill."""
    skill = Skill.query.get_or_404(skill_id)
    like = Like.query.filter_by(user_id=current_user.id, skill_id=skill_id).first()
    if like:
        db.session.delete(like)
        db.session.commit()
        liked = False
    else:
        like = Like(user_id=current_user.id, skill_id=skill_id)
        db.session.add(like)
        db.session.commit()
        liked = True
    count = Like.query.filter_by(skill_id=skill_id).count()
    return jsonify({'liked': liked, 'count': count})

@app.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    """Manage user profile."""
    form = UpdateAccountForm()
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your account has been updated!', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    return render_template('account.html', title='Account', form=form)

@app.route("/skill/new", methods=['GET', 'POST'])
@login_required
def new_skill():
    """Create a new skill."""
    form = SkillForm()
    # Load categories from DB
    form.category_id.choices = [(c.id, c.name) for c in Category.query.all()]
    if form.validate_on_submit():
        skill = Skill(title=form.title.data, description=form.description.data, 
                      category_id=form.category_id.data, author=current_user)
        db.session.add(skill)
        db.session.commit()
        flash('Your skill has been created!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('skill_form.html', title='New Skill', form=form, legend='New Skill')

@app.route("/skill/<int:skill_id>/update", methods=['GET', 'POST'])
@login_required
def update_skill(skill_id):
    """Edit an existing skill."""
    skill = Skill.query.get_or_404(skill_id)
    if skill.author != current_user and not current_user.is_admin:
        flash('You do not have permission to edit this skill.', 'danger')
        return redirect(url_for('dashboard'))
    form = SkillForm()
    form.category_id.choices = [(c.id, c.name) for c in Category.query.all()]
    if form.validate_on_submit():
        skill.title = form.title.data
        skill.category_id = form.category_id.data
        skill.description = form.description.data
        db.session.commit()
        flash('Your skill has been updated!', 'success')
        return redirect(url_for('dashboard'))
    elif request.method == 'GET':
        form.title.data = skill.title
        form.category_id.data = skill.category_id
        form.description.data = skill.description
    return render_template('skill_form.html', title='Update Skill', form=form, legend='Update Skill')

@app.route("/skill/<int:skill_id>/delete", methods=['POST'])
@login_required
def delete_skill(skill_id):
    """Delete a skill."""
    skill = Skill.query.get_or_404(skill_id)
    if skill.author != current_user and not current_user.is_admin:
        flash('You do not have permission to delete this skill.', 'danger')
        return redirect(url_for('dashboard'))
    db.session.delete(skill)
    db.session.commit()
    flash('Your skill has been deleted!', 'success')
    return redirect(url_for('dashboard'))

@app.route("/admin/feedback/<int:feedback_id>/delete", methods=['POST'])
@login_required
def admin_delete_feedback(feedback_id):
    """Admin function to delete a feedback entry."""
    if not current_user.is_admin:
        flash('You do not have permission to perform this action.', 'danger')
        return redirect(url_for('dashboard'))
    
    feedback = Feedback.query.get_or_404(feedback_id)
    db.session.delete(feedback)
    db.session.commit()
    flash('Feedback has been deleted.', 'success')
    return redirect(url_for('admin_panel'))

@app.route("/admin/contact/<int:msg_id>/delete", methods=['POST'])
@login_required
def admin_delete_contact(msg_id):
    """Admin function to delete a contact message."""
    if not current_user.is_admin:
        flash('You do not have permission to perform this action.', 'danger')
        return redirect(url_for('dashboard'))
    
    msg = ContactMessage.query.get_or_404(msg_id)
    db.session.delete(msg)
    db.session.commit()
    flash('Contact message has been deleted.', 'success')
    return redirect(url_for('contact'))

@app.errorhandler(404)
def error_404(error):
    """Render the custom 404 page."""
    return render_template('404.html'), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)

