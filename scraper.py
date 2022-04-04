from bs4 import BeautifulSoup as bs 
from urllib.request import urlopen as ur
import sqlite3, threading, time, re, socket, sys
from collections import deque

# Queue for IPs from website
proxy_queue = deque([])

# Reads from database an enqueues IPs in proxy_queue in (IP_num, port, timeout tag) tuple
# Timeout tag starts being 0s because we assume all IPs come in being active
class Reader:
	def __init__(self, countries):
		self.countries = countries

	def start(self):
		while True:
			for country in self.countries:
				url = "https://www.proxynova.com/proxy-server-list/country-" + country + "/"
				site = ur(url)
				page = bs(site.read(), "html.parser")
				site.close() 
				rows = page.find_all('tr')
				# Delete filler rows
				del rows[0]
				del rows[-1]

				length = len(rows)

				for row in rows:
					cells = row.find_all("td")
					if cells[0].abbr != None:

						# Not getting the IP using only REs because IP numbers also show up inside the abbr tag
						# Extract ip address
						text = cells[0].abbr.script.text 
						ip_num = re.search(r'(\d+.){3,3}\d+',text).group()

						# Extract port
						text = cells[1].text
						port = re.search(r'\d+',text).group()

						# Extract uptime
						text = cells[4].span.string
						uptime = int(re.search(r'\d+', text).group())

						# Extract anonimity	
						anonimity = cells[6].span.string

						if uptime >= 50 and anonimity == 'Elite':
							proxy_queue.append((ip_num,port,0))
			time.sleep(30)


# Pops queue elements and writes them into the database; if there's a database element tagged for deletion,
# next queue item goes in there, else it goes to the bottom of db
class Writer(threading.Thread):
	def __init__(self, file):
		threading.Thread.__init__(self)
		self.file = file


	# THREAD 2 actvated when this function is called
	def run(self):
		print(0)
		# Creating database connections
		self.database = sqlite3.connect(self.file, check_same_thread=False)
		self.cursor = self.database.cursor()

		while True:
			try:
				# If proxy_queue is not empty, grab next element's IP, check it's not already in db, check if there are timed out IPs in the db,
				# if so, insert new IP there, else, insert at the bottom
				if proxy_queue:
					entry = proxy_queue.popleft()
					ip = (entry[0],)
					self.cursor.execute("SELECT IP FROM ProxyTable WHERE IP=?",ip)
					ip_exists = self.cursor.fetchone()
					print(ip_exists)
					if not ip_exists: #add condition
						print(ip)
						self.cursor.execute("SELECT IP FROM ProxyTable WHERE Timeout=1")
						timeout_ip = self.cursor.fetchone()
						if timeout_ip:
							print(2)
							query = "UPDATE ProxyTable SET IP=?,Port=?,Timeout=? WHERE IP=?"
							# entry = list(entry).append(timeout_ip[0])
							self.cursor.execute(query, (entry[0], entry[1], 0, timeout_ip[0]))
						else:
							print(3)
							print(entry)
							query = "INSERT INTO ProxyTable (IP, Port, Timeout) VALUES (?,?,?)"
							self.cursor.execute(query,entry)
						self.database.commit()

				time.sleep(10)
			# Catches database-locked exceptions
			except sqlite3.OperationalError:
				continue

	def terminate(self):
		self.database.commit()
		self.cursor.close()
		self.database.close()


# Class for checking if db IPs are timing out, if so, TIMEOUT field is updated to 1
class Checker(threading.Thread):
	def __init__(self,file):
		threading.Thread.__init__(self)
		self.file = file
		# Creating socket for connecting to the IPs
		self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.client_socket.settimeout(10)

	# Method that connects to an ip address and returns 1 if it times out
	# Returns 0 if the connection succeeds
	def connect(self, ip_address, port):
		return self.client_socket.connect_ex((ip_address,port))

	# THREAD 2 actvated when this function is called
	def run(self):
		self.database = sqlite3.connect(self.file,check_same_thread=False)
		self.cursor = self.database.cursor()
		while True:
			try:
				# Get number of rows in db
				self.cursor.execute("SELECT Count(*) FROM ProxyTable")
				size = self.cursor.fetchone()[0]
				if size:
					# Iterate through all db entries establishing connections
					for i in range(1,size):
						query = "SELECT IP,Port FROM ProxyTable WHERE rowid=?"
						self.cursor.execute(query, (i,))
						(ip, port) = self.cursor.fetchone()
						# If connect method returns nonzero value it means it didnt succeed, set timeout to 1
						if self.connect(ip, port): 
							print(ip + " timeout")
							query = "UPDATE ProxyTable SET Timeout=1 WHERE rowid=?"
							self.cursor.execute(query, (i,))

				time.sleep(10)

			except sqlite3.OperationalError:
				continue

	def terminate(self):
		self.client_socket.close()
		self.database.commit()
		self.cursor.close()
		self.database.close()


if __name__ == '__main__':
	
	try:
		countries = ["ru","cn"]
		database = "proxies.db"

		# Connect to the database just to create a table if there isn't one already
		connection = sqlite3.connect(database)
		cursor = connection.cursor()
		cursor.execute("CREATE TABLE IF NOT EXISTS ProxyTable (IP TEXT, Port INTEGER, Timeout INTEGER)")
		connection.commit()
		cursor.close()
		connection.close()

		# Start first thread
		DB_writer = Writer(database)
		DB_writer.start()

		# Start second thread
		DB_checker = Checker(database)
		DB_checker.start()

		data_reader = Reader(countries)
		data_reader.start()

	# Catches CTRL-C to end program
	except KeyboardInterrupt:
		print("Terminating...")
		DB_writer.terminate()
		DB_writer.join()
		DB_checker.terminate()
		DB_checker.join()
		sys.exit(0)


