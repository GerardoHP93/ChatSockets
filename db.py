import os
from datetime import datetime
from bson import ObjectId
from pymongo import MongoClient, DESCENDING
from werkzeug.security import generate_password_hash, check_password_hash
from user import User
from dotenv import load_dotenv

client = MongoClient(os.getenv('MONGODB_URI'))


#Send a ping
try:
  client.admin.command('ping')
  # print("CONECTADO CORRECTAMENTE")
except Exception as e:
  print(e)

chat_db= client.get_database('ChatDB')
users_collection = chat_db.get_collection('users')
rooms_collection = chat_db.get_collection("rooms")
room_members_collection = chat_db.get_collection("room_members")
messages_collection = chat_db.get_collection("messages")


def save_user(username, email, password):
    password_hash = generate_password_hash(password)
    users_collection.insert_one({'_id': username, 'email': email, 'password': password_hash})

def get_user(username):
    user_data = users_collection.find_one({'_id': username})

    return User(user_data['_id'], user_data['email'], user_data['password']) if user_data else None

#Nuevo video 5
def save_room(room_name, created_by):
    room_id = rooms_collection.insert_one(
        {'name': room_name, 'created_by': created_by, 'created_at': datetime.now()}).inserted_id
    #Añadir administrador, por eso el created_by es el mismo del quien lo creo, osea el creador es el admin y added_by por si mismo obvio.
    add_room_member(room_id, room_name, created_by, created_by, is_room_admin=True)
    return room_id


def update_room(room_id, room_name):
    rooms_collection.update_one({'_id': ObjectId(room_id)}, {'$set': {'name': room_name}})
    room_members_collection.update_many({'_id.room_id': ObjectId(room_id)}, {'$set': {'room_name': room_name}})

#El objetId(room_id) es porque en mongo el id se maneja como un tipo de dato especial "ObjectId" entonces si quieres hacer consultas en mongo, hay que convertir el string _id a un onjectId para que si lo encuentre en mongo
def get_room(room_id):
    return rooms_collection.find_one({'_id': ObjectId(room_id)})

#Añadir UN miembro
def add_room_member(room_id, room_name, username, added_by, is_room_admin=False):
    room_members_collection.insert_one(
        {'_id': {'room_id': ObjectId(room_id), 'username': username}, 'room_name': room_name, 'added_by': added_by,
         'added_at': datetime.now(), 'is_room_admin': is_room_admin})

#Añadir varios miembros
def add_room_members(room_id, room_name, usernames, added_by):
    room_members_collection.insert_many(
        [{'_id': {'room_id': ObjectId(room_id), 'username': username}, 'room_name': room_name, 'added_by': added_by,
          'added_at': datetime.now(), 'is_room_admin': False} for username in usernames])

def remove_room_members(room_id, usernames):
    room_members_collection.delete_many(
        {'_id': {'$in': [{'room_id': ObjectId(room_id), 'username': username} for username in usernames]}})

#Se hace el _id.room_id ya que nosotros definimos el id eb agregar miembros "room_member" como id compuesto, entonces tenemos que especificar en el filtro buscamos los miembros que tengan room.id igual al room_id buscado.
def get_room_members(room_id):
    return list(room_members_collection.find({'_id.room_id': ObjectId(room_id)}))

#Para buscar salas por su username
def get_rooms_for_user(username):
    return list(room_members_collection.find({'_id.username': username}))

def is_room_member(room_id, username):
    return room_members_collection.count_documents({'_id': {'room_id': ObjectId(room_id), 'username': username}})

def is_room_admin(room_id, username):
    return room_members_collection.count_documents(
        {'_id': {'room_id': ObjectId(room_id), 'username': username}, 'is_room_admin': True})

def save_message(room_id, text, sender):
    messages_collection.insert_one({'room_id': room_id, 'text': text, 'sender': sender, 'created_at': datetime.now()})


MESSAGE_FETCH_LIMIT = 5

def get_messages(room_id, page=0):
    offset = page * MESSAGE_FETCH_LIMIT
    messages = list(
        messages_collection.find({'room_id': room_id}).sort('_id', DESCENDING).limit(MESSAGE_FETCH_LIMIT).skip(offset))
    for message in messages:
        message['created_at'] = message['created_at'].strftime("%d %b, %H:%M")
    return messages[::-1]


def leave_room_db(room_id, username):
    # No permitir que el admin abandone la sala
    if is_room_admin(room_id, username):
        return False

    room_members_collection.delete_one(
        {'_id': {'room_id': ObjectId(room_id), 'username': username}}
    )
    return True