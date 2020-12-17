
from .Fahrzeug import *;
import threading
from .ChargingStation import *;
from .Task import *;




class RoutenSteuerung():
	'''
	Class that contains the Kafka stream app.
	The singleton instance of this class communicates with instances of the Fahrzeug class via Kafka topics.
	'''
	def __init__(self, numCars: int, numTasks: int,numChargingStations: int,movesUntilRecharge: int, secondsToPerformMove: float,secondsForCharge: float,boardLength: int, visual: bool, tileSize = -1, logsRoute = "./logs"):
		'''

		Initialization of the streaming app class called RoutenSteuerung
		:param numCars: Number of cars in simulation
		:param numTasks: Number of tasks needed to be accomplished
		:param numChargingStations: Number of charging stations positioned on warehouse floor
		:param movesUntilRecharge: Number of moves a car can make before it must seek a recharge
		:param secondsToPerformMove: Number of seconds that it takes a car to perform a move (only relevant in visual-mode)
		:param secondsForCharge: Number of seconds that it takes a car to charge
		:param boardLength: Number of squares on side of board (board then has area boardLength x boardLength)
		:param visual: whether visual-mode will be enabled
		:param tileSize: how large each square should be (only relevant in visual-mode)
		:param logsRoute: Root for logs for this run
		'''

		#assign passed values as instance variables in RoutenSteurung object
		self.numCars = numCars;
		self.numTasks = numTasks;
		self.numRemainingTasks = numTasks;
		self.boardLength = boardLength;
		self.secondsToPerformMove = secondsToPerformMove;
		self.visual = visual;
		self.tileSize = tileSize;
		self.numChargingStations = numChargingStations;
		self.movesUntilRecharge = movesUntilRecharge;
		self.secondsForCharge = secondsForCharge;
		self.logsRoot = logsRoute;


		#initialize other parameters of RoutenSteuerung object
		self.fzIdToTask = {}
		self.accomplishedTasks = 0; #no tasks have been accomplished upon initialazation
		self.finished = False #visual-mode parameter



		#initialize kafka consumer and producer
		try:
			self.positionUpdateConsumer = KafkaConsumer('updateAppWithCurrentPositions')
			#self.lowBatteryConsumer = KafkaConsumer('criticalBatteryTopic') #depricated
			self.producer = KafkaProducer(bootstrap_servers='localhost:9092')
		except:
			raise RuntimeError("Make sure you have zookeeper and kafka running in the background!")



		#Initialize main log file
		if not os.path.exists(logsRoute):
			os.mkdir(logsRoute);
		self.mainLogFile = open(self.logsRoot + "/" + "main.txt", "w");
		self.mainLogFile.write("=" * 15 + "\n" + "Initialized simulation with " + str(numCars) + " cars, " + str(numTasks) + " tasks, " + str(numChargingStations) + " charging stations, with board of lenth " + str(boardLength) + "\n" + "=" * 15 + "\n")


		self.generateChargingStations();


	def initThreads(self):
		'''
		Initializes threads used by kafka consumers.
		:return:
		'''
		# thread for consuming position updates from cars
		self.listeningThread = threading.Thread(target=self.listenForPositionUpdates)
		self.listeningThread.start()

		# # thread for consuming low battery updates from cars - depricated
		# self.lowBatteryListeningThread = threading.Thread(target=self.listenForCriticalBatteryAlarm)
		# self.lowBatteryListeningThread.start()

	def beginSimulation(self):
		'''
		When the simulation begins, each car is assigned a task (provided that there are not fewer tasks than cars - this case is handled in the asssignToFahrzeug method)
		:return:
		'''
		print("Starting Simulation")
		for f in self.fahrzeugIds:
			self.assignTaskToFahrzeug(f)
		for f in self.fahrzeugIds:

			if self.fzIdToTask[f] != None:
				self.calculateAndSendNextPositionToFahrzeug(f, self.fzIdToTask[f], self.initialPositions[f][0], self.initialPositions[f][0])



	def assignTaskToFahrzeug(self, fzId):
		'''
		This method is called at the start of the simulation as well as whenever a car finishes a task.
		If there are remaining tasks to do, this method creates a task for the given Fahrzeug,
		starting where it is currently placed and ending at a random board square. This topic
		is then pushed to the tasks topic.
		:param fzId: id of the car to whom a task might be assigned
		:param currentX: the current x-position of the car
		:param currentY: the current y-position of the car
		:return: (-1 if all tasks have been completed, None or newTask object if a new task is assigned)
		'''

		'''
		if there are no tasks remaining, then the car will not be assigned a task
		The dictionary keeping track of tasks assigned to cars will map from this car
		to none.
		Since there are no tasks remaining, the car is sent a message a decease message.
		'''
		if self.numRemainingTasks <= 0:
			self.fzIdToTask[fzId] = None;
			self.sendNextPositionToFahrzeug(fzId,"-1",-1,-1); #decease message, indicated by all -1's

			self.sendNewTask(fzId,decease=True); #decease message to that car's consumer of new tasks

			'''
			If the last task has just been accomplished then -1 is returned, indicating that the Streams App may now decease
			'''
			if self.accomplishedTasks == self.numTasks:
				return (-1,None);
			return (0, None);



		'''
		If this position is reached, then there exist further tasks to be assigned.
		A task it generated with a random start and end position which are not the same
		'''
		startX, startY, stopX, stopY = np.random.randint(0,self.boardLength, 4);
		while startX == stopX and startY == stopY:
			startX, startY, stopX, stopY = np.random.randint(0, self.boardLength, 4);
		self.mainLogFile.write("New task assigned to "+fzId+" starting on "+str(startX)+","+str(stopX)+"; ending on "+str(startY)+","+str(stopY)+"\n")

		#the task ID increments up from 0 up to numTasks - 1
		taskId = str(self.numTasks-self.numRemainingTasks)
		#a corresponding task object is initialized
		newTask = Task(startX = startX,startY=startY, stopX = stopX,stopY=stopY, assignedTo=fzId,taskId=taskId,tileSize=self.tileSize);

		#note that this car is assigned to the new task just created
		self.fzIdToTask[fzId] = newTask;

		#send a message indicating the creation of this new task
		self.sendNewTask(fzId,newTask=newTask);
		self.numRemainingTasks += -1;
		return (0, newTask)



	def sendNewTask(self, fzId, newTask = None, decease = False):
		'''
		Produce a new message in the newTask topic for consumption by cars
		:param fzId: the car to whom the new task is assigned
		:param newTask: the new task object
		:param decease: parameter set to indicate to the car that it may stop consuming the newTask topic, if all
		tasks have already been reserved
		:return:
		'''


		#decease dict is indicated by -1 values for x and y
		if decease:
			taskDict = {
				"vehicleId": fzId,
				"startX": -1,
				"startY": -1
			}

		#new task for reference by the corresponding car
		elif newTask != None:
			taskDict = {
				"taskId": newTask.taskId,
				"vehicleId": fzId,
				"startX": str(newTask.startX),
				"startY": str(newTask.startY),
				"stopX": str(newTask.stopX),
				"stopY": str(newTask.stopY),
				"timestamp": str(datetime.datetime.now())
			}
		else:
			raise NotImplementedError("Either a new task is sent or a decease notice is sent; neither is not an option!")

		#produce message into newTasks Kafka topic
		mes = str.encode(json.dumps(taskDict));
		self.producer.send('newTasks', mes)
		self.producer.flush()



	def listenForCriticalBatteryAlarm(self):
		'''
		#DEPRICATED - This functionality is now accomplished in the method listenForPositionUpdates
		Whenever a Fahrzeug has no battery left, this method will be triggered, as it is listening
		to the criticalBatteryTopic topic
		:return:
		'''

		#this for-loop serves for the thread to consume the criticalBatteryTopic topic.
		#Whenever there is a new message in this topic, a new round of the for-loop is triggered
		for mes in self.lowBatteryConsumer:

			#if 10 seconds pass betewen messages consumed then there has probably been an error.
			#This is a safe-guard against deadlocking
			self.lowBatteryConsumer.consumer_timeout_ms = 10000

			#decode message, determine which car has low battery
			mes = mes.value.decode()
			currentFZPosDict = json.loads(mes);
			fzInQuesetion = currentFZPosDict["vehicleId"]

			#car of id -1 is the signal that the app may close. Breaking out of the for-loop means
			#that consumption may stop and the thread working on consuming this topic may join
			if fzInQuesetion == "-1":
				break;

			self.mainLogFile.write("App received message: " + mes + "\n");

			#indicate that the app must first guide this tasks's car to a charging station before it continues guiding it
			#towards its task's target
			self.fzIdToTask[fzInQuesetion].putOnHoldBecauseOfBattery();

		print("Done consuming critical battery alarums")

	def generateChargingStations(self):
		'''
		Generate the passed number of charging stations
		:return:
		'''
		self.stations = []
		for _ in range(self.numChargingStations):
			x, y = np.random.randint(0,self.boardLength,2)
			self.stations.append(ChargingStation(x,y,self.visual,self.tileSize));

	def generateFahrzeuge(self):
		'''
		Generate the passed number of cars
		:return: List of car objects which the GUI uses to draw the cars. These car objects
		are never further referenced by this class - this is proven by making the list a local variable
		'''

		#id's ascending from 0 to numCars-1
		self.fahrzeugIds = [str(s) for s in range(self.numCars)];

		fahrzeuge = []#only used for GUI

		#note the cars' initial positions for initial task assignment
		self.initialPositions = {}
		for id in self.fahrzeugIds:
			startX, startY = np.random.randint(0,self.boardLength, 2)
			self.initialPositions[id] = (startX,startY)

			#create car object
			fz = Fahrzeug(id,startX,startY,self.secondsToPerformMove,
						  self.secondsForCharge,self.movesUntilRecharge,
						  self.visual, self.logsRoot, self.tileSize)
			fahrzeuge.append(fz);

			#each car has no assigned task upon generation
			self.fzIdToTask[id] = None;
			self.mainLogFile.write("Generated car with id " + id+"\n")
		return fahrzeuge

	def findNearestChargingPort(self, x, y):
		'''
		Charging port with euclidian norm closest to the passed x and y is returned
		:param x:
		:param y:
		:return: ChargingStation object
		'''
		return self.stations[
			np.argmin(
				[np.square(station.x-int(x))
				 +np.square(station.y-int(y))
				 for station in self.stations]
			)
		]

	def calculateNextXAndY(self, taskForFahrzeug,fzId, currentX, currentY):
		'''
		Method which calculates the next square for Fahrzeug to go if it has a task and has
		sufficient battery. If it has insufficient battery then it calculates the step
		towards the nearest charging port.
		:param taskForFahrzeug: Task object
		:param fzId: id of car whose next step must be calculated
		:param currentX: current x position of car
		:param currentY:current y position of car
		:return: x, y, finished if car has either finished its task _or_ reached a charging port (if it needed to charge)
		'''

		#target default is the car's task's target destination
		targetX = taskForFahrzeug.stopX
		targetY = taskForFahrzeug.stopY


		#if the car needs to charge, then car's target is its nearest charging port
		if taskForFahrzeug.onHoldBecauseOfBattery:
			nearestChargingPort = self.findNearestChargingPort(currentX,currentY)
			targetX = nearestChargingPort.x
			targetY = nearestChargingPort.y

		#if the car has not yet reached the task's starting position, then its target is the tasks' starting position
		elif not taskForFahrzeug.initialPositionReached:
			targetX = taskForFahrzeug.startX
			targetY = taskForFahrzeug.startY

		'''
		Calculate the x and y coordinates that are one step in the direction of the target
		If the target x and y are equal to the car's current x and y, then "finished" is noted 
		'''
		finished = True;
		if targetX != currentX:
			nextX = currentX + int((targetX - currentX) / np.fabs((targetX - currentX)));
			finished = False
		else:
			nextX = currentX;

		if targetY != currentY:
			nextY = currentY + int((targetY - currentY) / np.fabs((targetY - currentY)));
			finished = False
		else:
			nextY = currentY;

		'''
		If the car finished its current mission, and doesn't need to charge and hadn't yet been at its task's initial position,
		that means that the car reached its task's initial position
		This is noted in the task object, and the method is re-called, noting that the task's initial position has been reached
		'''
		if finished and not taskForFahrzeug.initialPositionReached and not taskForFahrzeug.onHoldBecauseOfBattery:

			#note that the tasks' initial position has been reached
			taskForFahrzeug.arriveAtInitialPosition()
			self.mainLogFile.write("Car " + fzId + " reached initial position for its task; now moving towards destination\n")
			#re-call the method
			return self.calculateNextXAndY(taskForFahrzeug,fzId,currentX,currentY);

		#Return the calculated x and y positions
		return nextX, nextY, finished

	def calculateAndSendNextPositionToFahrzeug(self,fzId,taskForFahrzeug,currentX, currentY):
		'''
		This method calls several helper methods to calculate the next position for the car to go,
		and to send this message to the nextPositions topic
		:param fzId: the car whose next position will be calculated
		:param taskForFahrzeug: the car's current task
		:param currentX: the car's current x position
		:param currentY: the car's current y position
		:return:
		'''

		#call helper method to calculate the next x and y position for car
		nextX, nextY, finished = self.calculateNextXAndY(taskForFahrzeug, fzId,currentX,currentY)


		#If car needed a charge and was thus headed towards a charging port
		if taskForFahrzeug.onHoldBecauseOfBattery:

			#if the car had just been charging, then it is all charged up now and can resume heading towards its task's
			#target (or its initial position, if this had not yet been reached)
			if taskForFahrzeug.charging:
				taskForFahrzeug.charging = False
				taskForFahrzeug.resume()
				self.mainLogFile.write("Car " + str(fzId) + "is charged up and ready to rumble\n")
				return self.calculateAndSendNextPositionToFahrzeug(fzId,taskForFahrzeug,currentX, currentY);
			#If the car has will reach its charging port in this current move
			elif finished:
				'''
				indicate that the car is now charging, and produce a message in the nextPositions topic
				which will tell the car to go to the charging port's position and to charge there
				'''
				taskForFahrzeug.charging = True;
			self.sendNextPositionToFahrzeug(fzId,taskForFahrzeug.taskId, nextX, nextY, charge=taskForFahrzeug.charging)

		#If the car did not need a charge but it did finish its task
		elif finished:

			self.mainLogFile.write("Woohoo! Car " + str(fzId) + " finished its task: " + str(taskForFahrzeug) + "\n")

			#Increment the number of completed tasks
			self.accomplishedTasks += 1;
			taskForFahrzeug.finish()

			'''
			Assign a new task to this car. If assignTaskToFahrzeug returns -1 at the first position, then all tasks are done
			And this will recurse back to the consumer loop, which will break out.
			newTask is None, then there are no more tasks to assign to the car.
			'''
			simulationOver, newTask = self.assignTaskToFahrzeug(fzId);
			if simulationOver == -1:
				return simulationOver;
			elif newTask != None:
				self.calculateAndSendNextPositionToFahrzeug(fzId, newTask, currentX, currentY)

		#If the car did not yet reach its destination, then simply send it the next position which was previously calculated
		else:
			self.sendNextPositionToFahrzeug(fzId,taskForFahrzeug.taskId, nextX, nextY)


	def listenForPositionUpdates(self):
		'''
		Whenever a Fahrzeug has moved, it produces a message in the updateAppWithCurrentPositions topic.
		There is a thread whose life cycle revolves around this method, listening for cars which have moved
		passed to that Fahrzeug
		:return:
		'''

		# this for-loop serves for the thread to consume the updateAppWithCurrentPositions topic.
		# Whenever there is a new message in this topic, a new round of the for-loop is triggered
		#When a new message is consumed that means a car has moved one position and is asking for
		#its next position. This is calculated and sent back to the car via the nextPositions topic
		for mes in self.positionUpdateConsumer:

			# if 10 seconds pass betewen messages consumed then there has probably been an error.
			# This is a safe-guard against deadlocking
			self.positionUpdateConsumer.consumer_timeout_ms = 10000

			#decode message from car
			mes = mes.value.decode()
			currentFZPosDict = json.loads(mes);
			self.mainLogFile.write("App received message" + mes + "\n");
			fzInQuesetion = currentFZPosDict["vehicleId"]
			taskForFahrzeug = self.fzIdToTask[fzInQuesetion];
			needCharge = currentFZPosDict["needCharge"];

			#if car has low battery, then this is indicated in task
			if needCharge:
				self.fzIdToTask[fzInQuesetion].putOnHoldBecauseOfBattery();

			#calculate the next position for the car. If this method returns -1, then all tasks have been
			#accomplished and consumption of the updateAppWithCurrentPositions may cease
			allTasksDone = self.calculateAndSendNextPositionToFahrzeug(fzInQuesetion,taskForFahrzeug,int(currentFZPosDict["x"]),int(currentFZPosDict["y"]))
			if allTasksDone == -1:

				#Trigger decease in the consumer of the criticalBatteryTopic consumer, and break out of
				#the consumption loop
				# self.sendDeceaseToCriticalBatteryAlarmConsumer() # depricated
				break;

		self.finished = True;  # telling visual mode it can quit
		print("Streaming app is done consuming Position Updates")

	def sendDeceaseToCriticalBatteryAlarmConsumer(self):
		'''
		#Depricated - no longer necessary as this topic no longer exists
		This method is called by the Streams App to alert the thread consuming the criticalBatteryTopic
		that it may now cease consuming
		:return:
		'''

		#-1 is the code for decease
		deceaseDict = {
			"vehicleId": "-1"
		}

		#kafka syntax for producing a message in a topic
		self.producer.send('criticalBatteryTopic', str.encode(json.dumps(deceaseDict)))
		self.producer.flush()



	def sendNextPositionToFahrzeug(self, id,taskId, x, y, charge = False):
		'''
		This method pushes a message into the nextPositions queue for the particular car
		who needs to know where to move next
		:param id: id of car whose next move has been calculated
		:param x: next x position of car
		:param y: next y position of car
		:param charge: whether the car reached a charging port and should charge
		:return:
		'''


		positionDict = {
			"vehicleId": id,
			"taskId":taskId,
			"x": str(x),
			"y": str(y),
			"timestamp": str(datetime.datetime.now()),
			"charge":charge
		}

		# kafka syntax for producing a message in a topic
		mes = json.dumps(positionDict);
		self.producer.send('nextPositions', str.encode(mes))
		self.producer.flush()

		self.mainLogFile.write("App sent message: " + mes + "\n");




	def finish(self):
		'''
		This method is triggered only when all threads have been joined and kafka consumers
		have stopped consuming. the main log file is closed and the process finishes.
		:return:
		'''
		self.mainLogFile.write("All " + str(self.numTasks) + " tasks have been accomplished; terminating");
		self.mainLogFile.close()
		print("Streams App finshing")







	def draw(self, screen, tileSize):
		'''
		Relevant for visual mode. The Streams App contains all station and task objects - it requests
		that each of them draw themselves
		:param screen:
		:param tileSize:
		:return:
		'''
		for station in self.stations:
			station.draw(screen, tileSize);


		for task in self.fzIdToTask.values():
			if task != None and task.active:
				task.draw(screen, tileSize);