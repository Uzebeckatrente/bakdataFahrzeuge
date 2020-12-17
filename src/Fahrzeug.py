from .basicFuncs import *;
import threading



class Fahrzeug():
	'''
	Class representing vehicles in this simulation
	'''
	def __init__(self, id,initialX,initialY,secondsToPerformMove,secondsForRecharge,movesUntilRecharge, visual,logsRoot, tileSize = -1):
		'''

		:param id: unique car id
		:param initialX: initial x coordinate
		:param initialY: initial x coordinate
		:param secondsToPerformMove: how long Fahrzeug objects should sleep before informing the Streams App that they have moved
		This simulates a vehicle moving from place to place, which takes time
		:param secondsForRecharge: how long Fahrzeug objects should sleep when they have low battery and have reached a charging port
		This simulates a vehicle charging, which takes time
		:param movesUntilRecharge: how many moves a car can make before it signals to the Streams App that it has low battery
		:param visual: whether the app is in visual mode
		:param logsRoot: root of the log file which this car will create for itself
		:param tileSize: size of squares so the car knows how to draw itself
		'''

		#assign passed values as instance variables in Fahrzeug object
		self.x = initialX;
		self.y = initialY;
		self.visual = visual;
		self.id = str(id);
		self.secondsToPerformMove = secondsToPerformMove;
		self.movesUntilRecharge = movesUntilRecharge
		self.secondsForRecharge = secondsForRecharge;
		self.logsRoot = logsRoot;



		#initialize Kafka Consumers of nextPositions and newTasks topics
		self.nextPositionConsumer = KafkaConsumer('nextPositions')
		self.newTaskConsumer = KafkaConsumer('newTasks')
		self.producer = KafkaProducer(bootstrap_servers='localhost:9092')

		# Initialize log file for this car according to its unique id
		self.logFile = open(logsRoot+"/"+self.id+".txt","w")
		self.logFile.write("Car with id " + str(id) + " intialized\n");

		#it is not assigned to a task upon initialization
		self.currentTask = "-1";

		#initialize other parameters of Fahrzeug object
		self.charging = False; #not charging on initialization
		self.stepsForCurrentTask = 0; #how many steps car needs to perform its current task
		self.battery = self.movesUntilRecharge; #battery starts fully charged


		#initialize values and load images, only relevant to visual-mode
		#The car is normally yellow; however, when it has low battery it turns red with green tinted windows
		#When it is charging, it stays red with green tinted windows, but becomes tiny
		if visual:
			self.carNormal = pg.image.load("./src/img/carNormal.png")
			self.carNormal = pg.transform.scale(self.carNormal, (int(tileSize * 0.95), int(tileSize * 0.95)))

			self.carLowBattery = pg.image.load("./src/img/carLowBattery.png")
			self.carLowBattery = pg.transform.scale(self.carLowBattery, (int(tileSize * 0.95), int(tileSize * 0.95)))

			self.carCharging = pg.image.load("./src/img/carLowBattery.png")
			self.carCharging = pg.transform.scale(self.carLowBattery, (int(tileSize * 0.4), int(tileSize * 0.4)))

		#car sleeps for at least 0.001 seconds upon move performance to avoid potential synchronicity bugs
		if secondsToPerformMove < 0.001:
			self.secondsToPerformMove = 0.001


	def initThreads(self):
		'''
		Initializes threads used by kafka consumers.
		:return:
		'''

		# thread for consuming new tasks from streams app
		self.newTaskThread = threading.Thread(target=self.listenForNewTask)
		self.newTaskThread.start()

		# thread for consuming position updates from streams app
		self.listeningThread = threading.Thread(target=self.listenForNextPosition)
		self.listeningThread.start()


	def finish(self):
		'''
		When the car has finished its task and there are none left to do, it logs this and its main thread ends
		:return:
		'''

		print("Thread for Car",self.id," is finished; last task was",self.currentTask)
		if self.currentTask != "-1":
			self.logFile.write("Car " + self.id + " finished task " + self.currentTask + " in " + str(self.stepsForCurrentTask) + " steps\n\n\n")
		self.logFile.write("Car " + self.id + " is retired\n")
		self.logFile.close()



	def listenForNextPosition(self):
		'''
		Each time a message appears in the nextPositions queue that is germane to this Fahrzeug,
		this method will be triggered
		:return:
		'''

		# this for-loop serves for the thread to consume the nextPositions topic.
		# Whenever there is a new message in this topic, a new round of the for-loop is triggered
		# When a new message is consumed that the streams app is telling a car of the next position it must go to
		# If that car is not this car, then the message is ignored
		for mes in self.nextPositionConsumer:

			# if 10 seconds pass betewen messages consumed then there has probably been an error.
			# This is a safe-guard against deadlocking
			self.nextPositionConsumer.consumer_timeout_ms=10000

			#decode message from streams app
			mesStr = mes.value.decode()
			mes = json.loads(mesStr);

			#if the car about which this message has been sent is not this car object, then the message is ignored
			if str(self.id) != mes["vehicleId"]: continue;
			#if this position is reached, then the message pertains to this car object

			#if the x and y coordinates sent from the app are -1, then the car has reached its target and there are
			#no more tasks to do. It may now stop consuming kafka topics and decease.
			if int(mes["x"]) == -1 and int(mes["y"]) == -1:
				break;


			#if it is conceivable that, because of asynchony of kafka topics, that a car
			#will receive its next move before it receives its new task, upon the completion
			# of a task. If this happens, it will sleep until the new task has been processed.
			while mes["taskId"] != self.currentTask:
				time.sleep(0.01);
				print("Wires crossed for car",self.id,"in task generation; sleeping")

			self.logFile.write("Car " + self.id + " received message: " + mesStr+" in context of task " + self.currentTask+"\n");

			#move to the position that the streams app said to move to
			self.x = int(mes["x"]);
			self.y = int(mes["y"]);

			#if "charge" is set, then it reached a charging port. It now charges
			if mes["charge"]:
				self.charging = True;#visual parameter
				self.logFile.write("Car " + self.id + " is charging\n");

				#in visual mode, charging takes time
				if self.visual:
					time.sleep(self.secondsForRecharge);
				#after charging, the battery is fully charged.
				self.battery=self.movesUntilRecharge;

			#it need not charge
			else:
				self.charging = False;#visual parameter
				time.sleep(self.secondsToPerformMove);
				self.battery += -1;
				# if self.battery <= 0:
				# 	self.sendCriticalBatteryMessage()
			self.sendCurrentPositionToApp(self.battery <= 0)
		print("Car",self.id," is done listening for new positions")

	def listenForNewTask(self):
		'''
		Each time a message appears in the newTasks topic that is germane to this Fahrzeug,
		this method will be triggered
		:return:
		'''

		# this for-loop serves for the thread to consume the newTasks topic.
		# Whenever there is a new message in this topic, a new round of the for-loop is triggered
		# When a new message is consumed that the streams app is telling a car of the next position it must go to
		# If that car is not this car, then the message is ignored
		for mes in self.newTaskConsumer:

			# if 10 seconds pass betewen messages consumed then there has probably been an error.
			# This is a safe-guard against deadlocking
			self.newTaskConsumer.consumer_timeout_ms = 10000

			#decode message from streams app
			mesStr = mes.value.decode()
			mes = json.loads(mesStr);
			if str(self.id) != mes["vehicleId"]: continue;
			if mes["startX"] == mes["startY"] == -1:
				# if the x and y coordinates sent from the app are -1, then the car has reached its target and there are
				# no more tasks to do. It may now stop consuming kafka topics and decease.
				break;

			if self.currentTask != "-1":
				self.logFile.write("Car " + self.id + " finished task " + self.currentTask + " in " + str(self.stepsForCurrentTask) + " steps\n\n\n")


			#set car-task-specific logging variables
			self.stepsForCurrentTask = 0;
			self.currentTask = mes["taskId"];

			self.logFile.write("Car " + self.id + " received new task: " + mesStr + "\n");
		print("Car",self.id,"is done listening for new tasks")





	def sendCriticalBatteryMessage(self):
		'''
		#Depricated - this functionality is now encompassed by sendCurrentPositionToApp
		If the battery of the Fahrzeug reaches 0, it will send a message into the criticalBatteryTopic,
		and will be directed towards the nearest charging port
		:return:
		'''

		criticalBatteryDict = {
			"vehicleId": self.id,
		}

		positionDictJson = json.dumps(criticalBatteryDict)
		self.logFile.write("Car " + self.id + " sent critical battery message: "+ json.dumps(positionDictJson)+"\n")
		self.producer.send('criticalBatteryTopic', str.encode(positionDictJson))  #
		self.producer.flush()

	def sendCurrentPositionToApp(self, needCharge):
		'''
		This method pushes a message into the updateAppWithCurrentPositions queue
		It indicates which car it is and where it is, as well as whether it needs a charge
		:param needCharge:
		:return:
		'''
		'''
		This method pushes a message into the updateAppWithCurrentPositions topic for the app to consume
		:return:
		'''

		positionDict = {
			"vehicleId":self.id,
			"x":str(self.x),
			"y":str(self.y),
			"timestamp":str(datetime.datetime.now()),
			"needCharge":needCharge
		}

		# kafka syntax for producing a message in a topic
		positionDictJson = json.dumps(positionDict)
		self.logFile.write("Car "+self.id+" sent current pos: "+positionDictJson+" in context of task " + self.currentTask+"\n")
		self.producer.send('updateAppWithCurrentPositions', str.encode(positionDictJson))#
		self.producer.flush()

		#each time a move is sent to the app, a step is officially taken (for logging purposes)
		self.stepsForCurrentTask += 1;



	def draw(self, screen, tileSize):
		'''
		In visual-mode, car draws itself in pygame
		The car is normally yellow; however, when it has low battery it turns red with green tinted windows
		When it is charging, it stays red with green tinted windows, but becomes tiny
		:param screen:
		:param tileSize:
		:return:
		'''
		if self.charging:
			screen.blit(self.carCharging, (self.x * tileSize, self.y * tileSize))
		elif self.battery > 0:
			screen.blit(self.carNormal, (self.x * tileSize, self.y * tileSize))
		else:
			screen.blit(self.carLowBattery, (self.x * tileSize, self.y * tileSize))