"""
Triumphant Jesus Adoration Ministry (TJAM) Website
Flask Application - Complete Version with Enhanced Telegram Integration
"""

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, time
import re
import os
import requests
from werkzeug.utils import secure_filename
import json
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import atexit
import random

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here-change-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tjam.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# Telegram Configuration - SET THESE VALUES
TELEGRAM_BOT_TOKEN = "7993041952:AAHXAn-s7vfMV8xCzwOJEB8Bp8XzLmW8uF4"  # Get this from @BotFather
TELEGRAM_WEBHOOK_URL = "https://tjam.onrender.com/telegram-webhook"  # Your webhook URL

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

# Template filters for better display
@app.template_filter('from_json')
def from_json_filter(json_string):
    """Convert JSON string to Python object"""
    try:
        return json.loads(json_string) if json_string else []
    except (json.JSONDecodeError, TypeError):
        return []

@app.template_filter('ordinal')
def ordinal_filter(number):
    """Add ordinal suffix to number (1st, 2nd, 3rd, etc.)"""
    if 10 <= number % 100 <= 20:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(number % 10, 'th')
    return suffix

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

class TelegramSubscriber(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    telegram_chat_id = db.Column(db.String(50), nullable=False, unique=True)
    telegram_username = db.Column(db.String(50))
    is_active = db.Column(db.Boolean, default=True)
    prayer_dates = db.Column(db.Text)  # JSON array of dates [2, 15, 31] etc
    subscription_step = db.Column(db.String(20), default='completed')  # 'awaiting_dates', 'completed'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_notification_sent = db.Column(db.DateTime)

class PersonalizedPrayerMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    creator = db.relationship('User', backref=db.backref('personalized_messages', lazy=True))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class NotificationLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subscriber_id = db.Column(db.Integer, db.ForeignKey('telegram_subscriber.id'), nullable=False)
    subscriber = db.relationship('TelegramSubscriber', backref=db.backref('notifications', lazy=True))
    message_id = db.Column(db.Integer, db.ForeignKey('personalized_prayer_message.id'), nullable=True)
    message = db.relationship('PersonalizedPrayerMessage', backref=db.backref('logs', lazy=True))
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='sent')
    response_data = db.Column(db.Text)
    prayer_date = db.Column(db.Integer)  # Which date this was sent for (1-31)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Telegram Helper Functions
def send_telegram_message(chat_id, message):
    """Send a message to a Telegram chat"""
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        app.logger.warning("Telegram bot token not configured")
        return {'ok': False, 'error': 'Bot token not configured'}
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    data = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'HTML',
        'disable_web_page_preview': True
    }
    
    try:
        response = requests.post(url, data=data, timeout=10)
        return response.json()
    except Exception as e:
        app.logger.error(f"Error sending Telegram message: {e}")
        return {'ok': False, 'error': str(e)}

def setup_telegram_webhook():
    """Set up the Telegram webhook"""
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        return {'ok': False, 'error': 'Bot token not configured'}
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook"
    data = {'url': TELEGRAM_WEBHOOK_URL}
    
    try:
        response = requests.post(url, data=data)
        return response.json()
    except Exception as e:
        app.logger.error(f"Error setting up webhook: {e}")
        return {'ok': False, 'error': str(e)}

def send_personalized_prayer_notifications():
    """Send personalized notifications to users on their chosen dates"""
    try:
        today = datetime.now()
        current_day = today.day
        
        # Get all active subscribers who have this day in their prayer dates
        subscribers = TelegramSubscriber.query.filter_by(is_active=True).all()
        sent_count = 0
        
        for subscriber in subscribers:
            if not subscriber.prayer_dates:
                continue
                
            try:
                prayer_dates = json.loads(subscriber.prayer_dates)
                
                # Check if today is one of their prayer dates
                if current_day in prayer_dates:
                    # Check if we already sent notification today
                    today_log = NotificationLog.query.filter(
                        NotificationLog.subscriber_id == subscriber.id,
                        NotificationLog.prayer_date == current_day,
                        db.func.date(NotificationLog.sent_at) == today.date()
                    ).first()
                    
                    if today_log:
                        continue  # Already sent today
                    
                    # Get a random active prayer message
                    prayer_messages = PersonalizedPrayerMessage.query.filter_by(is_active=True).all()
                    if not prayer_messages:
                        continue
                    
                    selected_message = random.choice(prayer_messages)
                    
                    # Format personalized message
                    formatted_message = f"""<b>🙏 {selected_message.title}</b>

Hello {subscriber.name},

Today is your watch tower prayer day! 

{selected_message.message}

<i>Remember, God hears every prayer. Trust in His perfect timing.

Blessings,
TJAM Ministry</i>"""
                    
                    # Send message
                    result = send_telegram_message(subscriber.telegram_chat_id, formatted_message)
                    
                    # Log the notification
                    log_entry = NotificationLog(
                        subscriber_id=subscriber.id,
                        message_id=selected_message.id,
                        status='sent' if result.get('ok') else 'failed',
                        response_data=json.dumps(result),
                        prayer_date=current_day
                    )
                    db.session.add(log_entry)
                    
                    # Update subscriber's last notification time
                    subscriber.last_notification_sent = datetime.utcnow()
                    sent_count += 1
                    
                    app.logger.info(f"Sent personalized prayer to {subscriber.name} for date {current_day}")
                    
            except (json.JSONDecodeError, TypeError) as e:
                app.logger.error(f"Error parsing prayer dates for subscriber {subscriber.id}: {e}")
                continue
        
        db.session.commit()
        app.logger.info(f"Sent {sent_count} prayer notifications for day {current_day}")
        
    except Exception as e:
        app.logger.error(f"Error in send_personalized_prayer_notifications: {e}")

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

def save_uploaded_file(file):
    """Save uploaded file and return filename"""
    if file and file.filename:
        filename = secure_filename(file.filename)
        # Add timestamp to avoid filename conflicts
        name, ext = os.path.splitext(filename)
        filename = f"{name}_{int(datetime.utcnow().timestamp())}{ext}"
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return filename
    return None

# Telegram Webhook Route
@app.route('/telegram-webhook', methods=['POST'])
def telegram_webhook():
    """Enhanced webhook to handle subscription with prayer date collection"""
    try:
        update = request.get_json()
        
        if 'message' in update:
            message = update['message']
            chat_id = message['chat']['id']
            text = message.get('text', '').strip()
            username = message['from'].get('username', '')
            first_name = message['from'].get('first_name', 'Friend')
            
            # Get or create subscriber
            subscriber = TelegramSubscriber.query.filter_by(telegram_chat_id=str(chat_id)).first()
            
            # Handle different commands and conversation states
            if text.lower() in ['/start', '/subscribe']:
                if subscriber:
                    subscriber.is_active = True
                    subscriber.subscription_step = 'awaiting_dates'
                    db.session.commit()
                    welcome_msg = f"<b>Welcome back {first_name}!</b> Let's update your prayer preferences."
                else:
                    subscriber = TelegramSubscriber(
                        name=first_name,
                        telegram_chat_id=str(chat_id),
                        telegram_username=username,
                        subscription_step='awaiting_dates'
                    )
                    db.session.add(subscriber)
                    db.session.commit()
                    welcome_msg = f"<b>🙏 Welcome to TJAM Prayer Notifications!</b>\n\nHello {first_name}!"
                
                # Ask for prayer dates
                dates_msg = f"""{welcome_msg}

<b>Personalize Your Prayer Experience</b>

Please choose your monthly prayer dates (1-31). You can select multiple dates by sending them separated by commas.

<b>Examples:</b>
• <code>7</code> (7th of every month)
• <code>1,15</code> (1st and 15th of every month)
• <code>5,12,25</code> (5th, 12th, and 25th)

<b>📅 What dates would you like to receive prayer notifications?</b>"""
                
                send_telegram_message(chat_id, dates_msg)
            
            elif subscriber and subscriber.subscription_step == 'awaiting_dates':
                # Process prayer dates input
                try:
                    # Parse dates from user input
                    dates_input = text.replace(' ', '').split(',')
                    prayer_dates = []
                    
                    for date_str in dates_input:
                        date_num = int(date_str)
                        if 1 <= date_num <= 31:
                            prayer_dates.append(date_num)
                    
                    if not prayer_dates:
                        error_msg = """<b>❌ Invalid dates</b>

Please enter valid dates between 1 and 31, separated by commas.

<b>Examples:</b>
• <code>7</code>
• <code>1,15</code>
• <code>5,12,25</code>

Try again:"""
                        send_telegram_message(chat_id, error_msg)
                        return "OK", 200
                    
                    # Save prayer dates
                    subscriber.prayer_dates = json.dumps(sorted(prayer_dates))
                    subscriber.subscription_step = 'completed'
                    subscriber.is_active = True
                    db.session.commit()
                    
                    # Format dates for display
                    date_suffixes = {1: 'st', 2: 'nd', 3: 'rd', 21: 'st', 22: 'nd', 23: 'rd', 31: 'st'}
                    formatted_dates = []
                    for date in sorted(prayer_dates):
                        suffix = date_suffixes.get(date, 'th')
                        formatted_dates.append(f"{date}{suffix}")
                    
                    dates_text = ", ".join(formatted_dates)
                    
                    success_msg = f"""<b>✅ Subscription Complete!</b>

You're now subscribed to receive prayer notifications on:
<b>{dates_text}</b> of every month.

<b>What you'll receive:</b>
• Personalized prayer messages
• Spiritual encouragement 
• Monthly reminders for prayer

<b>Commands:</b>
• <code>/dates</code> - View your current prayer dates
• <code>/change</code> - Change your prayer dates
• <code>/unsubscribe</code> - Stop notifications
• <code>/help</code> - Show all commands

<i>God bless you on your prayer journey! 🙏</i>"""
                    
                    send_telegram_message(chat_id, success_msg)
                    
                except (ValueError, TypeError):
                    error_msg = """<b>❌ Invalid format</b>

Please enter numbers only, separated by commas.

<b>Valid examples:</b>
• <code>7</code>
• <code>1,15</code> 
• <code>5,12,25</code>

Try again:"""
                    send_telegram_message(chat_id, error_msg)
            
            elif text.lower() == '/dates':
                if subscriber and subscriber.prayer_dates:
                    dates = json.loads(subscriber.prayer_dates)
                    date_suffixes = {1: 'st', 2: 'nd', 3: 'rd', 21: 'st', 22: 'nd', 23: 'rd', 31: 'st'}
                    formatted_dates = []
                    for date in sorted(dates):
                        suffix = date_suffixes.get(date, 'th')
                        formatted_dates.append(f"{date}{suffix}")
                    
                    dates_text = ", ".join(formatted_dates)
                    dates_msg = f"""<b>📅 Your Prayer Dates</b>

You receive notifications on:
<b>{dates_text}</b> of every month

Send <code>/change</code> to update your dates."""
                else:
                    dates_msg = "You haven't set any prayer dates yet. Send <code>/start</code> to subscribe."
                
                send_telegram_message(chat_id, dates_msg)
            
            elif text.lower() == '/change':
                if subscriber:
                    subscriber.subscription_step = 'awaiting_dates'
                    db.session.commit()
                    
                    change_msg = """<b>📅 Change Your Prayer Dates</b>

Enter your new monthly prayer dates (1-31), separated by commas.

<b>Examples:</b>
• <code>7</code> (7th of every month)
• <code>1,15</code> (1st and 15th)
• <code>5,12,25</code> (5th, 12th, and 25th)

<b>What are your new prayer dates?</b>"""
                    
                    send_telegram_message(chat_id, change_msg)
                else:
                    send_telegram_message(chat_id, "You're not subscribed yet. Send <code>/start</code> to begin.")
            
            elif text.lower() in ['/unsubscribe', '/stop']:
                if subscriber:
                    subscriber.is_active = False
                    db.session.commit()
                    goodbye_msg = f"""<b>You've been unsubscribed</b> from TJAM prayer notifications.

We're sorry to see you go, {subscriber.name}.

Your prayer dates have been saved. Send <code>/start</code> to resubscribe anytime.

<i>May God bless you always! 🙏</i>"""
                    send_telegram_message(chat_id, goodbye_msg)
                else:
                    send_telegram_message(chat_id, "You weren't subscribed to notifications.")
            
            elif text.lower() == '/help':
                help_msg = """<b>🙏 TJAM Prayer Bot Commands</b>

<b>Subscription:</b>
• <code>/start</code> - Subscribe/resubscribe to notifications
• <code>/unsubscribe</code> - Stop receiving notifications

<b>Prayer Dates:</b>
• <code>/dates</code> - View your current prayer dates  
• <code>/change</code> - Change your prayer dates

<b>Support:</b>
• <code>/help</code> - Show this help message

<i>Need more help? Contact our ministry through our website.</i>"""
                send_telegram_message(chat_id, help_msg)
            
            else:
                # Handle unrecognized messages
                if subscriber and subscriber.subscription_step == 'awaiting_dates':
                    # They're in the middle of setting dates but sent something else
                    reminder_msg = """<b>📅 Please enter your prayer dates</b>

Send numbers between 1-31, separated by commas.

<b>Examples:</b> <code>7</code> or <code>1,15</code> or <code>5,12,25</code>"""
                    send_telegram_message(chat_id, reminder_msg)
                else:
                    # General unrecognized command
                    help_msg = """<b>Command not recognized</b>

Send <code>/help</code> to see available commands, or <code>/start</code> to subscribe to prayer notifications."""
                    send_telegram_message(chat_id, help_msg)
        
        return "OK", 200
        
    except Exception as e:
        app.logger.error(f"Telegram webhook error: {e}")
        return "Error", 500

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
            'unread_messages': Contact.query.filter_by(is_read=False).count(),
            'telegram_subscribers': TelegramSubscriber.query.filter_by(is_active=True).count(),
            'prayer_messages': PersonalizedPrayerMessage.query.filter_by(is_active=True).count()
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

# Blog Post Management
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
            
            # Handle file upload
            featured_image = None
            if 'featured_image' in request.files:
                file = request.files['featured_image']
                if file.filename:
                    featured_image = save_uploaded_file(file)
                    if not featured_image:
                        flash('Invalid image file. Post created without image.', 'warning')
            
            post = BlogPost(
                title=request.form['title'],
                content=request.form['content'],
                excerpt=request.form.get('excerpt'),
                author_id=current_user.id,
                featured_image=featured_image,
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
        # Delete associated image file if exists
        if post.featured_image:
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], post.featured_image)
            if os.path.exists(image_path):
                os.remove(image_path)
        
        db.session.delete(post)
        db.session.commit()
        flash('Post deleted successfully!', 'success')
    except Exception as e:
        app.logger.error(f"Error deleting post: {e}")
        flash('An error occurred while deleting the post.', 'error')
    
    return redirect(url_for('admin_posts'))

# Video Management
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

@app.route('/admin/videos/<int:video_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_edit_video(video_id):
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    video = AdorationVideo.query.get_or_404(video_id)
    
    if request.method == 'POST':
        try:
            youtube_url = request.form['youtube_url']
            youtube_id = extract_youtube_id(youtube_url)
            
            if not youtube_id:
                flash('Invalid YouTube URL. Please provide a valid YouTube video URL.', 'error')
                return render_template('admin/video_form.html', video=video)
            
            video.title = request.form['title']
            video.description = request.form.get('description')
            video.youtube_url = youtube_url
            video.youtube_id = youtube_id
            video.thumbnail_url = get_youtube_thumbnail(youtube_id)
            video.is_featured = bool(request.form.get('is_featured'))
            
            db.session.commit()
            flash('Video updated successfully!', 'success')
            return redirect(url_for('admin_videos'))
        except Exception as e:
            app.logger.error(f"Error updating video: {e}")
            flash('An error occurred while updating the video. Please try again.', 'error')
    
    return render_template('admin/video_form.html', video=video)

@app.route('/admin/videos/<int:video_id>/delete', methods=['POST'])
@login_required
def admin_delete_video(video_id):
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    try:
        video = AdorationVideo.query.get_or_404(video_id)
        db.session.delete(video)
        db.session.commit()
        flash('Video deleted successfully!', 'success')
    except Exception as e:
        app.logger.error(f"Error deleting video: {e}")
        flash('An error occurred while deleting the video.', 'error')
    
    return redirect(url_for('admin_videos'))

# Event Management
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

# Prayer Management
@app.route("/admin/prayers", endpoint="admin_prayers")
@login_required
def admin_prayers():
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    prayers = Prayer.query.order_by(Prayer.created_at.desc()).all()
    return render_template("admin/prayers.html", prayers=prayers)

@app.route("/admin/prayers/new", methods=["GET", "POST"], endpoint="admin_add_prayer")
@login_required
def admin_add_prayer():
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    if request.method == "POST":
        try:
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
        except Exception as e:
            app.logger.error(f"Error adding prayer: {e}")
            flash('An error occurred while adding the prayer. Please try again.', 'error')
    
    return render_template("admin/prayer_form.html")

@app.route("/admin/prayers/<int:prayer_id>/edit", methods=["GET", "POST"], endpoint="admin_edit_prayer")
@login_required
def admin_edit_prayer(prayer_id):
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    prayer = Prayer.query.get_or_404(prayer_id)
    
    if request.method == "POST":
        try:
            prayer.title = request.form["title"]
            prayer.content = request.form["content"]
            prayer.category = request.form.get("category")
            prayer.is_featured = "is_featured" in request.form
            db.session.commit()
            flash("Prayer updated successfully", "success")
            return redirect(url_for("admin_prayers"))
        except Exception as e:
            app.logger.error(f"Error updating prayer: {e}")
            flash('An error occurred while updating the prayer. Please try again.', 'error')
    
    return render_template("admin/prayer_form.html", prayer=prayer)

@app.route("/admin/prayers/<int:prayer_id>/delete", methods=["POST"], endpoint="admin_delete_prayer")
@login_required
def admin_delete_prayer(prayer_id):
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    try:
        prayer = Prayer.query.get_or_404(prayer_id)
        db.session.delete(prayer)
        db.session.commit()
        flash("Prayer deleted successfully", "success")
    except Exception as e:
        app.logger.error(f"Error deleting prayer: {e}")
        flash('An error occurred while deleting the prayer.', 'error')
    
    return redirect(url_for("admin_prayers"))

# Testimony Management
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

# Message Management
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

# Live Stream Management
@app.route("/admin/livestream", endpoint="admin_livestreams")
@login_required
def admin_livestreams():
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    streams = LiveStream.query.order_by(LiveStream.created_at.desc()).all()
    return render_template("admin/livestreams.html", streams=streams)

@app.route("/admin/livestream/new", methods=["GET", "POST"], endpoint="admin_add_livestream")
@login_required
def admin_add_livestream():
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    if request.method == "POST":
        try:
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
        except Exception as e:
            app.logger.error(f"Error adding livestream: {e}")
            flash('An error occurred while adding the livestream.', 'error')
    
    return render_template("admin/livestream_form.html")

@app.route("/admin/livestream/<int:stream_id>/edit", methods=["GET", "POST"], endpoint="admin_edit_livestream")
@login_required
def admin_edit_livestream(stream_id):
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    stream = LiveStream.query.get_or_404(stream_id)
    
    if request.method == "POST":
        try:
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
        except Exception as e:
            app.logger.error(f"Error updating livestream: {e}")
            flash('An error occurred while updating the livestream.', 'error')
    
    return render_template("admin/livestream_form.html", stream=stream)

@app.route("/admin/livestream/<int:stream_id>/toggle", methods=["POST"], endpoint="admin_toggle_livestream")
@login_required
def admin_toggle_livestream(stream_id):
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    try:
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
    except Exception as e:
        app.logger.error(f"Error toggling livestream: {e}")
        flash('An error occurred while updating the stream status.', 'error')
    
    return redirect(url_for("admin_livestreams"))

@app.route("/admin/livestream/<int:stream_id>/delete", methods=["POST"], endpoint="admin_delete_livestream")
@login_required
def admin_delete_livestream(stream_id):
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    try:
        stream = LiveStream.query.get_or_404(stream_id)
        db.session.delete(stream)
        db.session.commit()
        flash("Live stream deleted successfully", "success")
    except Exception as e:
        app.logger.error(f"Error deleting livestream: {e}")
        flash('An error occurred while deleting the livestream.', 'error')
    
    return redirect(url_for("admin_livestreams"))

# Adoration Schedule Management
@app.route("/admin/schedule", endpoint="admin_schedules")
@login_required
def admin_schedules():
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    schedules = AdorationSchedule.query.order_by(AdorationSchedule.start_time).all()
    return render_template("admin/schedules.html", schedules=schedules)

@app.route("/admin/schedule/new", methods=["GET", "POST"], endpoint="admin_add_schedule")
@login_required
def admin_add_schedule():
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    if request.method == "POST":
        try:
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
        except Exception as e:
            app.logger.error(f"Error adding schedule: {e}")
            flash('An error occurred while adding the schedule.', 'error')
    
    return render_template("admin/schedule_form.html")

@app.route("/admin/schedule/<int:schedule_id>/edit", methods=["GET", "POST"], endpoint="admin_edit_schedule")
@login_required
def admin_edit_schedule(schedule_id):
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    schedule = AdorationSchedule.query.get_or_404(schedule_id)
    
    if request.method == "POST":
        try:
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
        except Exception as e:
            app.logger.error(f"Error updating schedule: {e}")
            flash('An error occurred while updating the schedule.', 'error')
    
    return render_template("admin/schedule_form.html", schedule=schedule)

@app.route("/admin/schedule/<int:schedule_id>/delete", methods=["POST"], endpoint="admin_delete_schedule")
@login_required
def admin_delete_schedule(schedule_id):
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    try:
        schedule = AdorationSchedule.query.get_or_404(schedule_id)
        db.session.delete(schedule)
        db.session.commit()
        flash("Schedule deleted successfully", "success")
    except Exception as e:
        app.logger.error(f"Error deleting schedule: {e}")
        flash('An error occurred while deleting the schedule.', 'error')
    
    return redirect(url_for("admin_schedules"))

# TELEGRAM ADMINISTRATION ROUTES
@app.route("/admin/telegram", endpoint="admin_telegram")
@login_required
def admin_telegram():
    """Main Telegram management dashboard"""
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    try:
        # Get statistics
        total_subscribers = TelegramSubscriber.query.count()
        active_subscribers = TelegramSubscriber.query.filter_by(is_active=True).count()
        
        # Count today's notifications
        today = datetime.now().date()
        today_notifications = NotificationLog.query.filter(
            db.func.date(NotificationLog.sent_at) == today
        ).count()
        
        # Count prayer messages
        prayer_messages_count = PersonalizedPrayerMessage.query.filter_by(is_active=True).count()
        
        # Get all subscribers
        subscribers = TelegramSubscriber.query.order_by(TelegramSubscriber.created_at.desc()).all()
        
        # Get recent notifications
        recent_notifications = NotificationLog.query.join(TelegramSubscriber).order_by(
            NotificationLog.sent_at.desc()
        ).limit(10).all()
        
        return render_template('admin/telegram.html',
                             total_subscribers=total_subscribers,
                             active_subscribers=active_subscribers,
                             today_notifications=today_notifications,
                             prayer_messages_count=prayer_messages_count,
                             subscribers=subscribers,
                             recent_notifications=recent_notifications)
    except Exception as e:
        app.logger.error(f"Error loading Telegram admin: {e}")
        flash('An error occurred loading the Telegram management page.', 'error')
        return redirect(url_for('admin_dashboard'))

@app.route("/admin/telegram/send-test/<int:subscriber_id>", methods=["POST"])
@login_required
def admin_send_test_message(subscriber_id):
    """Send a test message to a specific subscriber"""
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    try:
        subscriber = TelegramSubscriber.query.get_or_404(subscriber_id)
        data = request.get_json()
        message = data.get('message', 'Test message from TJAM Admin')
        
        result = send_telegram_message(subscriber.telegram_chat_id, message)
        
        if result.get('ok'):
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': result.get('description', 'Unknown error')})
            
    except Exception as e:
        app.logger.error(f"Error sending test message: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route("/admin/telegram/toggle-subscriber/<int:subscriber_id>", methods=["POST"])
@login_required
def admin_toggle_subscriber(subscriber_id):
    """Toggle subscriber active status"""
    if not current_user.is_admin:
        return jsonify({'success': False, 'error': 'Unauthorized'}), 403
    
    try:
        subscriber = TelegramSubscriber.query.get_or_404(subscriber_id)
        data = request.get_json()
        subscriber.is_active = data.get('active', not subscriber.is_active)
        
        db.session.commit()
        return jsonify({'success': True})
        
    except Exception as e:
        app.logger.error(f"Error toggling subscriber: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route("/admin/telegram/test-notifications", methods=["POST"])
@login_required
def admin_test_notifications():
    """Manually trigger notification sending for testing"""
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    try:
        send_personalized_prayer_notifications()
        flash('Test notifications sent successfully!', 'success')
    except Exception as e:
        app.logger.error(f"Error sending test notifications: {e}")
        flash('Error sending notifications', 'error')
    
    return redirect(url_for('admin_telegram'))

@app.route("/admin/telegram/setup-webhook", methods=["POST"])
@login_required
def admin_setup_webhook():
    """Set up Telegram webhook"""
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    result = setup_telegram_webhook()
    if result.get('ok'):
        flash('Webhook set up successfully!', 'success')
    else:
        flash(f'Error setting up webhook: {result.get("description", "Unknown error")}', 'error')
    
    return redirect(url_for('admin_telegram'))

# PERSONALIZED PRAYER MESSAGES MANAGEMENT
@app.route("/admin/prayer-messages", endpoint="admin_prayer_messages")
@login_required
def admin_prayer_messages():
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    messages = PersonalizedPrayerMessage.query.order_by(PersonalizedPrayerMessage.created_at.desc()).all()
    active_count = PersonalizedPrayerMessage.query.filter_by(is_active=True).count()
    
    # Get usage statistics (optional - you might want to track this)
    recent_used_messages = messages  # Placeholder - you could add usage tracking
    
    return render_template("admin/prayer_messages.html", 
                         messages=messages, 
                         active_count=active_count,
                         recent_used_messages=recent_used_messages)

@app.route("/admin/prayer-messages/new", methods=["GET", "POST"], endpoint="admin_add_prayer_message")
@login_required
def admin_add_prayer_message():
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    if request.method == "POST":
        try:
            new_message = PersonalizedPrayerMessage(
                title=request.form["title"],
                message=request.form["message"],
                is_active="is_active" in request.form,
                created_by=current_user.id
            )
            db.session.add(new_message)
            db.session.commit()
            flash("Prayer message created successfully", "success")
            return redirect(url_for("admin_prayer_messages"))
            
        except Exception as e:
            app.logger.error(f"Error creating prayer message: {e}")
            flash("Error creating prayer message", "error")
    
    return render_template("admin/prayer_message_form.html")

@app.route("/admin/prayer-messages/<int:message_id>/edit", methods=["GET", "POST"], endpoint="admin_edit_prayer_message")
@login_required
def admin_edit_prayer_message(message_id):
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    message = PersonalizedPrayerMessage.query.get_or_404(message_id)
    
    if request.method == "POST":
        try:
            message.title = request.form["title"]
            message.message = request.form["message"]
            message.is_active = "is_active" in request.form
            
            db.session.commit()
            flash("Prayer message updated successfully", "success")
            return redirect(url_for("admin_prayer_messages"))
            
        except Exception as e:
            app.logger.error(f"Error updating prayer message: {e}")
            flash("Error updating prayer message", "error")
    
    # Get usage count (optional - you might want to track this)
    usage_count = NotificationLog.query.filter_by(message_id=message_id).count()
    
    return render_template("admin/prayer_message_form.html", message=message, usage_count=usage_count)

@app.route("/admin/prayer-messages/<int:message_id>/delete", methods=["POST"], endpoint="admin_delete_prayer_message")
@login_required
def admin_delete_prayer_message(message_id):
    if not current_user.is_admin:
        return redirect(url_for('index'))
    
    try:
        message = PersonalizedPrayerMessage.query.get_or_404(message_id)
        db.session.delete(message)
        db.session.commit()
        flash("Prayer message deleted successfully", "success")
    except Exception as e:
        app.logger.error(f"Error deleting prayer message: {e}")
        flash("Error deleting prayer message", "error")
    
    return redirect(url_for("admin_prayer_messages"))

# API endpoint to update viewer count (can be called via JavaScript)
@app.route("/api/livestream/<int:stream_id>/viewers", methods=["POST"])
def update_viewer_count(stream_id):
    stream = LiveStream.query.get_or_404(stream_id)
    data = request.get_json()
    stream.viewer_count = data.get("count", 0)
    db.session.commit()
    return {"success": True}

# Error Handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    db.session.rollback()
    return render_template('errors/500.html'), 500

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
            
            # Create sample prayer messages if none exist
            if PersonalizedPrayerMessage.query.count() == 0:
                sample_messages = [
                    {
                        'title': 'Morning Blessing',
                        'message': 'May this new day bring you closer to God\'s love and purpose for your life. As you wake up this morning, remember that His mercies are new every day.\n\n"The Lord your God is with you, the Mighty Warrior who saves. He will take great delight in you; in his love he will no longer rebuke you, but will rejoice over you with singing." - Zephaniah 3:17\n\nTake time to thank Him for this beautiful day and ask for His guidance in all you do.'
                    },
                    {
                        'title': 'Strength for Today',
                        'message': 'When life feels overwhelming, remember that God\'s strength is made perfect in our weakness. You don\'t have to face today\'s challenges alone.\n\n"I can do all things through Christ who strengthens me." - Philippians 4:13\n\nTake a moment to pray and surrender your worries to Him. He is faithful and will provide everything you need.'
                    },
                    {
                        'title': 'Peace in His Presence',
                        'message': 'In the midst of life\'s storms, God offers us His perfect peace. Today, let His presence calm your anxious heart and give you rest.\n\n"Peace I leave with you; my peace I give you. I do not give to you as the world gives. Do not let your hearts be troubled and do not be afraid." - John 14:27\n\nSpend time in quiet prayer today, allowing His peace to wash over you.'
                    }
                ]
                
                for msg_data in sample_messages:
                    sample_msg = PersonalizedPrayerMessage(
                        title=msg_data['title'],
                        message=msg_data['message'],
                        is_active=True,
                        created_by=admin.id
                    )
                    db.session.add(sample_msg)
                
                db.session.commit()
                print("Sample prayer messages created")
                
            print("Database initialized successfully!")
            
        except Exception as e:
            print(f"Error initializing database: {e}")

# Initialize and start the scheduler
scheduler = BackgroundScheduler()
scheduler.add_job(
    func=send_personalized_prayer_notifications,
    trigger=CronTrigger(hour=9, minute=0),  # Send at 9 AM daily
    id='personalized_prayer_notifications',
    name='Send Personalized Prayer Notifications',
    replace_existing=True
)

# Start the scheduler when the app starts
def start_scheduler():
    if not scheduler.running:
        scheduler.start()
        print("Scheduler started - will send notifications at 9 AM daily")

# Shut down the scheduler when the app stops
atexit.register(lambda: scheduler.shutdown())

if __name__ == '__main__':
    init_db()
    start_scheduler()
    
    print("\n" + "="*60)
    print("TJAM Flask Application Starting...")
    print("="*60)
    print("Default admin login:")
    print("Username: admin")
    print("Password: admin123")
    print("\nTelegram Configuration:")
    print(f"Bot Token: {'✓ Set' if TELEGRAM_BOT_TOKEN != 'YOUR_BOT_TOKEN_HERE' else '✗ Not configured'}")
    print(f"Webhook URL: {TELEGRAM_WEBHOOK_URL}")
    print("\nIMPORTANT: Update TELEGRAM_BOT_TOKEN and TELEGRAM_WEBHOOK_URL")
    print("before deploying to production")
    print("\nFeatures included:")
    print("- Complete ministry website with blog, videos, events")
    print("- Admin panel for content management")
    print("- Telegram prayer notification system")
    print("- Personalized prayer scheduling (1-31 of each month)")
    print("- Live streaming management")
    print("- Prayer and testimony management")
    print("- Automated daily notifications")
    print("="*60)
    
    app.run(debug=True)