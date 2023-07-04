import struct
import json
import time

class Message:
    def __init__(self, sock, uid=None):
        self._sock = sock
        self._uid = uid
        self._recv_buffer = b""
        self._data_bytes = 4 # max length of header = 256**4 bytes
        self._packet_size = 1024
        self._reset()
    
    def _reset(self):
        self._data_len = None
        self._data = None

    def getuid(self):
        return self._uid

    def recv(self):
        while True:
            try:
                data = self._sock.recv(self._packet_size)

                #client closed
                if not data:
                    None
                
                self._recv_buffer += data
                while len(self._recv_buffer) < self._data_bytes:
                    data = self._sock.recv(self._packet_size)
                    self._recv_buffer += data

                self._data_len = struct.unpack(">L", self._recv_buffer[:self._data_bytes])[0]
                self._recv_buffer = self._recv_buffer[self._data_bytes:]

                while len(self._recv_buffer) < self._data_len:
                    self._recv_buffer += self._sock.recv(self._packet_size)
                
                self._data = json.loads(self._recv_buffer[:self._data_len])
                self._recv_buffer = self._recv_buffer[self._data_len:]

                result = self._data
                self._reset()
                return result
                

            except BlockingIOError:
                print("Blocking error occurs.")
            
    def send(self, data):
        try:
            data = json.dumps(data).encode()
            self._sock.sendall(struct.pack(">L", len(data)) + data)

        except BlockingIOError:
            print("Blocking error occurs.")

    def close(self):
        try:
            self._sock.close()
        except OSError as e:
            print(f"Error: socket.close() exception.")
        finally:
            self._sock = None
        