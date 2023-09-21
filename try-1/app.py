from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from bs4 import BeautifulSoup
import requests
from flask_pymongo import PyMongo
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
import openai
from flask_mail import Mail, Message
from config import MONGODB, YOUTUBE_API, CHATGPT_API, SECRET_KEY


app = Flask(__name__)


from pymongo import MongoClient

client = MongoClient(
MONGODB
)

db = client.test1

db = client.users2  # Connect to the 'users2' database
users_collection = db.users  # Connect to the 'users' collection within 'users2'

# Flask-Login Configuration
login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)


# User model
class User(UserMixin):
    def __init__(self, user_id):
        self.id = user_id


# Load user from MongoDB
@login_manager.user_loader
def load_user(user_id):
    return User(user_id)


@app.route("/")
def home():
    return render_template("index.html")


# Signup route
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        hashed_password = generate_password_hash(password, method="sha256")

        # Check if username is already taken
        if users_collection.find_one({"username": username}):
            flash("Username is already taken.")
            return redirect(url_for("signup"))

        # Create a new user document
        user_id = users_collection.insert_one(
            {"username": username, "password": hashed_password}
        ).inserted_id

        # Log the user in
        user = User(str(user_id))
        login_user(user)
        return redirect(url_for("home"))

    return render_template("signup.html")


# Login route
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user_data = users_collection.find_one({"username": username})

        if user_data and check_password_hash(user_data["password"], password):
            user = User(str(user_data["_id"]))
            login_user(user)
            return redirect(url_for("home"))
        else:
            flash("Login failed. Check your credentials.")

    return render_template("login.html")


# Initialize Flask-Mail
mail = Mail(app)


# Password Reset Request route
@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form[
            "email"
        ]  # You can use email or username as per your user data structure

        # Check if the email exists in your database
        user_data = users_collection.find_one(
            {"email": email}
        )  # Replace with your actual user data structure

        if user_data:
            # Generate a unique token for password reset (you can use a library like secrets)
            import secrets

            reset_token = secrets.token_hex(16)

            # Save the reset token and its expiration time in your database
            # For example, you can create a password_reset_tokens collection

            # Send the password reset email
            msg = Message(
                "Password Reset", sender="your_email@gmail.com", recipients=[email]
            )
            msg.body = f"Click the following link to reset your password: {url_for('reset_password', token=reset_token, _external=True)}"
            mail.send(msg)

            flash("A password reset email has been sent to your email address.")
            return redirect(url_for("login"))
        else:
            flash("Email not found. Please check your email address.")

    return render_template("forgot_password.html")


# Logout route
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("home"))


# Folder POST
@app.route("/folder", methods=["POST"])
def folder_post():
    url_receive = request.form["url_give"]
    category_receive = request.form["category_give"]
    note_receive = request.form["note_give"]

    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36 Edg/116.0.1938.69"
    }

    data = requests.get(url_receive, headers=headers)

    soup = BeautifulSoup(data.text, "html.parser")

    og_image = soup.select_one('meta[property="og:image"]')
    og_title = soup.select_one('meta[property="og:title"]')

    image = og_image["content"]
    title = og_title["content"]
    url = url_receive

    doc = {
        "image": image,
        "title": title,
        "category": category_receive,
        "note": note_receive,
        "url": url,
    }

    db.folder.insert_one(doc)

    return jsonify({"msg": "POST request!"})


# Community Post
@app.route("/community", methods=["POST"])
def community_post():
    url_receive = request.form["url_give"]
    category_receive = request.form["category_give"]
    thoughts_receive = request.form["thoughts_give"]

    count = db.community.count_documents({})
    num = count + 1

    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36 Edg/116.0.1938.69"
    }

    data = requests.get(url_receive, headers=headers)

    soup = BeautifulSoup(data.text, "html.parser")

    og_image = soup.select_one('meta[property="og:image"]')
    og_title = soup.select_one('meta[property="og:title"]')

    image = og_image["content"]
    title = og_title["content"]
    url = url_receive

    doc = {
        "num": num,
        "image": image,
        "title": title,
        "category": category_receive,
        "thoughts": thoughts_receive,
        "url": url,
        "done": 0,
    }

    db.community.insert_one(doc)

    return jsonify({"msg": "Data Saved!"})


# Folder GET
@app.route("/folder", methods=["GET"])
def folder_get():
    folder_list = list(db.folder.find({}, {"_id": False}))
    return jsonify({"folder": folder_list})


#  Video Marker Done
@app.route("/video/done", methods=["POST"])
def vidoe_done():
    num_receive = request.form["num_give"]
    db.community.update_one({"num": int(num_receive)}, {"$set": {"done": 1}})
    return jsonify({"msg": "Update Done"})


# Video Delete Now
@app.route("/delete", methods=["POST"])
def delete_community_video():
    num_receive = request.form["num_give"]
    db.community.delete_one({"num": int(num_receive)})
    return jsonify({"msg": "delete done!"})


# Community GET
@app.route("/community", methods=["GET"])
def community_get():
    community_list = list(db.community.find({}, {"_id": False}))
    return jsonify({"community": community_list})


# Subjects Video Fetching


API_KEY = YOUTUBE_API

PLAYLIST_ID_CS = "PL8dPuuaLjXtNlUrzyH5r6jN9ulIgZBpdo"
PLAYLIST_ID_MATH = "PLybg94GvOJ9FoGQeUMFZ4SWZsr30jlUYK"
PLAYLIST_ID_FIN = "PLmSGbCS0swswHGaytV6QQkyA9tGR7i0tV"
PLAYLIST_ID_BLOCK = "PLUl4u3cNGP63UUkfL0onkxF6MYgVa04Fn"


def fetch_playlist_videos_cs():
    url = "https://www.googleapis.com/youtube/v3/playlistItems"
    params = {
        "part": "snippet",
        "playlistId": PLAYLIST_ID_CS,
        "key": API_KEY,
        "maxResults": 12,  # Adjust as needed
    }
    response = requests.get(url, params=params)
    return response.json()


def fetch_playlist_videos_maths():
    url = "https://www.googleapis.com/youtube/v3/playlistItems"
    params = {
        "part": "snippet",
        "playlistId": PLAYLIST_ID_MATH,
        "key": API_KEY,
        "maxResults": 12,  # Adjust as needed
    }
    response = requests.get(url, params=params)
    return response.json()


def fetch_playlist_videos_fin():
    url = "https://www.googleapis.com/youtube/v3/playlistItems"
    params = {
        "part": "snippet",
        "playlistId": PLAYLIST_ID_FIN,
        "key": API_KEY,
        "maxResults": 12,  # Adjust as needed
    }
    response = requests.get(url, params=params)
    return response.json()


def fetch_playlist_videos_block():
    url = "https://www.googleapis.com/youtube/v3/playlistItems"
    params = {
        "part": "snippet",
        "playlistId": PLAYLIST_ID_BLOCK,
        "key": API_KEY,
        "maxResults": 12,  # Adjust as needed
    }
    response = requests.get(url, params=params)
    return response.json()


# Route for Computer Science (CS)
@app.route("/cs")
def cs():
    login_required
    playlist_videos = fetch_playlist_videos_cs()
    return render_template("cs.html", playlist_videos=playlist_videos)


# Route for Mathematics
@app.route("/maths")
def maths():
    login_required
    playlist_videos = fetch_playlist_videos_maths()
    return render_template("maths.html", playlist_videos=playlist_videos)


# Route for Finance
@app.route("/fi")
def fin():
    login_required
    playlist_videos = fetch_playlist_videos_fin()
    return render_template("fin.html", playlist_videos=playlist_videos)


# Route for Blockchain
@app.route("/block")
def block():
    login_required
    playlist_videos = fetch_playlist_videos_block()
    return render_template("block.html", playlist_videos=playlist_videos)


@app.route("/moreSubjects")
def moreSubjects():
    login_required
    return render_template("moreSubjects.html")


openai.api_key = CHATGPT_API


@app.route("/aim", methods=["POST"])
def ai():
    message = []
    # message.append(request.form["message_give"])
    print(message)
    message.append({"role": "system", "content": request.form["message_give"]})

    # message.append({"role": "user", "content": message})

    response = openai.ChatCompletion.create(model="gpt-3.5-turbo", messages=message)

    reply = response["choices"][0]["message"]["content"]

    return jsonify({"msg": reply})

@app.route('/meme',)
def meme():
    return render_template('meme.html')


if __name__ == "__main__":
    app.secret_key = SECRET_KEY
    app.run(debug=True)
