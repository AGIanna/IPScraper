# IPScraper
scrape.py is a multithreaded program that scrapes IP proxies, stores them in a database and updates the database if an IP times out. 

client.py and server.py let a user check the database and retrieve active IPs.

Run scrape.py to create or open existing SQLite database and begin scraping.
RUn server.py to initialize server and run client.py to send IP queries to the database.
