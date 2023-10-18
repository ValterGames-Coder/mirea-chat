import base64

import requests
from flask import Flask, render_template, request, url_for, redirect, session
from flask_socketio import SocketIO, send, emit
from flask_sqlalchemy import SQLAlchemy
from flask_session import Session
import datetime

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*")


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.Text, nullable=False)
    password = db.Column(db.Text, nullable=False)
    icon = db.Column(db.Text, default='https://i.ibb.co/BCYfKPZ/icon.png')

    def __repr__(self):
        return '<User %r>' % self.id


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer)
    username = db.Column(db.Text, nullable=False)
    text = db.Column(db.Text, nullable=False)
    date = db.Column(db.DateTime, default=datetime.datetime.now)

    def __repr__(self):
        return '<Message %r>' % self.id


@socketio.on('message')
def handler_message(message):
    print(message)
    if message['text'] != "User connected!":
        text = message['text']
        user_id = message['user_id']
        username = message['username']
        message_id = message['message_id']

        if message_id is None:
            new_message = Message(text=text, user_id=user_id, username=username)

            try:
                db.session.add(new_message)
                db.session.commit()

                print('New message add!')
            except:
                print('Error Database')

            user = User.query.filter_by(id=user_id).first_or_404()
            message['icon'] = user.icon
            message['message_id'] = Message.query.count()
            message['date'] = new_message.date.strftime("%d.%m в %H:%M")
            message['is_edit'] = False
            emit('message', message, broadcast=True)
        else:
            message['is_edit'] = True
            edit_message = Message.query.filter_by(id=message_id).first_or_404()
            edit_message.text = text
            edit_message.date = datetime.datetime.now()
            message['date'] = edit_message.date.strftime("%d.%m в %H:%M")
            db.session.commit()
            print('Message edit!')
            emit('message', message, broadcast=True)


@socketio.on('delete')
def delete_message(message):
    print(message)
    message_id = message['message_id']
    Message.query.filter_by(id=message_id).delete()
    db.session.commit()
    emit('delete', message, broadcast=True)


@app.route('/login', methods=['POST', 'GET'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        try:
            if User.query.filter(User.username == username) and User.query.filter(User.password == password):
                user = User.query.filter_by(username=username, password=password).first_or_404()
                print(user.id)
                session['id'] = user.id
                return redirect(url_for('chat'))
        except:
            print('Error')
    else:
        return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))


@app.route('/profile', methods=['POST', 'GET'])
def profile():
    user_id = session.get('id')
    if user_id is None:
        return redirect(url_for('home'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        icon = request.files['icon']
        print(icon)
        if icon.filename is not '':
            params = {
                'key': 'e171bf3bf065459ac1f72c6f46dac86a',
            }
            files = {
                'image': icon,
            }
            response = requests.post('https://api.imgbb.com/1/upload', params=params, files=files)
            file = response.json()['data']['url']
        else:
            file = 'https://i.ibb.co/BCYfKPZ/icon.png'

        try:
            edit_user = User.query.filter_by(id=user_id).first_or_404()
            edit_user.username = username
            edit_user.password = password
            edit_user.icon = file
            print(edit_user.icon)
            db.session.commit()
            return render_template('profile.html')
        except:
            print('Error Database')
    return render_template('profile.html')


@app.route('/signup', methods=['POST', 'GET'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        icon = request.files['icon']

        if icon is not None:
            params = {
                'key': 'e171bf3bf065459ac1f72c6f46dac86a',
            }
            files = {
                'image': icon,
            }
            response = requests.post('https://api.imgbb.com/1/upload', params=params, files=files)
            file = response.json()['data']['url']

            user = User(username=username, password=password, icon=file)
        else:
            user = User(username=username, password=password)

        try:
            if User.query.filter(User.username != username) and User.query.filter(User.password != password):
                db.session.add(user)
                db.session.commit()
                session['id'] = user.id
                return redirect(url_for('chat'))
        except:
            print('Error Database')
    else:
        return render_template('signup.html')


@app.route('/chat')
def chat():
    try:
        user_id = session.get('id')
        if user_id is None:
            return 'You don\'t login\n<a href="/">Back</a>'
        if User.query.filter(User.id == user_id):
            user = User.query.filter_by(id=user_id).first()
            db.session.commit()
            #session.clear()
            return render_template('chat.html', user=user)
    except:
        return 'You don\'t login\n<a href="/">Back</a>'


    return render_template('chat.html')


@app.route('/')
def home():
    user_id = session.get('id')
    if user_id is not None:
        if User.query.filter(User.id == user_id):
            return redirect(url_for('chat'))
    return render_template('home.html')


if __name__ == '__main__':
    app.run(debug=True)