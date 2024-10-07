import socket
import struct
import pickle
import threading

# Lists to keep track of connected clients for both audio and text
audio_clients = []

count = 1

# Dictionary to keep track of connected clients || Access the data using socket
clients_connected = {}

# Dictionary to send client data || Access the data using user_id
client_data = {}

def broadcast_text(message, current_client):
    """Function to broadcast a text message to all clients except the sender"""
    for client in list(clients_connected.keys()):
        if client != current_client:
            try:
                # Sending 'message' notification
                length = struct.pack('i', len("message"))
                client.send(length)
                client.send("message".encode())

                # Sending Message
                message_length = struct.pack('i', len(message))
                client.send(message_length)
                client.send(message)
            except (ConnectionResetError, ConnectionAbortedError, OSError):
                print(f"Error sending message to {clients_connected[client][0]}")
                del clients_connected[client]
                client.close()
                break

def broadcast_text_image(image_bytes, image_data, data_length, data, current_client):
    """Function to broadcast a text message to all clients except the sender"""
    for client in clients_connected:
        if client != current_client:
            # Sending Image Notification
            length = struct.pack('i', len("image"))
            client.send(length)
            client.send("image".encode())

            # Sending Message
            client.send(data_length)
            client.send(data)

            # Sending Image
            client.send(image_bytes)
            client.send(image_data)
            print("Sent image to client", clients_connected[client][0])
            
def handle_text_client(text_socket):
    """Function to handle communication with a single text client"""
    while True:
            try:
                verification_length = struct.unpack('i', text_socket.recv(4))[0]
                verification = b""
                while len(verification) < verification_length:
                    verification += text_socket.recv(1)
                verification = verification.decode()

                if verification == "message" :
                    try:
                        message_length_bytes = text_socket.recv(4)
                        message_length = struct.unpack('i', message_length_bytes)[0]
                        message = b''
                        while len(message) < message_length:
                            message += text_socket.recv(1024*64)
                        messagef = pickle.loads(message)
                        print("From : ",messagef['from'], "Message : ", messagef['message'], "ID : ", messagef['id'])
                        broadcast_text(message, text_socket)
                    except (pickle.UnpicklingError, EOFError, ConnectionResetError, ConnectionAbortedError, OSError) as e:
                        print(f"Error receiving message line 58 : {e}")
                        break
            
                elif verification == "Image" :
                    # Receive image bytes
                    try:
                        # Receive Message
                        data_length = text_socket.recv(4)
                        data_length_int = struct.unpack('i', data_length)[0]
                        data = b''
                        while len(data) < data_length_int:
                            data += text_socket.recv(1)

                        image_size_bytes = text_socket.recv(4)
                        image_size_int = struct.unpack('i', image_size_bytes)[0]

                        # Receive image data
                        image_data = b''
                        while len(image_data) < image_size_int:
                            image_data += text_socket.recv(1024*64)

                        broadcast_text_image(image_size_bytes, image_data, data_length, data, text_socket)
                    except (struct.error, pickle.UnpicklingError, EOFError, ConnectionResetError, ConnectionAbortedError, OSError) as e:
                        print(f"Error receiving image size line 76 : {e}")
                        break

            except (ConnectionResetError, ConnectionAbortedError, EOFError, struct.error, OSError, pickle.UnpicklingError) as e:
                print(f"{clients_connected.get(text_socket, [None])[0]} disconnected with error : \n{e}")
                for client in clients_connected:
                    if client != text_socket:
                        length = struct.pack('i', len("notification"))
                        client.send(length)
                        client.send('notification'.encode())
                        data = pickle.dumps({
                            'message': f"{clients_connected[text_socket][0]} left the chat",
                            'name' : clients_connected[text_socket][0],
                            'id': clients_connected[text_socket][1], 
                            'n_type': 'left'
                        })

                        data_length_bytes = struct.pack('i', len(data))
                        client.send(data_length_bytes)
                        client.send(data)

                if text_socket in clients_connected:
                    del client_data[clients_connected[text_socket][1]]
                    del clients_connected[text_socket]
                    text_socket.close()
                print("Connection for that client has closed")
                break
        
def handle_audio_client(audio_socket):
    """Function to handle communication with a single audio client"""
    while True:
        try:
            audio_data = audio_socket.recv(1024)
            for client in audio_clients:
                if client != audio_socket:
                    client.send(audio_data)
        except:
            if audio_socket in audio_clients:
                audio_clients.remove(audio_socket)
            audio_socket.close()
            break

def start_audio_server():
    """Function to start the audio server"""
    audio_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    audio_server.bind(('localhost', 12345))  # Port for audio communication
    audio_server.listen()

    print("Audio server is listening for connections...")

    while True:
        audio_socket, audio_address = audio_server.accept()
        print(f"Audio connected with {audio_address}")
        audio_clients.append(audio_socket)
        audio_thread = threading.Thread(target=handle_audio_client, args=(audio_socket,))
        audio_thread.start()

def start_text_server():
    """Function to start the text server"""
    text_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    text_server.bind(('localhost', 12346))  # Port for text communication
    text_server.listen()
    print("Text server is listening for connections...")

    # Get the default receive buffer size (SO_RCVBUF)
    default_recv_buf_size = text_server.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF)

    # Get the default send buffer size (SO_SNDBUF)
    default_send_buf_size = text_server.getsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF)

    print(f"Default receive buffer size: {default_recv_buf_size} bytes")
    print(f"Default send buffer size: {default_send_buf_size} bytes")

    global count
    while True:
        # ---------------------------------------------------------------------------------------------------------------------------------------

        # Accept connections
        client_socket, client_address = text_server.accept()
        print(f"Connections from {client_address} has been established")

        # ---------------------------------------------------------------------------------------------------------------------------------------

        # Receive client name
        try:
            client_name_bytes = client_socket.recv(4) # Receive username_length_bytes
            username_length = struct.unpack('i', client_name_bytes)[0]
            username_bytes = client_socket.recv(username_length)
            client_name = username_bytes.decode('utf-8')
        except (OSError, ConnectionAbortedError, Exception) as e:
            print("Error receiving client name:", e)

        print(f"{client_address} identified itself as {client_name}")
        
        # ---------------------------------------------------------------------------------------------------------------------------------------
        
        # Add client to dictionary
        clients_connected[client_socket] = (client_name, count)

        # ---------------------------------------------------------------------------------------------------------------------------------------

        # Receive image bytes length
        image_size_bytes = client_socket.recv(4)
        image_size_int = struct.unpack('i', image_size_bytes)[0]

        # -----------------------------------------------------------------------------------------------------------------------

        # Receive image extension
        client_socket.send(b'received')
        image_extension_bytes = client_socket.recv(4)
        image_extension_int = struct.unpack('i', image_extension_bytes)[0]
        image_extension = b""
        while len(image_extension) < image_extension_int:
            image_extension += client_socket.recv(1024*64)
        image_extension = image_extension.decode()

        # -------------------------------------------------------------------------------------------------------------------------

        # Receive image bytes
        image_data = b''
        while len(image_data) < image_size_int:
            try:
                image_data += client_socket.recv(1024*64)
            except (ConnectionResetError, ConnectionAbortedError, OSError):
                print(f"{client_address} disconnected")
                break

        # -------------------------------------------------------------------------------------------------------------------------

        # Store new client's name and image in dictionary
        client_data[count] = (client_name, image_data, image_extension)

        # -------------------------------------------------------------------------------------------------------------------------

        # Send client's data dictionary to the new client
        clients_data_bytes = pickle.dumps(client_data)
        clients_data_length = struct.pack('i', len(clients_data_bytes))
        client_socket.send(clients_data_length)  # Send length of data bytes
        client_socket.send(clients_data_bytes)  # Send data bytes
            
        # -------------------------------------------------------------------------------------------------------------------------

        # Receive "image_received" message from the new client
        if client_socket.recv(1024) == b"image_received" :
            print("Image received when connecting")

            # Send user_id to new client
            client_socket.send(struct.pack('i', count))

            # Send notification to new client
            for client in clients_connected:
                if client != client_socket:
                    length = struct.pack('i', len("notification"))
                    client.send(length)
                    client.send('notification'.encode())
                    data = pickle.dumps({'message': f"{clients_connected[client_socket][0]} joined the chat", 'extension': image_extension,
                        'image_bytes': image_data, 'name': clients_connected[client_socket][0], 'n_type': 'joined', 'id': count})
                    data_length_bytes = struct.pack('i', len(data))
                    client.send(data_length_bytes)
                    client.send(data)

        # -------------------------------------------------------------------------------------------------------------------------

        count += 1
        text_thread = threading.Thread(target=handle_text_client, args=(client_socket,))
        text_thread.start()

# Start both servers
audio_server_thread = threading.Thread(target=start_audio_server)
text_server_thread = threading.Thread(target=start_text_server)

audio_server_thread.start()
text_server_thread.start()