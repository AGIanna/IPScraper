from socket import *
import sqlite3, re

# Function that connects to the database and returns all the IPs
def get_ip_from_db():
	database = sqlite3.connect("proxies.db")
	cursor = database.cursor()
	cursor.execute("SELECT IP FROM ProxyTable")
	return cursor.fetchall()

# Dict that stores client information in (port:assigned ip from database) pairs
client_info = {}
# Create socket and bind to a port
serverPort = 12000
serverSocket = socket(AF_INET, SOCK_DGRAM)
serverSocket.bind(('', serverPort))
print("Server ready")

while True:
	# recvfrom method returns a message (command) and tuple (addr) containing ip and port where message came from
	command, addr = serverSocket.recvfrom(2048)
	# Get the port only
	port = addr[1]
	# Add new client if its port is not already in client dict
	if port not in client_info.keys():
		client_info[port] = ""

	# Decode message
	command = command.decode()

	# If client wants to get an ip for the first time or change it, call function that gets
	# all IPs from the database, and choose one that is not already in use to assign it to 
	# the client
	if command == 's': 
		ip_list = get_ip_from_db() 
		active_ips = client_info.values() 
		for ip in ip_list: 
			if ip not in active_ips:
				client_info[port] = ip[0]
				break
		# Handle case where all IPs are currently in use
		if client_info[port] == "":
			message = "No proxies available"
		else: 
			message = "Server: You've been assigned " + client_info[port]

	# Display all active clients with number and IP
	elif command == 'd':
		ind = 1
		message = ""
		active_clients = client_info.values()
		# Loop through active clients and concat to message in 1. 111.111.111.111 format
		for count, ip in enumerate(list(active_clients), 1):
			message += "%s. %s \n" % (count, ip)

	# Last choice is for when the client wants to send a message to another client
	else:
		# Extract numbers from message
		number = re.match(r'\d+',command)
		# If the string does have numbers
		if number != None:
			# Find the 
			ip_index = int(number.group())
			ports_list = list(client_info.keys())
			if ip_index-1 < len(ports_list):
				key = ports_list[ip_index-1]
				# Extract text from the command, did it this way because of RE complications
				index = command.find(str(ip_index)[-1])
				text = command[index+1:]
				message = "From [%s] %s: %s" % (ip_index, client_info[key], text)
				# ISSUE: handling clients that disconnect right when another client is about to send a message
				# modify addr so that this message goes to the receiving client
				addr = ("127.0.0.1", int(key))

		# Otherwise invalid input
		else:
			message = "Invalid input, try again."

		# Send appropriate message to appropriate client
	serverSocket.sendto(message.encode(), addr)