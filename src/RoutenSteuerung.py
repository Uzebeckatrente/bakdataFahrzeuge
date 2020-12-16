
from .basicFuncs import *;
from .Fahrzeug import *;
import threading
from .gui import arrow
from .ChargingStation import *;
from .Task import *;




class RoutenSteuerung():
	'''
	Class that contains the Kafka stream app
	'''
	def __init__(self, numCars, numTasks,numChargingStations,movesUntilRecharge, secondsToPerformMove,secondsForCharge,boardLength, visual, tileSize = -1, logsRoute = "./logs"):
		self.numFahrzeuge = numCars;
		self.numTasks = numTasks;
		self.numRemainingTasks = numTasks;
		self.positionUpdateConsumer = KafkaConsumer('updateAppWithCurrentPositions')
		self.lowBatteryConsumer = KafkaConsumer('criticalBatteryTopic')
		self.producer = KafkaProducer(bootstrap_servers='localhost:9092')
		self.boardLength = boardLength;
		self.fzIdToTask = {}
		self.secondsToPerformMove=secondsToPerformMove;
		self.visual = visual;
		self.tileSize = tileSize;
		self.numChargingStations=numChargingStations;
		self.movesUntilRecharge=movesUntilRecharge;
		self.secondsForCharge=secondsForCharge;
		if not os.path.exists(logsRoute):
			os.mkdir(logsRoute);
		self.logsRoot = logsRoute;

		self.mainLogFile = open(self.logsRoot + "/" + "main.txt","w");
		self.mainLogFile.write("="*15+"\n"+"Initialized simulation with " + str(numCars) + " cars, " + str(numTasks) + " tasks, " + str(numChargingStations) + " charging stations, with board of lenth " + str(boardLength)+"\n"+"="*15+"\n")
		self.accomplishedTasks = 0;

		self.ids = [str(s) for s in range(numCars)];
		self.finished = False;

		self.generateChargingStations();

	def initThreads(self):
		self.listeningThread = threading.Thread(target=self.listenForPositionUpdates)
		self.listeningThread.start()
		self.lowBatteryListeningThread = threading.Thread(target=self.listenForCriticalBatteryAlarm)
		self.lowBatteryListeningThread.start()

	def beginSimulation(self):
		print("Starting Simulation")
		for f in self.fahrzeugIds:
			self.assignTaskToFahrzeug(f, self.initialPositions[f][0],self.initialPositions[f][1])

	def finish(self):
		self.mainLogFile.write("All " + str(self.numTasks) + " tasks have been accomplished; terminating");
		self.mainLogFile.close()





	def draw(self, screen, tileSize):
		for station in self.stations:
			station.draw(screen, tileSize);


		for task in self.fzIdToTask.values():
			if task != None and task.active:
				task.draw(screen, tileSize);

	def assignTaskToFahrzeug(self, fzId, currentX, currentY):
		'''
		If there are remaining tasks to do, this method creates a task for the given Fahrzeug,
		starting where it is currently placed and ending at a random board square. This topic
		is then pushed to the tasks topic.
		:param fz:
		:return:
		'''
		if self.numRemainingTasks <= 0:
			self.fzIdToTask[fzId] = None;
			self.sendNextPositionToFahrzeug(fzId,"-1",-1,-1);
			taskDict = {
				"vehicleId": fzId,
				"startX": -1,
				"startY": -1
			}
			self.sendNewTask(taskDict);

			if self.accomplishedTasks == self.numTasks:
				return -1;
			return;

		startX = np.random.randint(0,self.boardLength);
		startY = np.random.randint(0,self.boardLength);
		stopX = np.random.randint(0,self.boardLength)
		stopY = np.random.randint(0,self.boardLength);
		while startX == stopX and startY == stopY:
			startX = np.random.randint(0, self.boardLength);
			startY = np.random.randint(0, self.boardLength);
			stopX = np.random.randint(0, self.boardLength)
			stopY = np.random.randint(0, self.boardLength);
		self.mainLogFile.write("New task assigned to "+fzId+" starting on "+str(startX)+","+str(stopX)+"; ending on "+str(startY)+","+str(stopY)+"\n")

		taskId = str(self.numTasks-self.numRemainingTasks)
		newTask = Task(startX = startX,startY=startY, stopX = stopX,stopY=stopY, assignedTo=fzId,taskId=taskId,tileSize=self.tileSize);
		self.fzIdToTask[fzId] = newTask;
		self.availableFahrzeuge.remove(fzId);
		taskDict = {
			"taskId":taskId,
			"vehicleId": fzId,
			"startX": str(newTask.startX),
			"startY": str(newTask.startY),
			"stopX": str(newTask.stopX),
			"stopY": str(newTask.stopY),
			"timestamp": str(datetime.datetime.now())
		}

		self.sendNewTask(taskDict);
		self.numRemainingTasks += -1;
		self.calculateAndSendNextPositionToFahrzeug(fzId,newTask,currentX,currentY)

	def sendNewTask(self,taskDict):
		mes = str.encode(json.dumps(taskDict));
		self.producer.send('newTasks', mes)
		self.producer.flush()



	def listenForCriticalBatteryAlarm(self):
		'''
		Whenever a Fahrzeug has no battery left, this method will be triggered, as it is listening
		to the criticalBatteryTopic topic
		:return:
		'''
		for mes in self.lowBatteryConsumer:
			self.lowBatteryConsumer.consumer_timeout_ms = 10000
			mes = mes.value.decode()
			currentFZPosDict = json.loads(mes);
			fzInQuesetion = currentFZPosDict["vehicleId"]
			if fzInQuesetion == "-1":
				break;
			self.mainLogFile.write("App received message: " + mes + "\n");
			self.fzIdToTask[fzInQuesetion].putOnHoldBecauseOfBattery();
		print("Done consuming critical battery alarums")

	def generateChargingStations(self):
		self.stations = []
		for _ in range(self.numChargingStations):
			self.stations.append(ChargingStation(np.random.randint(0,self.boardLength),np.random.randint(0,self.boardLength),self.visual,self.tileSize));

	def generateFahrzeuge(self):
		self.fahrzeugIds = []
		fahrzeuge = []#only used for GUI
		self.availableFahrzeuge = []
		self.initialPositions = {}
		for id in self.ids:
			startX = np.random.randint(0,self.boardLength)
			startY = np.random.randint(0,self.boardLength)
			self.initialPositions[id] = (startX,startY)
			fz = Fahrzeug(id,startX,startY,self.secondsToPerformMove,self.secondsForCharge,self.movesUntilRecharge, self.visual, self.logsRoot, self.tileSize)
			fahrzeuge.append(fz);
			self.fahrzeugIds.append(id);
			self.availableFahrzeuge.append(id);
			self.fzIdToTask[id] = None;
			self.mainLogFile.write("Generated car with id " + id+"\n")
		return fahrzeuge

	def findNearestChargingPort(self, x, y):
		return self.stations[np.argmin([np.square(station.x-int(x))+np.square(station.y-int(y)) for station in self.stations])]

	def calculateNextXAndY(self, taskForFahrzeug,fzId, currentX, currentY):
		'''
		Method which calculates the direction for the Fahrzeug to go if it has a task and has
		sufficient battery. If it has insufficient battery then it calculates the step
		towards the nearest charging port.
		:param taskForFahrzeug:
		:return:
		'''
		targetX = taskForFahrzeug.stopX
		targetY = taskForFahrzeug.stopY



		if taskForFahrzeug.onHoldBecauseOfBattery:
			nearestChargingPort = self.findNearestChargingPort(currentX,currentY)
			targetX = nearestChargingPort.x
			targetY = nearestChargingPort.y
		elif not taskForFahrzeug.initialPositionReached:
			targetX = taskForFahrzeug.startX
			targetY = taskForFahrzeug.startY

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

		if finished and not taskForFahrzeug.initialPositionReached and not taskForFahrzeug.onHoldBecauseOfBattery:
			#This means the initial destination has been reached
			taskForFahrzeug.arriveAtInitialPosition()
			self.mainLogFile.write("Car " + fzId + " reached initial position for its task; now moving towards destination\n")
			return self.calculateNextXAndY(taskForFahrzeug,fzId,currentX,currentY);


		return nextX, nextY, finished

	def calculateAndSendNextPositionToFahrzeug(self,fzId,taskForFahrzeug,currentX, currentY):
		nextX, nextY, finished = self.calculateNextXAndY(taskForFahrzeug, fzId,currentX,currentY)

		if taskForFahrzeug.onHoldBecauseOfBattery:
			charge = False
			if taskForFahrzeug.charging:
				taskForFahrzeug.charging = False
				taskForFahrzeug.resume()
				self.mainLogFile.write("Car " + str(fzId) + "is charged up and ready to rumble\n")
			elif finished:
				charge = True;
				taskForFahrzeug.charging = True;
			self.sendNextPositionToFahrzeug(fzId,taskForFahrzeug.taskId, nextX, nextY, charge=charge)
		elif finished:

			self.mainLogFile.write("Woohoo! Car " + str(fzId) + " finished its task: " + str(taskForFahrzeug) + "\n")
			self.accomplishedTasks += 1;
			self.availableFahrzeuge.append(fzId);
			taskForFahrzeug.finish()
			return self.assignTaskToFahrzeug(fzId,currentX,currentY);
		else:
			self.sendNextPositionToFahrzeug(fzId,taskForFahrzeug.taskId, nextX, nextY)


	def listenForPositionUpdates(self):
		'''
		Whenever a Fahrzeug has moved, this method is triggered; a new position must be
		passed to that Fahrzeug
		:return:
		'''

		for mes in self.positionUpdateConsumer:
			self.positionUpdateConsumer.consumer_timeout_ms = 10000
			mes = mes.value.decode()
			currentFZPosDict = json.loads(mes);
			self.mainLogFile.write("App received message" + mes + "\n");
			fzInQuesetion = currentFZPosDict["vehicleId"]
			taskForFahrzeug = self.fzIdToTask[fzInQuesetion];
			allTasksDone = self.calculateAndSendNextPositionToFahrzeug(fzInQuesetion,taskForFahrzeug,int(currentFZPosDict["x"]),int(currentFZPosDict["y"]))
			if allTasksDone == -1:
				#maybe send desist to other consumer
				self.sendDeceaseToCriticalBatteryAlarmConsumer()
				self.finished = True;
				break;

		print("Done consuming Position Updates:)")

	def sendDeceaseToCriticalBatteryAlarmConsumer(self):
		deceaseDict = {
			"vehicleId": "-1"
		}

		mes = json.dumps(deceaseDict);
		self.producer.send('criticalBatteryTopic', str.encode(mes))
		self.producer.flush()



	def sendNextPositionToFahrzeug(self, id,taskId, x, y, charge = False):
		'''
		This method pushes a message into the nextPositions queue for the particular Fahrzeug
		who needs to know where to move next
		:param id:
		:param x:
		:param y:
		:param charge:
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

		mes = json.dumps(positionDict);
		self.mainLogFile.write("App sent message: " + mes+"\n");
		self.producer.send('nextPositions', str.encode(mes))
		self.producer.flush()




