import tkinter as tk
import socket
import threading
import shared_lib
import json

color_id = {
    'red': '#B22222',
    'orange': '#FF8C00',
    'yellow': '#FFD700',
    'green': '#228B22',
    'blue': '#4169E1',
    'purple': '#8A2BE2',
    'black': '#000000',
    'white': '#F5F5F5'
}

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect(("172.20.10.7", 4443))

message_obj = shared_lib.Message(client_socket)

drawing_user = None
p_list = None
score = None
question = None
current_user = None
maintk = None
countdown_id = None
canvas = None
g_canvas = None

def update_countdown(minutes, seconds):
    countdown_label['text'] = f"Time Left: {minutes:02d} : {seconds:02d}"
    if seconds > 0:
        seconds -= 1
    elif minutes > 0:
        minutes -= 1
        seconds = 59
    else:
        # Timer has reached 0
        return
    global countdown_id
    countdown_id = maintk.after(1000, update_countdown, minutes, seconds)

def data_receive(msgobj):
    global p_list, score, drawing_user, question, current_user
    global g_clear, g_lastx, g_lasty, g_eventx, g_eventy, g_color
    global countdown_id
    while True:
        data = msgobj.recv()
        if data is None:
                break
        

        data_type = data['type']
        data_content = data['content']

        if(data_type == 'uid_initialization'): #send name後，收到自己的uid
            current_user = data_content['uid']

        elif(data_type == 'user_delete'): 
            delete_id = data_content['uid']
            del p_list[delete_id]
            del score[delete_id]
            update_user_list()
            update_score_board()

        elif(data_type == 'user_add'): #game start
            p_list = data_content['uid_username']  
            drawing_user = data_content['painter_uid']
            main()          

        elif(data_type == 'new_round'): 
            maintk.destroy()
            
            drawing_user = data_content['painter_uid']
            question = data_content['topic']
            main()
            
            maintk.after_cancel(countdown_id)
            update_countdown(1, 0)            
            if(current_user == drawing_user):
                input_entry.configure(state="readonly")
                send_button.config(state="disabled")
            else:
                input_entry.configure(state="normal")
                send_button.config(state="normal")

            update_user_list()
            
            

            

        elif(data_type == 'scoreboard'): 
            score = data_content['uid_score']
            update_score_board()

        elif(data_type == 'chat'):
            player = p_list[(data_content['uid'])]
            message_update = data_content['message']
            display_box.configure(state='normal')
            display_box.insert(tk.END, f'{player}: {message_update}\n\n')
            display_box.configure(state='disabled')

        elif(data_type == 'bingo'):
            if(current_user == data_content['uid']):
                input_entry.configure(state="readonly")
                send_button.config(state="disabled")

            message_update = data_content["message"]
            
            display_box.configure(state='normal')
            display_box.insert(tk.END, f'"[SYSTEM]" {message_update}\n\n', "red")
            display_box.configure(state='disabled')


        elif(data_type == 'drawing_events'): 
            g_clear = data_content['event']['clear']
            g_eventx = data_content['event']['eventx']
            g_eventy = data_content['event']['eventy']
            g_lastx = data_content['event']['lastx']
            g_lasty = data_content['event']['lasty']
            g_color = data_content['event']['color']
            
            if g_clear:
                g_canvas.delete('draw')

            elif (g_eventx - g_lastx) != 0 or (g_eventy - g_lasty) != 0:
                if g_color == 'white':
                    g_canvas.create_line((g_lastx, g_lasty, g_eventx, g_eventy), fill=color_id['white'], width=15, tags='draw')
                else:
                    g_canvas.create_line((g_lastx, g_lasty, g_eventx, g_eventy), fill=color_id[g_color], width=3, tags='draw')

        elif(data_type == 'game_over'):
            winner = data_content['winner_uid']
            game_over(winner)
            
        else:
            print("unknown type")

receive_thread = threading.Thread(target=data_receive, args = (message_obj,))
receive_thread.start()


def user_ready(msgobj):
    send_message = {"type": "user_ready", "content": {"uid": current_user, "username": name}}
    msgobj.send(send_message)

def send_paint_update(msgobj, eventx, eventy):
    send_message = {"type": "drawing_events", "content":{"event":{"clear": False, "eventx": eventx, "eventy": eventy, "lastx":lastx, "lasty":lasty, "color":brush_color}}}
    msgobj.send(send_message)

def send_clear_canvas(msgobj):
    send_message = {"type": "drawing_events", "content":{"event":{"clear": True, "eventx": 0, "eventy": 0, "lastx":lastx, "lasty":lasty, "color":brush_color}}}
    msgobj.send(send_message)

def click_chat_button(msgobj):
    send_message = {"type": "chat", "content":{"uid": current_user, "message": message_text}}
    msgobj.send(send_message)

def update_user_list():
    user_listbox.delete(0, tk.END)
    for id, user in p_list.items():
        if id == drawing_user:
            user_listbox.insert(tk.END, f'{user} [drawing...]')
        elif id == current_user:
            user_listbox.insert(tk.END, f'{user} [you]')
        else:
            user_listbox.insert(tk.END, user)

def update_score_board():
    for widget in scoreboard_frame.winfo_children():
            widget.destroy()

    scoreboard_label = tk.Label(scoreboard_frame, text="Scoreboard", font=("Arial", 12), fg="black")
    scoreboard_label.pack(side=tk.TOP, padx=10, pady=10)

    for id, user in p_list.items():
        score_label = tk.Label(scoreboard_frame, text=f'{user}: {score[id]}', font=("Arial", 10), fg="black")
        score_label.pack(side=tk.TOP, padx=10, pady=0)

# def canvas():
#     if current_user == drawing_user:
#         global question_label
#         # Question label
#         question_label = tk.Label(maintk, text=question, font=("Arial", 12), fg="black")
#         question_label.grid(row=0, column=1, rowspan=1, sticky='n', padx=10, pady=10)

#         global lastx, lasty, brush_color
#         lasty, lastx = 0, 0
#         brush_color = 'black'
#         eraser_active = False

#         def xy(event):
#             global lastx, lasty
#             lastx = event.x
#             lasty = event.y

#         def addLine(event):
#             if eraser_active:
#                 canvas.create_line((lastx, lasty, event.x, event.y), fill=color_id['white'], width=15, tags='draw')
#             else:
#                 canvas.create_line((lastx, lasty, event.x, event.y), fill=color_id[brush_color], width=3, tags='draw')
            
#             send_paint_update(message_obj, event.x, event.y)

#             lasty = event.y
#             lastx = event.x

#         def clear_canvas():
#             canvas.delete('draw')
#             send_clear_canvas(message_obj)

#         def change_color(color_name):
#             nonlocal eraser_active
#             global brush_color
#             if color_name == 'white':
#                 brush_color = 'white'
#                 eraser_active = True
#             else:
#                 brush_color = color_name
#                 eraser_active = False

#         global canvas
#         canvas = tk.Canvas(maintk, width=400, height=650, bg='#F5F5F5')
#         canvas.grid(row=0, column=1, rowspan=8, sticky='nsew', padx=10, pady=50)
#         canvas.bind('<Button-1>', xy)
#         canvas.bind('<B1-Motion>', addLine)

#         colors = list(color_id.keys())
#         for i, color_name in enumerate(colors):
#             y = 40 + (i * 50)
#             if color_name == 'white':
#                 oval = canvas.create_oval(10, y, 30, y + 20, fill=color_id[color_name], tags=color_name)
#             else:
#                 oval = canvas.create_oval(10, y, 30, y + 20, fill=color_id[color_name], tags=color_name)
#             canvas.tag_bind(oval, '<Button-1>', lambda event, name=color_name: change_color(name))

#         clear_button = tk.Button(canvas, text="Clear", command=clear_canvas)
#         clear_button.place(x=10, y=430)

#     # guess
#     else:
#         global g_canvas
#         g_canvas = tk.Canvas(maintk, width=400, height=380, bg='#F5F5F5')
#         g_canvas.grid(row=0, column=1, rowspan=4, sticky='nsew', padx=10, pady=10)

#         global g_clear, g_lastx, g_lasty, g_eventx, g_eventy, g_color
#         g_clear = False
#         g_lastx, g_lasty, g_eventx, g_eventy = 0, 0, 0, 0
#         g_color = ''


    

def log_in():
    global login
    login = tk.Tk()
    login.title("Log in")
    login.geometry('300x200')

    label = tk.Label(login, text="Please enter your user name:")
    label.grid(row=0, column=0, padx=10, pady=10, sticky='w')

    entry = tk.Entry(login, width=25)
    entry.grid(row=1, column=0, padx=10, sticky='ew')

    def ready():
        ready_button.config(state="disabled")
        user_ready(message_obj)
        

    def confirm_name():
        global name
        name = entry.get()
        entry.configure(state="readonly") #送出後唯讀

        welcome = tk.Label(login, height=3, width=20, text=f"Hello, {name}!\n")
        welcome.grid(row=2, column=0, padx=10, pady=10, sticky='n')

        global ready_button
        ready_button = tk.Button(login, text="Ready", command=ready)
        ready_button.grid(row=3, column=0, padx=10, pady=10, sticky='e')

    button = tk.Button(login, text="enter", command=confirm_name)
    button.grid(row=3, column=0, padx=10, pady=10, sticky='e')

    login.grid_rowconfigure(0, weight=1)
    login.grid_rowconfigure(1, weight=1)
    login.grid_rowconfigure(2, weight=1)
    login.grid_rowconfigure(3, weight=1)
    login.grid_columnconfigure(0, weight=1)

    login.mainloop()

def main():
    login.withdraw()

    global maintk
    maintk = tk.Toplevel()
    maintk.title("Drawing Game")
    maintk.columnconfigure(0, weight=1)
    maintk.columnconfigure(1, weight=2)
    maintk.columnconfigure(2, weight=1)
    maintk.rowconfigure(0, weight=1)
    maintk.rowconfigure(1, weight=1)
    maintk.rowconfigure(2, weight=1)
    maintk.rowconfigure(3, weight=1)
    maintk.rowconfigure(4, weight=1)
    maintk.rowconfigure(5, weight=1)
    maintk.geometry('800x600')

    # Countdown Timer
    global countdown_label
    countdown_label = tk.Label(maintk, font=("Arial", 12), text="Time Left: 01 : 00")
    countdown_label.grid(row=0, column=0, columnspan=2, sticky='nw', padx=10, pady=10)

    update_countdown(1, 0) 

    # User List
    user_list_frame = tk.Frame(maintk)
    user_list_frame.grid(row=1, column=0, sticky=tk.S, padx=10, pady=10)

    user_list_label = tk.Label(user_list_frame, text="Player List", font=("Arial", 12), fg="black")
    user_list_label.pack(side=tk.TOP, padx=10, pady=10)
    
    global user_listbox
    user_listbox = tk.Listbox(user_list_frame)
    user_listbox.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=10)
    

    # Scoreboard
    global scoreboard_frame

    scoreboard_frame = tk.Frame(maintk)
    scoreboard_frame.grid(row=2, column=0, rowspan=4, sticky='nsew', padx=10, pady=10)

    global question
    # Canvas
    # drawing
    if current_user == drawing_user:
        # Question label
        
        question_label = tk.Label(maintk, text=question, font=("Arial", 12), fg="black")
        question_label.grid(row=0, column=1, rowspan=1, sticky='n', padx=10, pady=10)

        global lastx, lasty, brush_color
        lasty, lastx = 0, 0
        brush_color = 'black'
        eraser_active = False

        def xy(event):
            global lasty, lastx
            lastx = event.x
            lasty = event.y

        def addLine(event):
            global lasty, lastx
            if eraser_active:
                canvas.create_line((lastx, lasty, event.x, event.y), fill=color_id['white'], width=15, tags='draw')
            else:
                canvas.create_line((lastx, lasty, event.x, event.y), fill=color_id[brush_color], width=3, tags='draw')
            send_paint_update(message_obj, event.x, event.y)
            lasty = event.y
            lastx = event.x

        def clear_canvas():
            canvas.delete('draw')
            send_clear_canvas(message_obj)

        def change_color(color_name):
            global brush_color, eraser_active
            if color_name == 'white':
                brush_color = 'white'
                eraser_active = True
            else:
                brush_color = color_name
                eraser_active = False

        
        canvas = tk.Canvas(maintk, width=400, height=650, bg='#F5F5F5')
        canvas.grid(row=0, column=1, rowspan=8, sticky='nsew', padx=10, pady=50)
        canvas.bind('<Button-1>', xy)
        canvas.bind('<B1-Motion>', addLine)

        colors = list(color_id.keys())
        for i, color_name in enumerate(colors):
            y = 40 + (i * 50)
            oval = canvas.create_oval(10, y, 30, y + 20, fill=color_id[color_name], tags=color_name)
            canvas.tag_bind(oval, '<Button-1>', lambda event, name=color_name: change_color(name))

        clear_button = tk.Button(canvas, text="Clear", command=clear_canvas)
        clear_button.place(x=10, y=430)

    # guess
    else:
        global g_canvas, g_clear,g_lastx, g_lasty, g_eventx, g_eventy, g_color
        g_canvas = tk.Canvas(maintk, width=400, height=380, bg='#F5F5F5')
        g_canvas.grid(row=1, column=1, rowspan=6, sticky='nsew', padx=10, pady=10)

        g_clear = False
        g_lastx, g_lasty, g_eventx, g_eventy = 0, 0, 0, 0
        g_color = ''

        

    # if current_user == drawing_user:
    #     # Question label
    #     question_label = tk.Label(maintk, text=question, font=("Arial", 12), fg="black")
    #     question_label.grid(row=0, column=1, rowspan=1, sticky='n', padx=10, pady=10)

    #     global lastx, lasty, brush_color
    #     lasty, lastx = 0, 0
    #     brush_color = 'black'
    #     eraser_active = False

    #     def xy(event):
    #         global lastx, lasty
    #         lastx = event.x
    #         lasty = event.y

    #     def addLine(event):
    #         if eraser_active:
    #             canvas.create_line((lastx, lasty, event.x, event.y), fill=color_id['white'], width=15, tags='draw')
    #         else:
    #             canvas.create_line((lastx, lasty, event.x, event.y), fill=color_id[brush_color], width=3, tags='draw')
            
    #         send_paint_update(message_obj, event.x, event.y)

    #         lasty = event.y
    #         lastx = event.x

    #     def clear_canvas():
    #         canvas.delete('draw')
    #         send_clear_canvas(message_obj)

    #     def change_color(color_name):
    #         nonlocal eraser_active
    #         global brush_color
    #         if color_name == 'white':
    #             brush_color = 'white'
    #             eraser_active = True
    #         else:
    #             brush_color = color_name
    #             eraser_active = False

    #     global canvas
    #     canvas = tk.Canvas(maintk, width=400, height=650, bg='#F5F5F5')
    #     canvas.grid(row=0, column=1, rowspan=8, sticky='nsew', padx=10, pady=50)
    #     canvas.bind('<Button-1>', xy)
    #     canvas.bind('<B1-Motion>', addLine)

    #     colors = list(color_id.keys())
    #     for i, color_name in enumerate(colors):
    #         y = 40 + (i * 50)
    #         if color_name == 'white':
    #             oval = canvas.create_oval(10, y, 30, y + 20, fill=color_id[color_name], tags=color_name)
    #         else:
    #             oval = canvas.create_oval(10, y, 30, y + 20, fill=color_id[color_name], tags=color_name)
    #         canvas.tag_bind(oval, '<Button-1>', lambda event, name=color_name: change_color(name))

    #     clear_button = tk.Button(canvas, text="Clear", command=clear_canvas)
    #     clear_button.place(x=10, y=430)

    # # guess
    # else:
    #     global g_canvas
    #     g_canvas = tk.Canvas(maintk, width=400, height=380, bg='#F5F5F5')
    #     g_canvas.grid(row=0, column=1, rowspan=4, sticky='nsew', padx=10, pady=10)

    #     global g_clear, g_lastx, g_lasty, g_eventx, g_eventy, g_color
    #     g_clear = False
    #     g_lastx, g_lasty, g_eventx, g_eventy = 0, 0, 0, 0
    #     g_color = ''

    # receive_thread = threading.Thread(target=canvas)
    # receive_thread.start()
        

    # Message Box
    message_frame = tk.Frame(maintk)
    message_frame.grid(row=0, column=2, rowspan=5, sticky='nsew', padx=10, pady=10)

    global display_box
    display_box = tk.Text(message_frame, width=30, height=35)
    display_box.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    display_box.tag_configure("red", foreground="red")

    # for player, message_text in message.items():
    #     display_box.insert(tk.END, f'{p_list[player]}: {message_text}\n\n')

    # Input col
    input_frame = tk.Frame(message_frame)
    input_frame.pack(fill=tk.X, padx=10, pady=10)

    global input_entry
    input_entry = tk.Entry(input_frame, width=23)
    input_entry.pack(side=tk.LEFT)
    

    # Input message
    def send_message():
        global message_text
        message_text = input_entry.get()
        input_entry.delete(0, tk.END)
        click_chat_button(message_obj)


    # Send button
    global send_button
    send_button = tk.Button(input_frame, text="Send", command=send_message)
    send_button.pack(side=tk.LEFT)

    
    #maintk.mainloop()

def game_over(winner):
    maintk.destroy()
    gameover = tk.Toplevel()
    gameover.title('Game over')
    gameover.geometry('400x350')

    gameover_label = tk.Label(gameover, text=' --  Game Over  -- ', font=("Arial", 14))
    gameover_label.grid(row=0, column=0, sticky='nsew', padx=10, pady=(10, 0))

    scoreboard_frame = tk.Frame(gameover)
    scoreboard_frame.grid(row=1, column=0, sticky='nsew', padx=10, pady=5)  # 调整垂直填充值

    scoreboard_label = tk.Label(scoreboard_frame, text="Scoreboard", font=("Arial", 12), fg="black")
    scoreboard_label.pack(side=tk.TOP, padx=10, pady=10)

    for id, user in p_list.items():
        score_label = tk.Label(scoreboard_frame, text=f'{user}: {score[id]}', font=("Arial", 10), fg="black")
        score_label.pack(side=tk.TOP, padx=10, pady=5)

    winner_label = tk.Label(gameover, text='The winner is ' + p_list[winner] + '!', font=("Arial", 14))
    winner_label.grid(row=2, column=0, sticky='nsew', padx=10, pady=(10, 10))


    gameover.grid_rowconfigure(0, weight=1)
    gameover.grid_rowconfigure(3, weight=1)
    gameover.grid_columnconfigure(0, weight=1)

if __name__ == '__main__':
    log_in()