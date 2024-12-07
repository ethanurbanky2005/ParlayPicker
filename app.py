# app.py

from dotenv import load_dotenv
import os
from datetime import datetime

load_dotenv()

from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    login_required,
    logout_user,
    current_user,
)
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from forms import RegistrationForm, LoginForm
from werkzeug.security import generate_password_hash, check_password_hash
from logic.data_fetch import (
    get_games_and_odds,
    get_advanced_metrics,
    get_player_props,
    get_betting_splits,
    get_injured_players,
)
from logic.model import predict_outcomes
from logic.parlay import build_optimal_parlay
from logic.risk_management import calculate_stakes
from logic.odds_analysis import analyze_line_movement
import json
import requests  # Ensure requests is imported for futures route

app = Flask(__name__, instance_relative_config=True)

# ------------------------------
# Configuration
# ------------------------------
app.config.update(
    SECRET_KEY=os.getenv("SECRET_KEY", "default_secret_key"),  # Fallback for development
    SQLALCHEMY_DATABASE_URI="sqlite:///parlay.db",
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
)

# ------------------------------
# Extensions Setup
# ------------------------------
# SQLAlchemy setup
db = SQLAlchemy(app)

# Flask-Migrate setup
migrate = Migrate(app, db)

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"  # Redirect to login page if not authenticated

# ------------------------------
# Database Models
# ------------------------------
class User(UserMixin, db.Model):
    __tablename__ = 'user'  # Explicitly define the table name

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), nullable=False)  # Remove unique=True here
    password_hash = db.Column(db.String(150), nullable=False)
    bets = db.relationship("Bet", backref="user", lazy=True)

    __table_args__ = (
        db.UniqueConstraint('email', name='uq_user_email'),  # Named unique constraint
    )

class Bet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    parlay = db.Column(db.String(500), nullable=False)  # JSON string
    stake = db.Column(db.Float, nullable=False)
    outcome = db.Column(db.String(50), nullable=True)  # 'Win', 'Loss', 'Pending'
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

# ------------------------------
# Create database tables if they don't exist
# ------------------------------
with app.app_context():
    db.create_all()

# ------------------------------
# User Loader for Flask-Login
# ------------------------------
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ------------------------------
# Context Processor
# ------------------------------
@app.context_processor
def inject_now():
    return {"now": datetime.utcnow()}

# ------------------------------
# Routes
# ------------------------------

@app.route('/', methods=['GET'])
def index():
    """
    Home page of the application.
    """
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    """
    User registration route.
    """
    form = RegistrationForm()
    if form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        password = form.password.data

        # Check if username already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash("Username already exists. Please choose a different one.", "error")
            return redirect(url_for("register"))

        # Check if email already exists
        existing_email = User.query.filter_by(email=email).first()
        if existing_email:
            flash("Email already registered. Please use a different one.", "error")
            return redirect(url_for("register"))

        # Create new user
        password_hash = generate_password_hash(password)
        new_user = User(username=username, email=email, password_hash=password_hash)
        db.session.add(new_user)
        db.session.commit()

        flash("Registration successful. Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html", form=form)

@app.route("/login", methods=["GET", "POST"])
def login():
    """
    User login route.
    """
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        # Find user by username
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash("Logged in successfully.", "success")
            return redirect(url_for("index"))
        else:
            flash("Invalid username or password.", "error")

    return render_template("login.html", form=form)

@app.route("/logout")
@login_required
def logout():
    """
    User logout route.
    """
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))

@app.route("/games", methods=["GET", "POST"])
@login_required
def games():
    """
    Route to select games for parlay.
    """
    if request.method == "POST":
        season = request.form.get("season")
        week = request.form.get("week")
        if not season or not week:
            flash("Please provide both season and week.", "error")
            return redirect(url_for("games"))
        try:
            week = int(week)
        except ValueError:
            flash("Week must be an integer.", "error")
            return redirect(url_for("games"))

        # Fetch games with odds
        games = get_games_and_odds(season, week)
        if not games:
            flash("No games found for the selected season and week.", "info")
            return redirect(url_for("games"))

        # Fetch advanced metrics
        adv_metrics = get_advanced_metrics(season, week)
        if not adv_metrics:
            flash("Advanced metrics not available.", "warning")

        # Predict outcomes
        predicted_games = predict_outcomes(games, adv_metrics)

        return render_template("games.html", games=predicted_games, season=season, week=week)

    return render_template("games_select.html")

@app.route("/parlay", methods=["POST"])
@login_required
def parlay():
    """
    Route to create and save a parlay bet.
    """
    selected_games = request.form.getlist("selected_games")
    if not selected_games:
        flash("No games selected for parlay.", "error")
        return redirect(url_for("games"))

    # Retrieve season and week from hidden fields
    season = request.form.get("season")
    week = request.form.get("week")
    if not season or not week:
        flash("Season and week information missing.", "error")
        return redirect(url_for("games"))
    try:
        week = int(week)
    except ValueError:
        flash("Week must be an integer.", "error")
        return redirect(url_for("games"))

    # Fetch detailed data for selected games
    games = get_games_and_odds(season, week)
    if not games:
        flash("No games found for the selected season and week.", "info")
        return redirect(url_for("games"))

    games_with_predictions = [g for g in games if str(g["GameID"]) in selected_games]
    if not games_with_predictions:
        flash("Selected games not found in the fetched games.", "error")
        return redirect(url_for("games"))

    # Fetch player props for all selected games
    all_player_props = []
    for game in games_with_predictions:
        props = get_player_props(game["GameID"])
        all_player_props.extend(props)

    # Build parlay
    parlay = build_optimal_parlay(selected_games, games_with_predictions, all_player_props)

    # Calculate stake
    stake = calculate_stakes(parlay)

    # Save bet to database
    parlay_json = json.dumps(parlay)
    new_bet = Bet(parlay=parlay_json, stake=stake, user_id=current_user.id)
    db.session.add(new_bet)
    db.session.commit()

    flash("Parlay created and saved successfully.", "success")
    return render_template("parlay.html", legs=parlay, stake=stake)

@app.route("/live")
@login_required
def live_updates():
    """
    Route to display live odds updates.
    """
    # Example: Fetch live odds for the current week
    # In a real app, determine the current week dynamically
    season = "2024"
    week = "15"  # Assuming current week is 15
    live_odds = analyze_line_movement(season, week)
    return render_template("live.html", odds=live_odds)

@app.route("/futures", methods=["GET"])
@login_required
def futures():
    """
    Route to display futures markets.
    """
    # Fetch futures markets from SportsDataIO
    season = "2024"
    futures_url = f"https://api.sportsdata.io/v3/cfb/odds/json/BettingFuturesBySeason/{season}"
    try:
        futures_resp = requests.get(futures_url, params={"key": os.getenv("SDIO_API_KEY")}, timeout=10)
        logger.debug(f"GET {futures_resp.url} - Status Code: {futures_resp.status_code}")
        if futures_resp.status_code != 200:
            flash("Error fetching futures markets.", "error")
            futures_data = []
        else:
            futures_data = futures_resp.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Request exception while fetching futures markets: {e}")
        flash("Error fetching futures markets.", "error")
        futures_data = []

    return render_template("futures.html", futures=futures_data)

@app.route("/betting_splits/<market_id>", methods=["GET"])
@login_required
def betting_splits_route(market_id):
    """
    Route to display betting splits for a specific market.
    """
    splits = get_betting_splits(market_id)
    return render_template("betting_splits.html", splits=splits, market_id=market_id)

@app.route("/injuries", methods=["GET"])
@login_required
def injuries():
    """
    Route to display injured players.
    """
    injured_players = get_injured_players()
    return render_template("injuries.html", injuries=injured_players)

@app.route("/past_bets", methods=["GET"])
@login_required
def past_bets():
    """
    Route to display user's past bets.
    """
    user_bets = Bet.query.filter_by(user_id=current_user.id).order_by(Bet.timestamp.desc()).all()
    return render_template("past_bets.html", bets=user_bets)

@app.route("/dashboard", methods=["GET"])
@login_required
def dashboard():
    """
    Route to display user dashboard with statistics.
    """
    user_bets = Bet.query.filter_by(user_id=current_user.id).all()
    # Calculate statistics like total bets, wins, losses, ROI, etc.
    total_bets = len(user_bets)
    wins = len([bet for bet in user_bets if bet.outcome == "Win"])
    losses = len([bet for bet in user_bets if bet.outcome == "Loss"])
    pending = len([bet for bet in user_bets if bet.outcome == "Pending"])
    total_stake = sum(bet.stake for bet in user_bets)
    total_return = sum(
        bet.stake * (1 + float(json.loads(bet.parlay)[0]["odds"].replace('-', '')) / 100)
        for bet in user_bets
        if bet.outcome == "Win"
    )
    roi = ((total_return - total_stake) / total_stake) * 100 if total_stake > 0 else 0

    stats = {
        "total_bets": total_bets,
        "wins": wins,
        "losses": losses,
        "pending": pending,
        "total_stake": total_stake,
        "total_return": total_return,
        "roi": round(roi, 2),
    }

    return render_template("dashboard.html", stats=stats)

# ------------------------------
# Run the Application
# ------------------------------
if __name__ == "__main__":
    app.run(debug=True)
