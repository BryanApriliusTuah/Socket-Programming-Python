import tkinter as tk
import os
import errno
import socket
import struct
import pickle
import pyaudio
import datetime
import time
import threading
import customtkinter as ctk

from io import BytesIO
from tkinter import messagebox
from tkinter import filedialog
from PIL import Image, ImageTk

# Audio settings
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100

# Initialize PyAudio object
audio = pyaudio.PyAudio()

# Create streams for audio input and output
stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
output_stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE, output=True, frames_per_buffer=CHUNK)

stop_receive_audio_event = threading.Event()
stop_send_audio_event = threading.Event()

class App(ctk.CTk):
    def __init__(self):
        """
        Initialize the Tkinter App.

        This includes setting the title, geometry, and whether the window is resizable.
        It also initializes the Login class and packs it into the window.
        """
        super().__init__()

        self.title("Dialog Chat")
        self.geometry("800x500")
        self.resizable(False, False)

        self.login_screen = Login(self)
        self.login_screen.pack(expand=True, fill="both")

        self.room_chat_screen = None
        # self.room_chat_screen = RoomChat(self, "localhost", "User A", False, socket.socket(socket.AF_INET, socket.SOCK_STREAM)).pack(expand=True, fill="both")

        self.mainloop()

    def show_room_chat(self, ip_address: str, username: str, client_connected: bool, client_socket: socket, user_id, image_path) -> None:
        """Transition from the login screen to the chat room screen."""
        if not client_connected:  # Only connect if the socket is not yet connected
            try:
                client_socket.connect((ip_address, 12346))  # Ensure socket is connected
            except socket.error as e:
                messagebox.showerror("Error", f"Cannot connect to server: {str(e)}")
                return

        if not ip_address or not username:
            messagebox.showerror("Error", "Please fill in all fields.")
            return

        if not self.room_chat_screen:
            self.login_screen.pack_forget()
            self.room_chat_screen = RoomChat(self, ip_address, username, client_connected, client_socket, user_id, image_path)
            self.room_chat_screen.pack(expand=True, fill="both")
        else:
            messagebox.showerror("Error", "RoomChat instance is already initialized. Please show the login screen first.")

    def show_login(self):
        """Show the login screen by hiding the chat room screen."""
        if self.room_chat_screen:
            self.room_chat_screen.pack_forget()
            self.login_screen.pack(expand=True, fill="both")
        else:
            messagebox.showerror("Error", "RoomChat instance is not initialized.")

class Login(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.master = master

        self.frame1 = ctk.CTkFrame(self)
        self.frame1.pack(expand=True, fill="both", side="left")

        self.frame2 = ctk.CTkFrame(self, corner_radius=0)
        self.frame2.pack(expand=True, fill="both", side="right")

        self.image_label = ctk.CTkLabel(self.frame1, text="", image=self.get_default_image(), compound="bottom", font=("Comic Sans", 20, "bold"))
        self.image_label.pack(expand=True, fill="both")

        self.ip_label = ctk.CTkLabel(self.frame2, text="I P  A D D R E S S", font=("Comic Sans", 13, "bold"))
        self.ip_label.place(x=50, y=150)

        self.ip_entry = ctk.CTkEntry(self.frame2, placeholder_text_color="gray", width=150, height=30)
        self.ip_entry.place(x=50, y=175)
        self.ip_entry.bind("<Return>", lambda event: self.username_entry.focus_set())

        self.username_label = ctk.CTkLabel(self.frame2, text="U S E R N A M E", font=("Comic Sans", 13, "bold"))
        self.username_label.place(x=50, y=225)

        self.username_entry = ctk.CTkEntry(self.frame2, width=150, height=30)
        self.username_entry.place(x=50, y=250)
        self.username_entry.bind("<Return>", lambda event: self.upload_image())

        self.upload_button = ctk.CTkButton(self.frame2, text="Upload Image", width=150, height=30, command=self.upload_image)
        self.upload_button.place(x=50, y=300)

        self.login_button = ctk.CTkButton(self.frame2, text="L O G I N", command=self.process, width=150, height=30)
        self.login_button.place(x=50, y=350)

        self.master.after(100, self.ip_entry.focus_set)

    def get_default_image(self):
        """Returns a default image for the login screen."""
        return ctk.CTkImage(Image.open("Icon/login.png"), size=(150, 150))

    def upload_image(self) -> None:
        """Opens a file dialog to select an image and displays it in the UI."""
        self.image_path = filedialog.askopenfilename()
        image_name = os.path.basename(self.image_path)
        self.image_extension = image_name[image_name.rfind('.')+1:]

        try:
            image = Image.open(self.image_path)
            image = ctk.CTkImage(image, size=(150, 150))
            self.image_label.configure(image=image)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def process(self):
        """Handles the login process when the user clicks the login button."""
        ip_address = self.ip_entry.get().strip()
        username = self.username_entry.get().strip()
        if not username:
            messagebox.showinfo("Error", "Please fill in all fields.")
            return

        try:

            # -------------------------------------------------------------------------------------------------------------------------

            # Connect to server
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((ip_address, 12346)) # Connect to the text server

            # -------------------------------------------------------------------------------------------------------------------------

            # Send username to server
            username_length = len(username)
            username_length_bytes = struct.pack('i', username_length)
            client_socket.send(username_length_bytes)
            client_socket.send(username.encode('utf-8'))

            # -------------------------------------------------------------------------------------------------------------------------

            if not self.image_path:
                self.image_path = "Icon/login.png"
            with open(self.image_path, 'rb') as image_file:
                image_data = image_file.read()

            image_length = len(image_data)
            image_length_bytes = struct.pack('i', image_length)
            
            # Send image bytes length
            client_socket.send(image_length_bytes)

            # -------------------------------------------------------------------------------------------------------------------------

            # Send image extension
            if client_socket.recv(1024) == b'received':
                image_extension_length = struct.pack('i', len(self.image_extension))
                client_socket.send(image_extension_length)
                client_socket.send(str(self.image_extension).strip().encode())

            # -------------------------------------------------------------------------------------------------------------------------

            client_socket.send(image_data)

            # -------------------------------------------------------------------------------------------------------------------------

            # Receive client's data dictionary from server
            clients_data_size_bytes = client_socket.recv(4) # Receive length of data bytes
            clients_data_size_int = struct.unpack('i', clients_data_size_bytes)[0]

            clients_data = b""
            while len(clients_data) < clients_data_size_int:
                clients_data += client_socket.recv(1024*64) # Receive data bytes

            clients_connected = pickle.loads(clients_data)

            # -------------------------------------------------------------------------------------------------------------------------

            # Send 'image_received' to server
            client_socket.send(b'image_received')

            # -------------------------------------------------------------------------------------------------------------------------

            # Receive user id from server
            user_id = struct.unpack('i', client_socket.recv(4))[0]
            print(f"{username} is user no. {user_id}")

            self.master.show_room_chat(ip_address, username, clients_connected, client_socket, user_id, self.image_path)
            # -------------------------------------------------------------------------------------------------------------------------

        except ConnectionRefusedError:
            messagebox.showinfo("Can't connect !", "Server is offline , try again later.")
            client_socket.close()
        except Exception as e:
            messagebox.showinfo("Error", "An unexpected error occurred.")
            print(f"An unexpected error occurred: {e}")
            client_socket.close()
            return
        
class RoomChat(ctk.CTkFrame):
    
# -----------------------------------------------Audio-----------------------------------------------
    def start_audio(self):    
        if not self.audio :
            try:
                # Start the audio threads initially
                self.audio_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.audio_socket.connect((self.ip_address, 12345))  # Connect to the audio server

                self.receive_audio_thread = threading.Thread(target=self.receive_audio, args=(self.audio_socket,))
                self.send_audio_thread = threading.Thread(target=self.send_audio, args=(self.audio_socket,))
                self.receive_audio_thread.start()
                self.send_audio_thread.start()
                print("Starting audio...")
                self.audio = True

                self.audio_button.configure(fg_color="green")
            except Exception as e:
                print(f"An unexpected error occurred on audio: {e}")
        else :
            self.audio_socket.close()
            self.audio = False
            print("Stopping audio...")
            self.audio_button.configure(fg_color=self.upload_button_default_color)

    def receive_audio(self, audio_socket):
        if audio_socket is None:
            print("Error: audio_socket is null.")
            return

        while True:
            try:
                data = audio_socket.recv(CHUNK)
                if data is None:
                    break
                output_stream.write(data)
            except OSError as e:
                if e.errno == errno.ECONNRESET:
                    print("ReceiveAudio connection closed")
                else:
                    print(f"An unexpected error occurred on audio receive: {e}")
                audio_socket.close()
                break
        print("Receive audio thread stopped.")

    def send_audio(self, audio_socket):
        if audio_socket is None:
            print("Error: audio_socket is null.")
            return

        while True:
            try:
                data = stream.read(CHUNK)
                if data is None:
                    break
                audio_socket.send(data)
            except OSError as e:
                if e.errno == errno.ECONNRESET:
                    print("Send Audio connection closed")
                else:
                    print(f"An unexpected error occurred on audio send: {e}")
                audio_socket.close()
                break
        print("Send audio thread stopped.")

# -----------------------------------------------Audio-----------------------------------------------

    def on_frame_configure(self, canvas):
        # Update the scrollregion of the canvas to encompass the frame
        canvas.configure(scrollregion=canvas.bbox("all"))

    def _on_mousewheel_vertical(self, event, master):
        # print(f"Event delta: {event.delta}")
        master.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def frame1_widget(self, master) :
        # Frame 1 Widget
        label_image = ctk.CTkImage(Image.open("Icon/Purple Happy Smile Emoji Chat Logo.png"), size=(100, 100))
        self.label = ctk.CTkLabel(master, height=100, text="", image=label_image, text_color="white", bg_color="#2C2639")
        self.label.pack(fill="both")
        
        # Canvas on Frame 1
        self.canvas = tk.Canvas(master, bg="#2C2639", highlightthickness=0, width=250) # #2C2639
        self.canvas.pack(fill="both", side="left")

        # Scrollbar for Canvas Frame 1
        self.v_scrollbar  = ctk.CTkScrollbar(master, orientation="vertical", command=self.canvas.yview, bg_color="#2C2639", width=0)
        self.v_scrollbar.pack(side="right", fill="y")

        # Frame inside Canvas Frame 1
        self.scrollbar_frame = ctk.CTkFrame(self.canvas, fg_color="transparent")
        self.canvas.create_window((0,0), window=self.scrollbar_frame, anchor="nw")

        # Bind the canvas scrolling region
        self.canvas.configure(yscrollcommand=self.v_scrollbar.set)
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.canvas.bind("<Configure>", lambda e: self.on_frame_configure(self.canvas))

    def canvas2_widget(self, master):
        # Canvas on Frame 2
        self.canvas2 = tk.Canvas(master, bg="#F0F2F4", highlightthickness=0) # bg="#F0F2F4"
        self.canvas2.pack(fill="both")

        # Scrollbar for Canvas Frame 2
        self.scrollbar2 = ctk.CTkScrollbar(self.canvas2, orientation="vertical", command=self.canvas2.yview, height=350)
        self.scrollbar2.pack(side="right", fill="y")

        # Frame inside Canvas Frame 2 
        self.scrollbar_frame2 = ctk.CTkFrame(self.canvas2, fg_color="transparent")
        self.canvas2.create_window((0,0), window=self.scrollbar_frame2, anchor="nw")

        # Bind the canvas scrolling region
        self.canvas2.configure(yscrollcommand=self.scrollbar2.set)
        self.canvas2.configure(scrollregion=self.canvas2.bbox("all"))
        self.scrollbar_frame2.bind("<Configure>", lambda e: self.on_frame_configure(self.canvas2))

    def InputFrame2_widget(self, master):
        # Entry on Frame 2
        self.frame2_entry = ctk.CTkFrame(master, corner_radius=30, fg_color="transparent")
        self.frame2_entry.place(relwidth=0.9, relheight=0.085, relx=0.5, rely=0.9, anchor="center")
        
        # Entry on self.frame2_entry
        self.entry = ctk.CTkEntry(self.frame2_entry, border_width=0, placeholder_text="Write a message...")
        self.entry.pack(expand=True, fill="both", padx=5, pady=5, side="left")
        self.entry.bind("<Return>", lambda e: self.SendText())

        # Button for sending image to other clients
        upload_button_image = ctk.CTkImage(Image.open("Icon/picture-size.png"), size=(20, 20))
        self.upload_button = ctk.CTkButton(self.frame2_entry, text="", fg_color="white", hover_color="#824DFF", image=upload_button_image, width=1, command=self.upload_image_to_clients)
        self.upload_button.pack(side="left", padx=5)

        # Default Color Upload Button
        self.upload_button_default_color = self.upload_button.cget("fg_color")

        # Button Audio
        audio_button_image = ctk.CTkImage(Image.open("Icon/voice.png"), size=(20, 20))
        self.audio_button = ctk.CTkButton(self.frame2_entry, text="", fg_color="white", hover_color="#824DFF", image=audio_button_image, width=1, command=self.start_audio)
        self.audio_button.pack(side="left", padx=5)


        # Button on self.frame2_entry
        entry_button_image = ctk.CTkImage(Image.open("Icon/send-message.png"), size=(20, 20))
        self.button = ctk.CTkButton(self.frame2_entry, fg_color="white", hover_color="#824DFF", image=entry_button_image, width=1, text="", corner_radius=10, command=self.SendText)
        self.button.pack(side="right")

    def upload_image_to_clients(self) :
        image_path = filedialog.askopenfilename()
        # -------------------------------------------------------------------------------------------------------------------------

        # Convert Image to bytes
        with open(image_path, 'rb') as image_file:
            image_data = image_file.read()

        image_length = len(image_data)
        image_length_bytes = struct.pack('i', image_length)

        data = {'from': self.username, 'message': f"{self.username} has sent an image.", 'id' : self.user_id}
        sendDataToServer = pickle.dumps(data)
        message_length = struct.pack('i', len(sendDataToServer))

        # -------------------------------------------------------------------------------------------------------------------------

        # Sending image & message to other clients about sending image
        try:
            # Sending Image Notification
            length = struct.pack('i', len('Image'))
            self.client_socket.send(length)
            self.client_socket.send("Image".encode())

            # Sending Message
            self.client_socket.send(message_length)
            self.client_socket.send(sendDataToServer)

            # Sending Image
            self.client_socket.send(image_length_bytes)
            self.client_socket.send(image_data)

        except (OSError, ConnectionResetError) as e:
            messagebox.showerror("Error", "Failed to send image.")
            print("Error Sending Image: ", str(e))

    def clients_online(self, new_added) :
        if not new_added :
            for user_id in self.client_connected :
                name = self.client_connected[user_id][0]
                image_bytes = self.client_connected[user_id][1]
                extension = self.client_connected[user_id][2]

                with open(f"{user_id}.{extension}", 'wb') as f:
                    f.write(image_bytes)
                
                self.all_user_image[user_id] = f"{user_id}.{extension}"

                # Frame 
                self.frame = ctk.CTkFrame(self.scrollbar_frame, fg_color="transparent", width=200, height=50)
                self.frame.pack(pady=(0, 0.5))

                img = ctk.CTkImage(Image.open(f"{user_id}.{extension}"), size=(40, 40))
                self.img = ctk.CTkLabel(self.frame, image=img, text="", width=40, height=40)
                self.img.pack(side="left", padx=(10, 0))

                self.name = ctk.CTkLabel(self.frame, text=name, text_color="white", font=("Arial", 15, "bold"), width=200, padx=10, anchor="w")
                self.name.pack(side="top")

                self.online = ctk.CTkLabel(self.frame, text="⚫ Online", text_color="Green", font=("Arial", 12.5, "bold"), width=200, padx=10, anchor="w")
                self.online.pack(side="top")

                self.clients_online_label[str(user_id)] = (self.frame)

                widgets = [self.img,self.name,self.online,self.frame, self.canvas]

                for widget in widgets:
                    widget.bind("<MouseWheel>", lambda e: self._on_mousewheel_vertical(e, self.canvas))
           
        else :
            user_id = new_added[0]
            name = new_added[1]
            image_bytes = new_added[2]
            extension = new_added[3]

            with open(f"{user_id}.{extension}", 'wb') as f:
                f.write(image_bytes)

            self.all_user_image[user_id] = f"{user_id}.{extension}"

            # Frame 
            self.frame = ctk.CTkFrame(self.scrollbar_frame, fg_color="transparent", width=200, height=50)
            self.frame.pack(pady=(0, 0.5))

            img = ctk.CTkImage(Image.open(f"{user_id}.{extension}"), size=(40, 40))
            self.img = ctk.CTkLabel(self.frame, image=img, text="", width=40, height=40)
            self.img.pack(side="left", padx=(10, 0))

            self.name = ctk.CTkLabel(self.frame, text=name, text_color="white", font=("Arial", 15, "bold"), width=200, padx=10, anchor="w")
            self.name.pack(side="top")

            self.online = ctk.CTkLabel(self.frame, text="⚫ Online", text_color="Green", font=("Arial", 12.5, "bold"), width=200, padx=10, anchor="w")
            self.online.pack(side="top")

            self.clients_online_label[str(user_id)] = (self.frame)

            widgets = [
                self.img,
                self.name,
                self.online,
                self.frame,
            ]

            for widget in widgets:
                widget.bind("<MouseWheel>", lambda e: self._on_mousewheel_vertical(e, self.canvas))      

    def notification(self, data) :
        if data['n_type'] == 'joined':
            try:
                message = data['message']
                username = data['name']
                image = data['image_bytes']
                client_id = data['id']
                extension = data['extension']

                self.client_connected[client_id] = (username, image)
                self.clients_online([client_id, username, image, extension])
                
                # Notification Joined
                messagebox.showinfo("Notification", message)
            except Exception as e:
                print("Error : ", str(e))

        elif data['n_type'] == 'left':
            try:
                message = data['message']
                username = data['name']
                client_id = data['id']
                del self.client_connected[client_id]

                if str(client_id) in self.clients_online_label :
                    self.after(100, self.clients_online_label[str(client_id)].destroy())
                    del self.clients_online_label[str(client_id)]
                
                # Notification Left
                messagebox.showinfo("Notification", message)        
            except Exception as e:
                print("Error : ", str(e))
    
    def ReceiveData(self) :
        while True :
            try:
                verification_length = struct.unpack('i', self.client_socket.recv(4))[0]
                verification = b''
                while len(verification) < verification_length:
                    verification += self.client_socket.recv(1)
                verification = verification.decode()

                if verification == "notification" :
                        try:
                            data_size = self.client_socket.recv(4)
                            data_size_int = struct.unpack('i', data_size)[0]
                                
                            b = b''
                            while len(b) < data_size_int:
                                b += self.client_socket.recv(1024*64)
                            data = pickle.loads(b)
                            self.notification(data)
                        except(pickle.UnpicklingError, EOFError, ConnectionResetError, ConnectionAbortedError, OSError) as e:
                            print(f"Error receiving notification : {e}")
                            break

                elif verification == "message" :
                    try:
                        message_length = struct.unpack('i', self.client_socket.recv(4))[0]
                        message = b''
                        while len(message) < message_length:
                            message += self.client_socket.recv(1024*64)
                        Message = pickle.loads(message)
                        print("From : ",Message['from'], "Message : ", Message['message'], "ID : ", Message['id'])
                        self.ReceiveTextFormat(Message)

                    except(pickle.UnpicklingError, EOFError, ConnectionResetError, ConnectionAbortedError, OSError) as e:
                        print(f"Error receiving message : {e}")
                        break

                elif verification == "image" :
                    try:
                        data_length = self.client_socket.recv(4)
                        data_length_int = struct.unpack('i', data_length)[0]
                        data = b''
                        while len(data) < data_length_int :
                            data += self.client_socket.recv(1)
                        data = pickle.loads(data)

                        image_bytes_struct = self.client_socket.recv(4)
                        image_bytes = struct.unpack('i', image_bytes_struct)[0]
                        image_data = b''
                        while len(image_data) < image_bytes:
                            image_data += self.client_socket.recv(1024*64)

                        self.ReceiveImageFormat(image_data, data)
                    except (pickle.UnpicklingError, EOFError, ConnectionResetError, ConnectionAbortedError, OSError) as e:
                        print(f"Error receiving image : {e}")
                        break
                
                self.master.update_idletasks()
            except (ConnectionResetError, ConnectionAbortedError, OSError) as e:
                messagebox.showerror("Error", "Socket connection is closed or broken.")
                print(f"Error while receiving verification : {e}")
                break
            
    def ReceiveTextFormat(self, message) :
        From = message['from']
        Message = message['message']
        FormatedMessage = ''
        user_id = message['id']

        if len(Message) > 40 :
            for i in range(0, len(Message), 40):
                FormatedMessage += Message[i:i+40] + "\n"
        else :
            FormatedMessage = Message
        
        image = self.all_user_image[user_id]
        # Chat Frame 2
        self.frame2_chat = ctk.CTkFrame(self.scrollbar_frame2, fg_color="transparent", width=545, height=75)
        self.frame2_chat.pack(fill="both",pady=10) # padx=300 for client itself.

        # Img on Chat Frame 2
        img = ctk.CTkImage(Image.open(image), size=(40, 40))
        self.img = ctk.CTkLabel(self.frame2_chat, image=img, bg_color="transparent", text="", width=40, height=40)
        self.img.pack(side="left", padx=10)

        # Name on Chat Frame 2
        self.name = ctk.CTkLabel(self.frame2_chat, text=From, text_color="black", font=("Times New Roman Sans", 12, "bold"), width=200, padx=10, anchor="w")
        self.name.pack(side="top", fill="both")

        # Create a rounded frame to act as a background for the message
        self.rounded_frame = ctk.CTkFrame(self.frame2_chat, fg_color="#824DFF",)
        self.rounded_frame.pack(side="left", padx=10)  # Add padding for spacing

        # Message Label inside the rounded frame
        self.message = ctk.CTkLabel(self.rounded_frame, text=FormatedMessage, text_color="white", font=("Times New Roman Sans", 13, "bold"), justify="left")
        self.message.pack(expand=True, fill="both", padx=10, pady=5)

        # Store Message into list
        current_time = datetime.datetime.now()
        expire_time = current_time + datetime.timedelta(seconds=10)
        self.message_expired[expire_time] = self.frame2_chat

        widgets2 = [
            self.frame2_chat,
            self.img,
            self.name,
            self.rounded_frame,
            self.message,
            self.canvas2,
            self.scrollbar_frame2
        ]

        for widget in widgets2:
            widget.bind("<MouseWheel>", lambda e: self._on_mousewheel_vertical(e, self.canvas2))

    def TextExpired(self) :
        while True:
            current_time = datetime.datetime.now()
            for expire_time in list(self.message_expired.keys()):
                if expire_time <= current_time:
                    print("Expired Bro!")
                    frame = self.message_expired[expire_time]
                    frame.destroy()
                    del self.message_expired[expire_time]
                    break
            time.sleep(1)
            self.master.update_idletasks()

    def ReceiveImageFormat(self, image_data, data) :
        if not image_data and not data:
            return

        try:
            From = data['from']
            Message = data['message']
            user_id = data['id']
            image = self.all_user_image[user_id]
            # Chat Frame 2
            self.frame2_chat = ctk.CTkFrame(self.scrollbar_frame2, fg_color="transparent", width=545, height=75)
            self.frame2_chat.pack(fill="both",pady=10) # padx=300 for client itself.

            # Img on Chat Frame 2
            img = ctk.CTkImage(Image.open(image), size=(40, 40))
            self.img = ctk.CTkLabel(self.frame2_chat, image=img, bg_color="transparent", text="", width=40, height=40)
            self.img.pack(side="left", padx=10)

            # Name on Chat Frame 2
            self.name = ctk.CTkLabel(self.frame2_chat, text=From, text_color="black", font=("Times New Roman Sans", 12, "bold"), width=200, padx=10, anchor="w")
            self.name.pack(side="top", fill="both")

            # Create a rounded frame to act as a background for the message
            self.rounded_frame = ctk.CTkFrame(self.frame2_chat, fg_color="#824DFF",)
            self.rounded_frame.pack(side="left", padx=10)  # Add padding for spacing

            # Message button inside the rounded frame
            message_button_image = ctk.CTkImage(Image.open("Icon/image.png"), size=(20, 20))
            self.message_button = ctk.CTkButton(self.rounded_frame, fg_color="#824DFF", text=Message, image=message_button_image, text_color="white", font=("Times New Roman Sans", 13, "bold"), width=1)
            self.message_button.pack(fill="both", padx=10, pady=5)

            self.message_button_list[self.count_message_button_list] = self.message_button
            self.message_button.configure(command=lambda keypair=self.count_message_button_list: self.OpenImage(image_data, keypair))
            self.count_message_button_list += 1


            widgets2 = [
                self.frame2_chat,
                self.img,
                self.name,
                self.rounded_frame,
                self.message_button,
                self.canvas2,
                self.scrollbar_frame2
            ]

            for widget in widgets2:
                widget.bind("<MouseWheel>", lambda e: self._on_mousewheel_vertical(e, self.canvas2))

            self.master.update_idletasks()
        except (pickle.UnpicklingError, EOFError, ConnectionResetError, ConnectionAbortedError, OSError) as e:
            print(f"Error in ReceiveImageFormat: {e}")

    def OpenImage(self, image_data, keypair) :

        try:
            image = Image.open(BytesIO(image_data))
            width, height = image.size
            new_height = 500 
            new_width = int(width * (new_height / height))
            print(f"Width: {width}, Height: {height}")


            self.NewTab = ctk.CTkToplevel(self.master)
            self.NewTab.title("Image")
            # self.NewTab.geometry(f"{width}x{height}")

            image = ctk.CTkImage(image, size=(new_width, new_height))
            img = ctk.CTkLabel(self.NewTab, image=image, bg_color="transparent", text="")
            img.pack()

            if keypair in self.message_button_list :
                button = self.message_button_list[keypair]
                button.configure(command=None)
                button.configure(text="Image has been opened. It can't be opened again!")
                # del self.message_button_list[keypair]
        except (ConnectionResetError, ConnectionAbortedError, OSError) as e:
            print(f"Error in ReceiveImageFormat: {e}")
        
        self.master.update_idletasks()

    def SendText(self) :
        # Receive Entry Text
        message = self.entry.get().strip()

        if message :
            data = {'from': self.username, 'message': message, 'id' : self.user_id}
            sendDataToServer = pickle.dumps(data)
            message_length = struct.pack('i', len(sendDataToServer))
            try:
                # Sending 'message' notification
                length = struct.pack('i', len('message'))
                self.client_socket.send(length)
                self.client_socket.send('message'.encode())

                # Sending Message
                self.client_socket.send(message_length)
                self.client_socket.send(sendDataToServer)
            except (ConnectionResetError, ConnectionAbortedError, OSError) as e:
                messagebox.showerror("Error", "Failed to send message")
                print(f"Error sending message : {e}")
                return False

            FormatedMessage = ''

            if len(message) > 40 :
                for i in range(0, len(message), 40):
                    FormatedMessage += message[i:i+40] + "\n"
            else :
                FormatedMessage = message

            # Chat Frame 2
            self.frame2_chat = ctk.CTkFrame(self.scrollbar_frame2, fg_color="transparent", width=545, height=75)
            self.frame2_chat.pack(fill="both",pady=10) # padx=300 for client itself.

            # Img on Chat Frame 2
            img = ctk.CTkImage(Image.open(self.image), size=(40, 40))
            self.img = ctk.CTkLabel(self.frame2_chat, image=img, bg_color="transparent", text="", width=40, height=40)
            self.img.pack(side="left", padx=10)

            # Name on Chat Frame 2
            self.name = ctk.CTkLabel(self.frame2_chat, text=self.username, text_color="green", font=("Times New Roman Sans", 12, "bold"), width=200, padx=10, anchor="w")
            self.name.pack(side="top", fill="both")

            # Create a rounded frame to act as a background for the message
            self.rounded_frame = ctk.CTkFrame(self.frame2_chat, fg_color="green")
            self.rounded_frame.pack(side="left", padx=10)  # Add padding for spacing

            # Message Label inside the rounded frame
            self.message = ctk.CTkLabel(self.rounded_frame, text=FormatedMessage, text_color="white", font=("Times New Roman Sans", 13, "bold"), justify="left")
            self.message.pack(expand=True, fill="both", padx=10, pady=5)
            self.entry.delete(0, 'end')

            # Store Message into list
            current_time = datetime.datetime.now()
            expire_time = current_time + datetime.timedelta(seconds=10)
            self.message_expired[expire_time] = self.frame2_chat

            widgets2 = [
                self.frame2_chat,
                self.img,
                self.name,
                self.rounded_frame,
                self.message,
                self.canvas2,
                self.scrollbar_frame2
            ]

            for widget in widgets2:
                widget.bind("<MouseWheel>", lambda e: self._on_mousewheel_vertical(e, self.canvas2))
    
        else:
            messagebox.showinfo("Error", "No message to send or no valid connection.")

    def __init__(self, master, ip_address, username, client_connected, client_socket, user_id, image_path):
        super().__init__(master)
        self.master = master #Reference to App Object

        # -------------------------------------------------------------------------------------------------------------------

        self.username = username
        self.ip_address = ip_address
        self.image = image_path
        self.client_connected = client_connected
        self.client_socket = client_socket
        self.user_id = user_id
        self.all_user_image = {} # {user_id : (f"{user_id}.{extension}")}
        self.clients_online_label = {} # {user_id : (self.frame)}
        self.message_button_list = {} # {user_id : (self.message_button)}
        self.message_expired = {} # {'current time' : (self.frame2_chat)}
        self.count_message_button_list = 1
        self.audio = False

        # -------------------------------------------------------------------------------------------------------------------

        # Frame Layout
        self.Frame1 = ctk.CTkFrame(self)
        self.Frame1.pack(fill="both", side="left")

        self.Frame2 = ctk.CTkFrame(self, fg_color="#F0F2F4") # fg="#F0F2F4"
        self.Frame2.pack(expand=True, fill="both", side="left")

        # Frame 1 Widget
        self.frame1_widget(self.Frame1)

        # -------------------------------------------------------------------------------------------------------------------

        # Frame 2 Widget
        self.label2 = ctk.CTkLabel(self.Frame2, height=80, bg_color="#FFFFFF", text="Jaya Maju", font=("Arial",20, "bold"))
        self.label2.pack(fill="both")
        
        # Canvas on Frame 2
        self.canvas2_widget(self.Frame2)

        # Input on Frame 2
        self.InputFrame2_widget(self.Frame2)

        # ---------------------------------------------------------------------------------------------------------------------

        # Adding Online Client
        self.clients_online([])

        # Focus on Input
        self.master.after(100, self.entry.focus_set)

        # ---------------------------------------------------------------------------------------------------------------------

        # Receiving Text
        t = threading.Thread(target=self.ReceiveData)
        t.daemon = True
        t.start()

        t2 = threading.Thread(target=self.TextExpired)
        t2.daemon = True
        t2.start()

#Run Program
App()