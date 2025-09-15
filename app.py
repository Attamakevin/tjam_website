"""
Triumphant Jesus Adoration Ministry (TJAM) Website
Flask Application - Fixed Version
"""

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import re
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tjam.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# Create upload directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'admin_login'

# Template context processor to make current year available in templates
@app.context_processor
def inject_current_year():
    return {'current_year': datetime.now().year}

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class BlogPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    excerpt = db.Column(db.String(300))
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    author = db.relationship('User', backref=db.backref('posts', lazy=True))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    featured_image = db.Column(db.String(200))
    is_published = db.Column(db.Boolean, default=True)

class AdorationVideo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    youtube_url = db.Column(db.String(300), nullable=False)
    youtube_id = db.Column(db.String(50))
    thumbnail_url = db.Column(db.String(300))
    duration = db.Column(db.String(20))
    uploaded_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    uploader = db.relationship('User', backref=db.backref('videos', lazy=True))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_featured = db.Column(db.Boolean, default=False)
    view_count = db.Column(db.Integer, default=0)

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    event_date = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(200))
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    creator = db.relationship('User', backref=db.backref('events', lazy=True))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_recurring = db.Column(db.Boolean, default=False)
    category = db.Column(db.String(50), default='general')

class Prayer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_featured = db.Column(db.Boolean, default=False)

class Testimony(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120))
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_approved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    subject = db.Column(db.String(200))
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class LiveStream(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    stream_url = db.Column(db.String(500))
    stream_type = db.Column(db.String(50), default='youtube')
    is_live = db.Column(db.Boolean, default=False)
    viewer_count = db.Column(db.Integer, default=0)
    started_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AdorationSchedule(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    day_of_week = db.Column(db.Integer)  # 0=Monday, 6=Sunday, None=daily
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Helper Functions
def extract_youtube_id(url):
    """Extract YouTube video ID from URL"""
    youtube_regex = re.compile(
        r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/'
        r'(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
    )
    match = youtube_regex.match(url)
    return match.group(6) if match else None

def get_youtube_thumbnail(youtube_id):
    """Get YouTube thumbnail URL"""
    return f"https://img.youtube.com/vi/{youtube_id}/maxresdefault.jpg"

# Routes
@app.route('/')
def index():
    """Homepage with featured content"""
    try:
        featured_videos = AdorationVideo.query.filter_by(is_featured=True).limit(3).all()
        recent_posts = BlogPost.query.filter_by(is_published=True).order_by(BlogPost.created_at.desc()).limit(3).all()
        upcoming_events = Event.query.filter(Event.event_date > datetime.utcnow()).order_by(Event.event_date).limit(3).all()
        featured_prayers = Prayer.query.filter_by(is_featured=True).limit(2).all()
        
        return render_template('index.html', 
                             featured_videos=featured_videos,
                             recent_posts=recent_posts,
                             upcoming_events=upcoming_events,
                             featured_prayers=featured_prayers)
    except Exception as e:
        app.logger.error(f"Error loading homepage: {e}")
        flash('An error occurred loading the homepage.', 'error')
        return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/ministries')
def ministries():
    return render_template('ministries.html')

@app.route('/blog')
def blog():
    page = request.args.get('page', 1, type=int)
    try:
        posts = BlogPost.query.filter_by(is_published=True).order_by(BlogPost.created_at.desc()).paginate(
            per_page=6, page=page, error_out=False)
        return render_template('blog.html', posts=posts)
    except Exception as e:
        app.logger.error(f"Error loading blog: {e}")
        flash('An error occurred loading the blog.', 'error')
        return redirect(url_for('index'))

@app.route('/blog/<int:post_id>')
def blog_post(post_id):
    post = BlogPost.query.get_or_404(post_id)
    if not post.is_published:
        flash('This post is not available.', 'error')
        return redirect(url_for('blog'))
    
    # Get related posts
    related_posts = BlogPost.query.filter(
        BlogPost.id != post_id, 
        BlogPost.is_published == True
    ).order_by(BlogPost.created_at.desc()).limit(3).all()
    
    return render_template('blog_post.html', post=post, related_posts=related_posts)

@app.route('/adoration-videos')
def adoration_videos():
    page = request.args.get('page', 1, type=int)
    try:
        videos = AdorationVideo.query.order_by(AdorationVideo.created_at.desc()).paginate(
            per_page=9, page=page, error_out=False)
        return render_template('adoration_videos.html', videos=videos)
    except Exception as e:
        app.logger.error(f"Error loading videos: {e}")
        flash('An error occurred loading the videos.', 'error')
        return redirect(url_for('index'))

@app.route('/video/<int:video_id>')
def video_detail(video_id):
    video = AdorationVideo.query.get_or_404(video_id)
    
    try:
        # Increment view count
        video.view_count += 1
        db.session.commit()
    except Exception as e:
        app.logger.error(f"Error updating view count: {e}")
    
    # Get related videos
    related_videos = AdorationVideo.query.filter(AdorationVideo.id != video_id).limit(4).all()
    
    return render_template('video_detail.html', video=video, related_videos=related_videos)

@app.route('/events')
def events():
    try:
        upcoming = Event.query.filter(Event.event_date > datetime.utcnow()).order_by(Event.event_date).all()
        past = Event.query.filter(Event.event_date <= datetime.utcnow()).order_by(Event.event_date.desc()).limit(10).all()
        return render_template('events.html', upcoming=upcoming, past=past)
    except Exception as e:
        app.logger.error(f"Error loading events: {e}")
        flash('An error occurred loading events.', 'error')
        return redirect(url_for('index'))

@app.route('/prayers')
def prayers():
    category = request.args.get('category', 'all')
    try:
        if category == 'all':
            prayers = Prayer.query.order_by(Prayer.created_at.desc()).all()
        else:
            prayers = Prayer.query.filter_by(category=category).order_by(Prayer.created_at.desc()).all()
        
        categories = db.session.query(Prayer.category).distinct().all()
        categories = [cat[0] for cat in categories if cat[0]]
        
        return render_template('prayers.html', prayers=prayers, categories=categories, current_category=category)
    except Exception as e:
        app.logger.error(f"Error loading prayers: {e}")
        flash('An error occurred loading prayers.', 'error')
        return redirect(url_for('index'))

@app.route('/prayer/<int:prayer_id>')
def prayer_detail(prayer_id):
    prayer = Prayer.query.get_or_404(prayer_id)
    return render_template('prayer_detail.html', prayer=prayer)

@app.route('/testimonies')
def testimonies():
    try:
        testimonies = Testimony.query.filter_by(is_approved=True).order_by(Testimony.created_at.desc()).all()
        return render_template('testimonies.html', testimonies=testimonies)
    except Exception as e:
        app.logger.error(f"Error loading testimonies: {e}")
        flash('An error occurred loading testimonies.', 'error')
        return redirect(url_for('index'))

@app.route('/submit-testimony', methods=['GET', 'POST'])
def submit_testimony():
    if request.method == 'POST':
        try:
            # Validate required fields
            if not request.form.get('name') or not request.form.get('title') or not request.form.get('content'):
                flash('Please fill in all required fields.', 'error')
                return render_template('submit_testimony.html')
            
            testimony = Testimony(
                name=request.form['name'],
                email=request.form.get('email'),
                title=request.form['title'],
                content=request.form['content']
            )
            db.session.add(testimony)
            db.session.commit()
            flash('Thank you for sharing your testimony! It will be reviewed before publishing.', 'success')
            return redirect(url_for('testimonies'))
        except Exception as e:
            app.logger.error(f"Error submitting testimony: {e}")
            flash('An error occurred while submitting your testimony. Please try again.', 'error')
    
    return render_template('submit_testimony.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        try:
            # Validate required fields
            if not request.form.get('name') or not request.form.get('email') or not request.form.get('message'):
                flash('Please fill in all required fields.', 'error')
                return render_template('contact.html')
            
            contact = Contact(
                name=request.form['name'],
                email=request.form['email'],
                subject=request.form.get('subject'),
                message=request.form['message']
            )
            db.session.add(contact)
            db.session.commit()
            flash('Your message has been sent successfully! We will get back to you soon.', 'success')
            return redirect(url_for('contact'))
        except Exception as e:
            app.logger.error(f"Error submitting contact form: {e}")
            flash('An error occurred while sending your message. Please try again.', 'error')
    
    return render_template('contact.html')

@app.route('/live-adoration')
def live_adoration():
    return render_template('live_adoration.html')

@app.route('/donate')
def donate():
    return render_template('donate.html')

# Admin Routes
@app.route('/admin')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('index'))
    
    try:
        # Dashboard statistics
        stats = {
            'total_posts': BlogPost.query.count(),
            'total_videos': AdorationVideo.query.count(),
            'total_events': Event.query.count(),
            'pending_testimonies': Testimony.query.filter_by(is_approved=False).count(),
            'unread_messages': Contact.query.filter_by(is_read=False).count()
        }
        
        recent_posts = BlogPost.query.order_by(BlogPost.created_at.desc()).limit(5).all()
        recent_videos = AdorationVideo.query.order_by(AdorationVideo.created_at.desc()).limit(5).all()
        
        return render_template('admin/dashboard.html', stats=stats, recent_posts=recent_posts, recent_videos=recent_videos)
    except Exception as e:
        app.logger.error(f"Error loading admin dashboard: {e}")
        flash('An error occurred loading the dashboard.', 'error')
        return redirect(url_for('index'))

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        try:
            username = request.form['username']
            password = request.form['password']
            user = User.query.filter_by(username=username).first()
            
            if user and check_password_hash(user.password_hash, password):
                login_user(user)
                next_page = request.args.get('next')
                return redirect(next_page) if next_page else redirect(url_for('admin_dashboard'))
            else:
                flash('Invalid username or password', 'error')
        except Exception as e:
            app.logger.error(f"Error during login: {e}")
            flash('An error occurred during login. Please try again.', 'error')
    
    return render_template('admin/login.html')

@app.route('/admin/logout')
@login_required
def admin_logout():
    logout_user()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('index'))

@app.route('/admin/posts')
@login_required
def admin_posts():
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    try:
        posts = BlogPost.query.order_by(BlogPost.created_at.desc()).all()
        return render_template('admin/posts.html', posts=posts)
    except Exception as e:
        app.logger.error(f"Error loading admin posts: {e}")
        flash('An error occurred loading posts.', 'error')
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/posts/new', methods=['GET', 'POST'])
@login_required
def admin_new_post():
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        try:
            # Validate required fields
            if not request.form.get('title') or not request.form.get('content'):
                flash('Please fill in all required fields.', 'error')
                return render_template('admin/post_form.html')
            
            post = BlogPost(
                title=request.form['title'],
                content=request.form['content'],
                excerpt=request.form.get('excerpt'),
                author_id=current_user.id,
                is_published=bool(request.form.get('is_published'))
            )
            db.session.add(post)
            db.session.commit()
            flash('Post created successfully!', 'success')
            return redirect(url_for('admin_posts'))
        except Exception as e:
            app.logger.error(f"Error creating post: {e}")
            flash('An error occurred while creating the post. Please try again.', 'error')
    
    return render_template('admin/post_form.html')

@app.route('/admin/posts/<int:post_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_edit_post(post_id):
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    post = BlogPost.query.get_or_404(post_id)
    
    if request.method == 'POST':
        try:
            post.title = request.form['title']
            post.content = request.form['content']
            post.excerpt = request.form.get('excerpt')
            post.is_published = bool(request.form.get('is_published'))
            post.updated_at = datetime.utcnow()
            
            # Handle file upload
            if 'featured_image' in request.files:
                file = request.files['featured_image']
                if file.filename:
                    # Delete old image if exists
                    if post.featured_image:
                        old_image_path = os.path.join(app.config['UPLOAD_FOLDER'], post.featured_image)
                        if os.path.exists(old_image_path):
                            os.remove(old_image_path)
                    
                    # Save new image
                    featured_image = save_uploaded_file(file)
                    if featured_image:
                        post.featured_image = featured_image
                    else:
                        flash('Invalid image file. Image not updated.', 'warning')
            
            db.session.commit()
            flash('Post updated successfully!', 'success')
            return redirect(url_for('admin_posts'))
        except Exception as e:
            app.logger.error(f"Error updating post: {e}")
            flash('An error occurred while updating the post. Please try again.', 'error')
    
    return render_template('admin/post_form.html', post=post)

@app.route('/admin/posts/<int:post_id>/delete', methods=['POST'])
@login_required
def admin_delete_post(post_id):
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    try:
        post = BlogPost.query.get_or_404(post_id)
        db.session.delete(post)
        db.session.commit()
        flash('Post deleted successfully!', 'success')
    except Exception as e:
        app.logger.error(f"Error deleting post: {e}")
        flash('An error occurred while deleting the post.', 'error')
    
    return redirect(url_for('admin_posts'))

@app.route('/admin/videos')
@login_required
def admin_videos():
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    try:
        videos = AdorationVideo.query.order_by(AdorationVideo.created_at.desc()).all()
        return render_template('admin/videos.html', videos=videos)
    except Exception as e:
        app.logger.error(f"Error loading admin videos: {e}")
        flash('An error occurred loading videos.', 'error')
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/videos/new', methods=['GET', 'POST'])
@login_required
def admin_new_video():
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        try:
            youtube_url = request.form['youtube_url']
            youtube_id = extract_youtube_id(youtube_url)
            
            if not youtube_id:
                flash('Invalid YouTube URL. Please provide a valid YouTube video URL.', 'error')
                return render_template('admin/video_form.html')
            
            video = AdorationVideo(
                title=request.form['title'],
                description=request.form.get('description'),
                youtube_url=youtube_url,
                youtube_id=youtube_id,
                thumbnail_url=get_youtube_thumbnail(youtube_id),
                uploaded_by=current_user.id,
                is_featured=bool(request.form.get('is_featured'))
            )
            db.session.add(video)
            db.session.commit()
            flash('Video added successfully!', 'success')
            return redirect(url_for('admin_videos'))
        except Exception as e:
            app.logger.error(f"Error adding video: {e}")
            flash('An error occurred while adding the video. Please try again.', 'error')
    
    return render_template('admin/video_form.html')

@app.route('/admin/events')
@login_required
def admin_events():
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    try:
        events = Event.query.order_by(Event.event_date.desc()).all()
        now = datetime.utcnow()

        # Categorize events
        upcoming_events = [e for e in events if e.event_date >= now]
        past_events = [e for e in events if e.event_date < now]
        this_month_events = [
            e for e in events if e.event_date.month == now.month and e.event_date.year == now.year
        ]

        return render_template(
            'admin/events.html',
            events=events,
            upcoming_events=upcoming_events,
            past_events=past_events,
            this_month_events=this_month_events
        )
    except Exception as e:
        app.logger.error(f"Error loading admin events: {e}")
        flash('An error occurred loading events.', 'error')
        return redirect(url_for('admin_dashboard'))


@app.route('/admin/events/new', methods=['GET', 'POST'])
@login_required
def admin_new_event():
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        try:
            # Combine date and time
            event_date_str = request.form['event_date']
            event_time_str = request.form['event_time']
            event_datetime_str = f"{event_date_str} {event_time_str}"
            event_date = datetime.strptime(event_datetime_str, '%Y-%m-%d %H:%M')
            
            event = Event(
                title=request.form['title'],
                description=request.form.get('description'),
                event_date=event_date,
                location=request.form.get('location'),
                created_by=current_user.id,
                is_recurring=bool(request.form.get('is_recurring')),
                category=request.form.get('category', 'general')
            )
            db.session.add(event)
            db.session.commit()
            flash('Event created successfully!', 'success')
            return redirect(url_for('admin_events'))
        except ValueError:
            flash('Invalid date or time format. Please check your input.', 'error')
        except Exception as e:
            app.logger.error(f"Error creating event: {e}")
            flash('An error occurred while creating the event. Please try again.', 'error')
    
    return render_template('admin/event_form.html')


@app.route('/admin/events/<int:event_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_edit_event(event_id):
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    event = db.session.get(Event, event_id)
    if not event:
        flash('Event not found.', 'error')
        return redirect(url_for('admin_events'))
    
    if request.method == 'POST':
        try:
            # Combine date and time
            event_date_str = request.form['event_date']
            event_time_str = request.form['event_time']
            event_datetime_str = f"{event_date_str} {event_time_str}"
            event_date = datetime.strptime(event_datetime_str, '%Y-%m-%d %H:%M')
            
            event.title = request.form['title']
            event.description = request.form.get('description')
            event.event_date = event_date
            event.location = request.form.get('location')
            event.is_recurring = bool(request.form.get('is_recurring'))
            event.category = request.form.get('category', 'general')
            
            db.session.commit()
            flash('Event updated successfully!', 'success')
            return redirect(url_for('admin_events'))
        except ValueError:
            flash('Invalid date or time format. Please check your input.', 'error')
        except Exception as e:
            app.logger.error(f"Error updating event: {e}")
            flash('An error occurred while updating the event. Please try again.', 'error')
    
    return render_template('admin/event_form.html', event=event)


@app.route('/admin/events/<int:event_id>/delete', methods=['POST'])
@login_required
def admin_delete_event(event_id):
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    try:
        event = db.session.get(Event, event_id)
        if not event:
            flash('Event not found.', 'error')
            return redirect(url_for('admin_events'))
        
        db.session.delete(event)
        db.session.commit()
        flash('Event deleted successfully!', 'success')
    except Exception as e:
        app.logger.error(f"Error deleting event: {e}")
        flash('An error occurred while deleting the event.', 'error')
    
    return redirect(url_for('admin_events'))

@app.route('/admin/testimonies')
@login_required
def admin_testimonies():
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    try:
        testimonies = Testimony.query.order_by(Testimony.created_at.desc()).all()
        return render_template('admin/testimonies.html', testimonies=testimonies)
    except Exception as e:
        app.logger.error(f"Error loading admin testimonies: {e}")
        flash('An error occurred loading testimonies.', 'error')
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/testimony/<int:testimony_id>/approve')
@login_required
def admin_approve_testimony(testimony_id):
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    try:
        testimony = Testimony.query.get_or_404(testimony_id)
        testimony.is_approved = True
        db.session.commit()
        flash('Testimony approved successfully!', 'success')
    except Exception as e:
        app.logger.error(f"Error approving testimony: {e}")
        flash('An error occurred while approving the testimony.', 'error')
    
    return redirect(url_for('admin_testimonies'))

@app.route('/admin/testimony/<int:testimony_id>/delete', methods=['POST'])
@login_required
def admin_delete_testimony(testimony_id):
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    try:
        testimony = Testimony.query.get_or_404(testimony_id)
        db.session.delete(testimony)
        db.session.commit()
        flash('Testimony deleted successfully!', 'success')
    except Exception as e:
        app.logger.error(f"Error deleting testimony: {e}")
        flash('An error occurred while deleting the testimony.', 'error')
    
    return redirect(url_for('admin_testimonies'))

@app.route('/admin/messages')
@login_required
def admin_messages():
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    try:
        messages = Contact.query.order_by(Contact.created_at.desc()).all()
        return render_template('admin/messages.html', messages=messages)
    except Exception as e:
        app.logger.error(f"Error loading admin messages: {e}")
        flash('An error occurred loading messages.', 'error')
        return redirect(url_for('admin_dashboard'))

@app.route('/admin/message/<int:message_id>/mark-read')
@login_required
def admin_mark_message_read(message_id):
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    try:
        message = db.session.get(Contact, message_id)
        if not message:
            flash('Message not found.', 'error')
            return redirect(url_for('admin_messages'))
        
        message.is_read = True
        db.session.commit()
        flash('Message marked as read!', 'success')
    except Exception as e:
        app.logger.error(f"Error marking message as read: {e}")
        flash('An error occurred.', 'error')
    
    return redirect(url_for('admin_messages'))
# List all prayers
@app.route("/admin/prayers", endpoint="admin_prayers")
@login_required
def admin_prayers():
    prayers = Prayer.query.order_by(Prayer.created_at.desc()).all()
    return render_template("admin/prayers.html", prayers=prayers)

# Add a new prayer
@app.route("/admin/prayers/new", methods=["GET", "POST"], endpoint="admin_add_prayer")
@login_required
def admin_add_prayer():
    if request.method == "POST":
        title = request.form["title"]
        content = request.form["content"]
        category = request.form.get("category")
        is_featured = "is_featured" in request.form

        new_prayer = Prayer(
            title=title,
            content=content,
            category=category,
            is_featured=is_featured
        )
        db.session.add(new_prayer)
        db.session.commit()
        flash("Prayer added successfully", "success")
        return redirect(url_for("admin_prayers"))

    return render_template("admin/prayer_form.html")

# Edit an existing prayer
@app.route("/admin/prayers/<int:prayer_id>/edit", methods=["GET", "POST"], endpoint="admin_edit_prayer")
@login_required
def admin_edit_prayer(prayer_id):
    prayer = Prayer.query.get_or_404(prayer_id)

    if request.method == "POST":
        prayer.title = request.form["title"]
        prayer.content = request.form["content"]
        prayer.category = request.form.get("category")
        prayer.is_featured = "is_featured" in request.form
        db.session.commit()
        flash("Prayer updated successfully", "success")
        return redirect(url_for("admin_prayers"))

    return render_template("admin/prayer_form.html", prayer=prayer)

# Delete a prayer
@app.route("/admin/prayers/<int:prayer_id>/delete", methods=["POST"], endpoint="admin_delete_prayer")
@login_required
def admin_delete_prayer(prayer_id):
    prayer = Prayer.query.get_or_404(prayer_id)
    db.session.delete(prayer)
    db.session.commit()
    flash("Prayer deleted successfully", "success")
    return redirect(url_for("admin_prayers"))

# Initialize database
def init_db():
    """Initialize database with tables and default admin user"""
    with app.app_context():
        try:
            db.create_all()
            
            # Create admin user if doesn't exist
            admin = User.query.filter_by(username='admin').first()
            if not admin:
                admin = User(
                    username='admin',
                    email='admin@tjam.org',
                    password_hash=generate_password_hash('admin123'),
                    is_admin=True
                )
                db.session.add(admin)
                db.session.commit()
                print("Admin user created: username='admin', password='admin123'")
                
            print("Database initialized successfully!")
            
        except Exception as e:
            print(f"Error initializing database: {e}")
@app.errorhandler(404)
def page_not_found(e):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    db.session.rollback()
    return render_template('errors/500.html'), 500

# ADMIN ROUTES - Live Stream Management
@app.route("/admin/livestream", endpoint="admin_livestreams")
@login_required
def admin_livestreams():
    streams = LiveStream.query.order_by(LiveStream.created_at.desc()).all()
    return render_template("admin/livestreams.html", streams=streams)

@app.route("/admin/livestream/new", methods=["GET", "POST"], endpoint="admin_add_livestream")
@login_required
def admin_add_livestream():
    if request.method == "POST":
        # Turn off any existing live streams if this one is set to live
        if request.form.get("is_live"):
            LiveStream.query.filter_by(is_live=True).update({"is_live": False})
        
        new_stream = LiveStream(
            title=request.form["title"],
            description=request.form.get("description"),
            stream_url=request.form.get("stream_url"),
            stream_type=request.form.get("stream_type", "youtube"),
            is_live="is_live" in request.form,
            started_at=datetime.utcnow() if "is_live" in request.form else None
        )
        db.session.add(new_stream)
        db.session.commit()
        flash("Live stream added successfully", "success")
        return redirect(url_for("admin_livestreams"))
    
    return render_template("admin/livestream_form.html")

@app.route("/admin/livestream/<int:stream_id>/edit", methods=["GET", "POST"], endpoint="admin_edit_livestream")
@login_required
def admin_edit_livestream(stream_id):
    stream = LiveStream.query.get_or_404(stream_id)
    
    if request.method == "POST":
        # Turn off any existing live streams if this one is set to live
        if request.form.get("is_live") and not stream.is_live:
            LiveStream.query.filter_by(is_live=True).update({"is_live": False})
        
        stream.title = request.form["title"]
        stream.description = request.form.get("description")
        stream.stream_url = request.form.get("stream_url")
        stream.stream_type = request.form.get("stream_type", "youtube")
        
        was_live = stream.is_live
        stream.is_live = "is_live" in request.form
        
        # Set started_at if going live, or clear it if going offline
        if stream.is_live and not was_live:
            stream.started_at = datetime.utcnow()
        elif not stream.is_live and was_live:
            stream.started_at = None
            
        stream.updated_at = datetime.utcnow()
        db.session.commit()
        flash("Live stream updated successfully", "success")
        return redirect(url_for("admin_livestreams"))
    
    return render_template("admin/livestream_form.html", stream=stream)

@app.route("/admin/livestream/<int:stream_id>/toggle", methods=["POST"], endpoint="admin_toggle_livestream")
@login_required
def admin_toggle_livestream(stream_id):
    stream = LiveStream.query.get_or_404(stream_id)
    
    if not stream.is_live:
        # Turn off any other live streams
        LiveStream.query.filter_by(is_live=True).update({"is_live": False})
        stream.is_live = True
        stream.started_at = datetime.utcnow()
        flash(f"'{stream.title}' is now live!", "success")
    else:
        stream.is_live = False
        stream.started_at = None
        flash(f"'{stream.title}' is now offline", "info")
    
    db.session.commit()
    return redirect(url_for("admin_livestreams"))

@app.route("/admin/livestream/<int:stream_id>/delete", methods=["POST"], endpoint="admin_delete_livestream")
@login_required
def admin_delete_livestream(stream_id):
    stream = LiveStream.query.get_or_404(stream_id)
    db.session.delete(stream)
    db.session.commit()
    flash("Live stream deleted successfully", "success")
    return redirect(url_for("admin_livestreams"))

# ADMIN ROUTES - Adoration Schedule Management
@app.route("/admin/schedule", endpoint="admin_schedules")
@login_required
def admin_schedules():
    schedules = AdorationSchedule.query.order_by(AdorationSchedule.start_time).all()
    return render_template("admin/schedules.html", schedules=schedules)

@app.route("/admin/schedule/new", methods=["GET", "POST"], endpoint="admin_add_schedule")
@login_required
def admin_add_schedule():
    if request.method == "POST":
        from datetime import time
        
        start_time = time.fromisoformat(request.form["start_time"])
        end_time = time.fromisoformat(request.form["end_time"])
        day_of_week = request.form.get("day_of_week")
        day_of_week = int(day_of_week) if day_of_week else None
        
        new_schedule = AdorationSchedule(
            title=request.form["title"],
            description=request.form.get("description"),
            start_time=start_time,
            end_time=end_time,
            day_of_week=day_of_week,
            is_active="is_active" in request.form
        )
        db.session.add(new_schedule)
        db.session.commit()
        flash("Schedule added successfully", "success")
        return redirect(url_for("admin_schedules"))
    
    return render_template("admin/schedule_form.html")

@app.route("/admin/schedule/<int:schedule_id>/edit", methods=["GET", "POST"], endpoint="admin_edit_schedule")
@login_required
def admin_edit_schedule(schedule_id):
    schedule = AdorationSchedule.query.get_or_404(schedule_id)
    
    if request.method == "POST":
        from datetime import time
        
        schedule.title = request.form["title"]
        schedule.description = request.form.get("description")
        schedule.start_time = time.fromisoformat(request.form["start_time"])
        schedule.end_time = time.fromisoformat(request.form["end_time"])
        
        day_of_week = request.form.get("day_of_week")
        schedule.day_of_week = int(day_of_week) if day_of_week else None
        schedule.is_active = "is_active" in request.form
        
        db.session.commit()
        flash("Schedule updated successfully", "success")
        return redirect(url_for("admin_schedules"))
    
    return render_template("admin/schedule_form.html", schedule=schedule)

@app.route("/admin/schedule/<int:schedule_id>/delete", methods=["POST"], endpoint="admin_delete_schedule")
@login_required
def admin_delete_schedule(schedule_id):
    schedule = AdorationSchedule.query.get_or_404(schedule_id)
    db.session.delete(schedule)
    db.session.commit()
    flash("Schedule deleted successfully", "success")
    return redirect(url_for("admin_schedules"))

# API endpoint to update viewer count (can be called via JavaScript)
@app.route("/api/livestream/<int:stream_id>/viewers", methods=["POST"])
def update_viewer_count(stream_id):
    stream = LiveStream.query.get_or_404(stream_id)
    data = request.get_json()
    stream.viewer_count = data.get("count", 0)
    db.session.commit()
    return {"success": True}

if __name__ == '__main__':
    init_db()
    app.run(debug=True)