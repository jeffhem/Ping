from socket import *
import os
import sys
import struct
import time
import select
import binascii
import signal

ICMP_ECHO_REQUEST = 8
rttList = []
packetSent = 0.0
packetRecv = 0.0
location = ''

# server IPs on different continents
sAmerica = "52.94.7.70"
nAmerica = '52.119.233.18'
europe = '52.94.5.150'
asia = '52.94.8.34'

# print summaries after termination
def signal_handler(sig, frame):
	packetAvg = "{0:.1%}".format((packetSent - packetRecv) / packetSent)
	rttAvg = len(rttList) > 0 and sum(rttList)/len(rttList)
	print("")
	print('--- %s ping statistics ---' % location)
	print("%s packets transmitted, %s packets received, %s packet loss" % (packetSent, packetRecv, packetAvg))
	if len(rttList) > 0 : print("round-trip min/max/avg = %s/%s/%s ms" % (min(rttList), max(rttList), rttAvg))
	sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def checksum(string):
	csum = 0
	countTo = (len(string) // 2) * 2
	count = 0
	while count < countTo:
		thisVal = ord(string[count+1]) * 256 + ord(string[count])
		csum = csum + thisVal
		csum = csum & 0xffffffff
		count = count + 2

	if countTo < len(string):
		csum = csum + ord(string[len(string) - 1])
		csum = csum & 0xffffffff

	csum = (csum >> 16) + (csum & 0xffff)
	csum = csum + (csum >> 16)
	answer = ~csum
	answer = answer & 0xffff
	answer = answer >> 8 | (answer << 8 & 0xff00)
	return answer

def receiveOnePing(mySocket, ID, timeout, destAddr):
	timeLeft = timeout

	while 1:
		startedSelect = time.time()
		whatReady = select.select([mySocket], [], [], timeLeft)
		howLongInSelect = (time.time() - startedSelect)
		if whatReady[0] == []: # Timeout
			return "Request timed out."

		timeReceived = time.time()
		recPacket, addr = mySocket.recvfrom(1024)
		#Fill in start
		icmp = recPacket[20:28]
		resType, code, myChecksum, Id, sequence = struct.unpack("bbHHh", icmp)
		# print("Type: %s, Code: %s, Checksum: %s, Id: %s, Sequence: %s" % (resType, code, checksum, ID, sequence))
		if Id == ID:
			if resType == 3 and code >= 0 and code < 16:
				return "Destination Unreachable with code: %s" % code

			lastIndexOfd = 28 + struct.calcsize('d');
			timeSent = struct.unpack('d', recPacket[28:lastIndexOfd])[0];
			rtt = float("{:.4f}".format((timeReceived - timeSent) * 1000))
			rttList.append(rtt)
			global packetRecv
			packetRecv += 1
			return "Pong %s: %s ms" % (addr[0], rtt)
		#Fill in end

		timeLeft = timeLeft - howLongInSelect
		print(timeLeft)
		if timeLeft <= 0:
			return "Request timed out."

def sendOnePing(mySocket, destAddr, ID):
	# Header is type (8), code (8), checksum (16), id (16), sequence (16)

	myChecksum = 0
	# Make a dummy header with a 0 checksum
	# struct -- Interpret strings as packed binary data
	header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, myChecksum, ID, 1)
	data = struct.pack("d", time.time())
	# Calculate the checksum on the data and the dummy header.
	myChecksum = checksum(str(header + data))

	# Get the right checksum, and put in the header
	if sys.platform == 'darwin':
		# Convert 16-bit integers from host to network  byte order
		myChecksum = htons(myChecksum) & 0xffff
	else:
		myChecksum = htons(myChecksum)

	header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, myChecksum, ID, 1)
	packet = header + data

	global packetSent
	packetSent += 1
	mySocket.sendto(packet, (destAddr, 1)) # AF_INET address must be tuple, not str
	# Both LISTS and TUPLES consist of a number of objects
	# which can be referenced by their position number within the object.

def doOnePing(destAddr, timeout):
	icmp = getprotobyname("icmp")
	# SOCK_RAW is a powerful socket type. For more details:
#    http://sock-raw.org/papers/sock_raw

	mySocket = socket(AF_INET, SOCK_RAW, icmp)

	myID = os.getpid() & 0xFFFF  # Return the current process i
	sendOnePing(mySocket, destAddr, myID)
	delay = receiveOnePing(mySocket, myID, timeout, destAddr)

	mySocket.close()
	return delay

def ping(host, locate='', timeout=1):
	# timeout=1 means: If one second goes by without a reply from the server,
	# the client assumes that either the client's ping or the server's pong is lost
	dest = gethostbyname(host)
	global location
	location = locate or dest
	print("Pinging " + location + " using Python:")
	# Send ping requests to a server separated by approximately one second

	while 1 :
		delay = doOnePing(dest, timeout)
		print(delay)
		time.sleep(timeout)# one second
	print("")
	return delay

# ping four IPs in 4 different continents
ping(sAmerica, 'South America')
#ping(nAmerica, 'North America')
#ping(europe, 'Europe')
#ping(asia, 'Asia')

