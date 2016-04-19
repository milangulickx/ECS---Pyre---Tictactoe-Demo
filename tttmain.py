import random
from pyre import Pyre
from pyre import zhelper 
from pyre import pyre_peer
import zmq 
import uuid
import logging
import sys
import json

## functions needed for the game:

#make a board
board = [0,1,2,3,4,5,6,7,8]

#function to show the board
def showboard():
	print (board[0],'|',board[1],'|',board[2])
	print ('----------')
	print (board[3],'|',board[4],'|',board[5])
	print ('----------')
	print (board[6],'|',board[7],'|',board[8])
	print ('----------')

#function to check for a combination
def check(char,spot1,spot2,spot3):
        if board[spot1]==char and board[spot2]==char and board[spot3]==char:
                return True

#function to check the board for a winning combination
def checkall(char):
        if check(char,0,1,2):
                return True
        if check(char,3,4,5):
                return True
        if check(char,6,7,8):
                return True
        if check(char,0,3,6):
                return True
        if check(char,1,4,7):
                return True
        if check(char,2,5,8):
                return True
        if check(char,0,4,8):
                return True
        if check(char,2,4,6):
                return True

## the game itself
GROUPNAME = "TicTacToe"
STOP_COMMAND = "$$quit"


def chat_task(ctx, pipe):
	print("Game started")
	print("Name: %s" %NAME)
	connected_players = 1
	network_players = 1
	leave_counter = 0

	#Set up node for the game
	n = Pyre("")
	n.set_header("header_name", NAME)

	#Join the group
	n.join(GROUPNAME)
	
	#Start broadcasting node
	n.start()

	# Set up poller
	poller = zmq.Poller()
	poller.register(pipe, zmq.POLLIN)  #Local pipe (contains commands/messages we send through terminal)
	poller.register(n.socket(), zmq.POLLIN)

	# A while loop constantly polls for new items = PULL system
	while True:

		#Wait for new message to be polled. This function blocks until there is a new message
		items = dict(poller.poll())

        	#This are messages from ourselves
		if pipe in items:
			message_pipe = pipe.recv()
			if message_pipe.decode('utf-8') == STOP_COMMAND:
				break
			#check if the message is a number
			elif message_pipe.decode('utf-8').isdigit() == True and yourturn == True:
				#variable to keep the loop going until a correct number is given
				status = True
				#check which symbol you got assigned
				if playerX == True:
					while status == True:
						number = int(message_pipe.decode('utf-8'))
						#check if the spot is free
						if board[number] != "X" and board[number] != "O":
							status = False
							yourturn = False
							print("New status board:")
							board[number] = "X"
							showboard()
							#check for a winning combination
							if checkall("X") == True:
								print("You win!")
								n.whisper(OPPONENT,str(number).encode('utf-8'))
								break
							#when there's no winning combination, it's the other player's turn
							else:
								print("Waiting for opponent's move...")
							#let your opponent know which number you chose
							n.whisper(OPPONENT,str(number).encode('utf-8'))
						else:
							print("Spot taken, try again")
							message_pipe = pipe.recv()
				else:
					while status == True:
						number = int(message_pipe.decode('utf-8'))
						if board[number] != "X" and board[number] != "O":
							status = False
							yourturn = False
							print("New status board:")
							board[number] = "O"
							showboard()
							if checkall("O") == True:
								print("You win!")
								n.whisper(OPPONENT,str(number).encode('utf-8'))
								break
							else:
								print("Waiting for opponent's move...")
							n.whisper(OPPONENT,str(number).encode('utf-8'))
						else:
							print("Spot taken, try again")
							message_pipe = pipe.recv()
			elif message_pipe.decode('utf-8').isdigit() == True and yourturn == False:
				print("It's not your turn, wait for your opponent's move")
			#if the message isn't a number, it is send as a message to your opponent
			else:
				print("Sending message to opponent: %s" %message_pipe.decode('utf-8'))
				n.whisper(OPPONENT,message_pipe)

		# Received messages from system or messages from other peers
		else:
			cmds = n.recv()
			#print(">>>>>>>RECEIVED MESSAGE: ", cmds)
			msg_type = cmds.pop(0)
			player_uuid = uuid.UUID(bytes=cmds.pop(0))
			#OPPONENT = player_uuid
			#print("player uuid: ", player_uuid)
			msg_name = cmds.pop(0)
			
			if msg_type.decode('utf-8') == "ENTER":
				headers = json.loads(cmds.pop(0).decode('utf-8'))
				network_players += 1
				if network_players == 2:
					print("--------------------------------------------------------------------------------")
					print("New player discovered in network")
					print("Name:", headers.get("header_name"))
					print("--------------------------------------------------------------------------------")
			elif msg_type.decode('utf-8') == "JOIN":
				connected_players += 1
				#check if there's stil room for a player
				if connected_players > 2:
					leave = "No free spot left"
					n.whisper(player_uuid, leave.encode('utf-8'))
				elif connected_players == 2:
					print("--------------------------------------------------------------------------------")
					print("%s joined group" %headers.get("header_name"), cmds.pop(0).decode('utf-8'))
					print("--------------------------------------------------------------------------------")
					#if there are 2 players, you know your opponent:
					OPPONENT = player_uuid
					showboard()
					#randomly choose if you want to start
					assign = random.randint(0,1)
					if assign == 1:
						player_start = True
						n.whisper(OPPONENT, "$$Istart".encode('utf-8'))
					else:
						player_start = False
						n.whisper(OPPONENT, "$$Ustart".encode('utf-8'))						
			elif msg_type.decode('utf-8') == "WHISPER":
				message_opponent = cmds.pop(0).decode('utf-8')
				if message_opponent == "No free spot left":
					leave_counter += 1
					#if you get the message that you must leave from 2 other players, you are the third player
					if leave_counter == 2:
						print(message_opponent)
						break
				#if the random generators both got a compatible result, the game can start
				elif message_opponent == "$$Istart" and player_start == False:
					playerX = False
					yourturn = False
					print("You are symbol O")
					print("You opponent may start, please wait...")
				elif message_opponent == "$$Ustart" and player_start == True:
					playerX = True
					yourturn = True
					print("You are symbol X")
					print("You may start")
					print("Where do you want to place your X?")
				#when the results are incompatible: try again
				elif message_opponent == "$$Istart" and player_start == True:
					assign = random.randint(0,1)
					if assign == 1:
						player_start = True
						n.whisper(OPPONENT, "$$Istart".encode('utf-8'))
					else:
						player_start = False
						n.whisper(OPPONENT, "$$Ustart".encode('utf-8'))
				elif message_opponent == "$$Ustart" and player_start == False:
					assign = random.randint(0,1)
					if assign == 1:
						player_start = True
						n.whisper(OPPONENT, "$$Istart".encode('utf-8'))
					else:
						player_start = False
						n.whisper(OPPONENT, "$$Ustart".encode('utf-8'))
				#if you receive a number, this is your opponent's move
				elif message_opponent.isdigit() == True:
					yourturn = True
					print("--------------------------------------------------------------------------------")
					print("Number opponent: ",message_opponent)
					print("New status board:")
					#check for a winning combination based on which player you are
					if playerX == True:
						board[int(message_opponent)] = "O"
						showboard()
						if checkall('O') == True:
							print("You loose!")
							break
						#if your opponent didn't make a winning combination, it's your turn
						else:
							print("Your turn")
							print("Where do you want to place your X?")
					else:
						board[int(message_opponent)] = "X"
						showboard()
						if checkall('X') == True:
							print("You loose!")
							break
						else:
							print("Your turn")
							print("Where do you want to place your O?")					
				#if you just received a message, print it
				else:
					print("Opponent says: ",message_opponent)


			elif msg_type.decode('utf-8') == "EXIT":
				if connected_players == 2:
					print("%s left network" %headers.get("header_name"))
					connected_players -= 1
					print("Total connected players: ", connected_players)
				leave_counter -= 1
	print("Game stopped")
	n.stop()

if __name__ == '__main__':

	# For logging
	logger = logging.getLogger("pyre")
	logger.setLevel(logging.INFO)
	logger.addHandler(logging.StreamHandler())
	logger.propagate = False

	#Create ZMQ context
	ctx = zmq.Context()

	# Ask for username
	NAME = input("Username: ")

	# Set up a background chat_task thread. We use ZeroMQ to send inter-thread messages to that thread
	input_pipe = zhelper.zthread_fork(ctx, chat_task)

	# For python 2 versions, text input of user is differently defined
	input = input
	if sys.version_info.major < 3:
		input = raw_input

	while True:
		try:
			msg = input()
			input_pipe.send(msg.encode('utf_8')) #Send the input message to the local input pipe
		except (KeyboardInterrupt, SystemExit):
			break

	print("--------------------------------------------------------------------------------")
	input_pipe.send(STOP_COMMAND.encode('utf_8'))
	print("Leaving current game")
