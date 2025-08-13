import socket

LOCAL_IP = "127.0.0.1"
LOCAL_PORT = 4400

LAPTOP_IP = "10.42.0.1"
LAPTOP_PORT = 4400

BUFFER_SIZE = 8192  # Ajust to CSI packets size

# Local loopback
recv_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
recv_sock.bind((LOCAL_IP, LOCAL_PORT))

# Socket to send
send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

print(f"Forwarding UDP from {LOCAL_IP}:{LOCAL_PORT} to {LAPTOP_IP}:{LAPTOP_PORT}...")

while True:
    data, addr = recv_sock.recvfrom(BUFFER_SIZE)
    send_sock.sendto(data, (LAPTOP_IP, LAPTOP_PORT))
