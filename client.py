from socket import *
import threading, sys

# Create a separate thread to handle terminal input
class UInput(threading.Thread):
	def __init__(self, sock):
		threading.Thread.__init__(self)
		self.sock = sock

	def run(self):
		serverName = '127.0.0.1'
		serverPort = 12000
		while True:
			message = input()
			self.sock.sendto(message.encode(), (serverName, serverPort))
			#"c" is for closing program, and needs to be sent to server as well so it can take this client off of the list
			if message == "c":
				sys.exit()


# Create new socket
clientSocket = socket(AF_INET, SOCK_DGRAM)

# Create input thread
user_input = UInput(clientSocket)
print("s - get (new) proxy\nd - display active clients\nc - close\nn + message - send message to client n")
# Start input thread
user_input.start()

while True:
	# Get server message
	reply, serverAddress = clientSocket.recvfrom(2048)
	print(reply.decode())

