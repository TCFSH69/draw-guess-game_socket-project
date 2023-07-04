import socket
import json
import threading
import shared_lib
import random
import time

message_objs = []
uid_username = {}
scoreboard = {}
uids = []
topics = list(map(lambda x: x.strip(), open(r"./wordbank.txt", "r").readlines()))

'''
server to client
'''
predefined_dict_payloads = {
    "uid_initialization": {"type": "uid_initialization", "content": {"uid": None}},
    "user_delete": {"type": "user_delete", "content": {"uid": None}},
    "user_add": {"type": "user_add", "content": {"uid_username": None, "painter_uid": None}}, # send the list of all users when everyone is ready
    "new_round": {"type": "new_round", "content": {"painter_uid": None, "topic": None}},
    "scoreboard": {"type": "scoreboard", "content": {"uid_score": None}},
    "bingo": {"type": "bingo", "content": {"uid": None, "message": None}},
    "chat": {"type": "chat", "content": {"uid": None, "message": None}},
    "drawing_events": {"type": "drawing_events", "content": {"event": None}}, # may not use since server will only send the original data to all clients
    "game_over": {"type": "game_over", "content": {"winner_uid": None}},
}

'''
client to server
'''
'''
predefined_dict_payloads = {
    "user_ready": {"type": "user_ready", "content": {"uid": None, "username": None}},
    "chat": {"type": "chat", "content": {"uid": None, "message": None}},
    "drawing_events": {"type": "drawing_events", "content": {"event": None}},
}
'''

connections = 0    # total connections before game starts
ready_users = 0    # how many users are ready
uid_generator = 0  # a simple uid generator which generates uid from 0, 1, 2, ...
topic = ""         # topic of the round
painter_index = 0  # index of uids which indicates who's current painter
points = 30        # score for user guessing the correct answer, and it will decrese 10 every hit until reaching 10
hits = 0           # total number of users of guessing the correct answer
ending_time = None # round ending benchmark 

# to avoid race condition
lock1 = threading.Lock()
lock2 = threading.Lock()
lock3 = threading.Lock()

'''
client to server section
------------------------------------------------
'''
def recv_user_ready(data):
    global ready_users
    uid = data["content"]["uid"]
    username = data["content"]["username"]

    with lock1:
        ready_users += 1
        uid_username[uid] = username

    if ready_users == connections:
        ready_users = 0
        system_thread.start()

def recv_chat(data):
    global hits
    global points
    uid = data["content"]["uid"]
    message = data["content"]["message"]
    if message == topic:
        send_bingo(uid)
        with lock2:
            hits += 1
            scoreboard[uids[painter_index]] += 10
            scoreboard[uid] += points
            points = 10 if points == 10 else (points - 10)
        send_scoreboard()
    else:
        send_chat(data)

def recv_drawing_events(data):
    send_drawing_events(data)
'''
------------------------------------------------
'''

'''
server to client section
------------------------------------------------
'''
def send_uid_initialization(msgobj):
    data = predefined_dict_payloads["uid_initialization"]
    data["content"]["uid"] = msgobj.getuid()
    msgobj.send(data)

def send_user_delete(msgobj):
    global connections
    uid = msgobj.getuid()
    data = predefined_dict_payloads["user_delete"]
    data["content"]["uid"] = uid
    connections -= 1
    uids.remove(uid)
    message_objs.remove(msgobj)
    message_obj.close()
    # send after removing that socket
    send_to_all_clients(data)

def send_user_add():
    data = predefined_dict_payloads["user_add"]
    data["content"]["uid_username"] = uid_username
    data["content"]["painter_uid"] = uids[painter_index]
    send_to_all_clients(data)

def send_new_round():
    global painter_index
    round_reset()
    data = predefined_dict_payloads["new_round"]
    data["content"]["painter_uid"] = uids[painter_index]
    data["content"]["topic"] = topic
    send_to_all_clients(data)

def send_scoreboard():
    data = predefined_dict_payloads["scoreboard"]
    data["content"]["uid_score"] = scoreboard
    send_to_all_clients(data)

def send_bingo(uid):
    data = predefined_dict_payloads["bingo"]
    data["content"]["uid"] = uid
    data["content"]["message"] = f"{uid_username[uid]} has found the answer!"
    send_to_all_clients(data)

def send_chat(data):
    send_to_all_clients(data)

def send_drawing_events(data):
    with lock3:
        for _msgobj in message_objs:
            if _msgobj.getuid() != uids[painter_index]:
                _msgobj.send(data)

def send_game_over(uid):
    data = predefined_dict_payloads["game_over"]
    data["content"]["winner_uid"] = uid
    send_to_all_clients(data)
'''
------------------------------------------------
'''

'''
general function section
------------------------------------------------
'''
def send_to_all_clients(data):
    with lock3:
        for _msgobj in message_objs:
            _msgobj.send(data)

def scoreboard_reset():
    for uid in uids:
        scoreboard[uid] = 0

def has_winner():
    max_uid = -1
    max_score = 0
    for uid, score in scoreboard.items():
        if max_score < score:
            max_uid = uid
            max_score = score

    return max_uid if max_score >= 120 else -1

def round_reset():
    global hits
    global points
    global topic
    global ending_time
    hits = 0
    points = 30
    topic = random.choice(topics)
    ending_time = time.time() + 60 # 可以設65秒之類的讓中間有過渡畫面，因為client會沒收到new_round
'''
------------------------------------------------
'''

def game_system():
    global painter_index
    # game prerequisite
    send_user_add()
    scoreboard_reset()
    send_new_round()
    time.sleep(1)
    send_scoreboard()

    # update new round if time's up or everyone hits
    while True:
        if hits == connections - 1 or time.time() >= ending_time:
            uid = has_winner()
            # someone reaches winning condition, then game over
            if uid != -1:
                send_game_over(uid)
                # close all sockets
                for msgobj in message_objs:
                    msgobj.close()
                break

            # not game over yet, update painter idnex and start new round
            painter_index = (painter_index + 1) % len(uids)
            send_new_round()
            time.sleep(1)
            send_scoreboard()
        time.sleep(1)

def data_processing(data):
    global uid_generator
    data_type = data["type"]
    
    # Three kinds of data type for a packet sending from client to server
    if data_type == "user_ready":
        recv_user_ready(data)

    elif data_type == "chat":
        recv_chat(data)

    elif data_type == "drawing_events":
        recv_drawing_events(data)

    else:
        print("Unknown data type.")



def handle_client(msgobj):
    try:
        global connections
        # receive data, in blocking state
        while True:
            data = msgobj.recv()
            if data is None:
                break

            # process data by type
            data_processing(data)

        # connection closed
        send_user_delete(msgobj)
        
    except ConnectionResetError:
        print("Connection ends.")

# server socket initialization
server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind(("172.20.10.7", 4443))
server_socket.listen(4)

print("Server started. Waiting for connections...")

# the thread which controls the game flow
system_thread = threading.Thread(target=game_system)

while True:
    client_socket, client_address = server_socket.accept()

    # once accepting a request, update the number of connections and allocate a uid to the client
    connections += 1
    uid = str(uid_generator)
    uids.append(uid)
    uid_generator += 1

    print(f"Connections: {connections}, uid: {uid}")

    message_obj = shared_lib.Message(client_socket, uid)
    message_objs.append(message_obj)

    send_uid_initialization(message_obj)

    # establish a thread to handle any data from the client
    client_thread = threading.Thread(target=handle_client, args=(message_obj,))
    client_thread.start()