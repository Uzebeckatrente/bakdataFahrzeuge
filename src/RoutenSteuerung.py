
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
	def __init__(self, numCars, numTasks,numChargingStations,movesUntilRecharge, secondsToPerformMove,secondsForCharge,boardLength, visual, tileSize = -1):
		self.numFahrzeuge = numCars;
		self.numTasks = numTasks;
		self.numRemainingTasks = numTasks;
		self.consumer = KafkaConsumer('updateAppWithCurrentPositions')
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

		listeningThread = threading.Thread(target=self.listenForPositionUpdates)
		listeningThread.start()
		lowBatteryListeningThread = threading.Thread(target=self.listenForCriticalBatteryAlarm)
		lowBatteryListeningThread.start()

		self.ids = [str(s) for s in range(numCars)];
		self.generateFahrzeuge();
		self.generateChargingStations();

	def beginSimulation(self):
		for f in self.fahrzeuge.values():
			self.assignTaskToFahrzeug(f)

	def draw(self, screen, tileSize):
		for station in self.stations:
			station.draw(screen, tileSize);

		for fz in self.fahrzeuge.values():
			fz.draw(screen, tileSize);
			if fz.id in self.fzIdToTask and self.fzIdToTask[fz.id] != None:
				if not self.fzIdToTask[fz.id].onHoldBecauseOfBattery:
					arrow(screen, (220, 123, 40), (0, 255, 0), ((fz.x + 0.5) * tileSize, (fz.y + 0.5) * tileSize), ((self.fzIdToTask[fz.id].stopX + 0.5) * tileSize, (self.fzIdToTask[fz.id].stopY + 0.5) * tileSize), 2);
				else:
					nearestStation = self.findNearestChargingPort(fz.x,fz.y);
					arrow(screen, (255,0, 0), (255,0, 30), ((fz.x + 0.5) * tileSize, (fz.y + 0.5) * tileSize), ((nearestStation.x + 0.5) * tileSize, (nearestStation.y + 0.5) * tileSize), 2);

		for task in self.fzIdToTask.values():
			if task != None and task.active:
				task.draw(screen, tileSize);

	def assignTaskToFahrzeug(self, fz):
		'''
		If there are remaining tasks to do, this method creates a task for the given Fahrzeug,
		starting where it is currently placed and ending at a random board square. This topic
		is then pushed to the tasks topic.
		:param fz:
		:return:
		'''
		if self.numRemainingTasks <= 0:
			self.fzIdToTask[fz.id] = None;
			return;


		newTask = Task(startX=fz.x, startY=fz.y, stopX = np.random.randint(0,self.boardLength),stopY=np.random.randint(0,self.boardLength), assignedTo=fz.id,taskId=self.numTasks-self.numRemainingTasks-1,tileSize=self.tileSize);
		self.fzIdToTask[fz.id] = newTask;
		taskDict = {
			"vehicleId": fz.id,
			"startX": str(newTask.startX),
			"startY": str(newTask.startY),
			"stopX": str(newTask.stopX),
			"stopY": str(newTask.stopY),
			"timestamp": str(datetime.datetime.now())
		}

		mes = str.encode(json.dumps(taskDict));
		self.producer.send('tasks', mes)
		self.producer.flush()
		self.numRemainingTasks += -1;
		self.sendNextPositionToFahrzeug(fz.id,fz.x,fz.y);

	def listenForCriticalBatteryAlarm(self):
		'''
		Whenever a Fahrzeug has no batter left, this method will be triggered, as it is listening
		to the criticalBatteryTopic topic
		:return:
		'''
		for mes in self.lowBatteryConsumer:
			mes = mes.value.decode()
			currentFZPosDict = json.loads(mes);
			fzInQuesetion = currentFZPosDict["vehicleId"]
			self.fzIdToTask[fzInQuesetion].putOnHoldBecauseOfBattery();


	def generateChargingStations(self):
		self.stations = []
		for _ in range(self.numChargingStations):
			self.stations.append(ChargingStation(np.random.randint(0,self.boardLength),np.random.randint(0,self.boardLength),self.visual,self.tileSize));

	def generateFahrzeuge(self):
		self.fahrzeuge = {}
		for id in self.ids:
			fz = Fahrzeug(id,np.random.randint(0,self.boardLength),np.random.randint(0,self.boardLength),self.secondsToPerformMove,self.secondsForCharge,self.movesUntilRecharge, self.visual, self.tileSize)
			self.fahrzeuge[id] = fz;
			self.fzIdToTask[id] = None;
			print("generated",self.fzIdToTask)

	def findNearestChargingPort(self, x, y):
		return self.stations[np.argmin([np.square(station.x-int(x))+np.square(station.y-int(y)) for station in self.stations])]

	def calculateNextXAndY(self, taskForFahrzeug,currentFZPosDict):
		'''
		Method which calculates the direction for the Fahrzeug to go if it has a task and has
		sufficient battery. If it has insufficient battery then it calculates the step
		towards the nearest charging port.
		:param taskForFahrzeug:
		:param currentFZPosDict:
		:return:
		'''
		targetX = taskForFahrzeug.stopX
		targetY = taskForFahrzeug.stopY
		currentX = int(currentFZPosDict["x"]);
		currentY = int(currentFZPosDict["y"]);

		if taskForFahrzeug.onHoldBecauseOfBattery:
			nearestChargingPort = self.findNearestChargingPort(currentFZPosDict["x"],currentFZPosDict["y"])
			targetX = nearestChargingPort.x
			targetY = nearestChargingPort.y

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
		return nextX, nextY, finished

	def listenForPositionUpdates(self):
		'''
		Whenever a Fahrzeug has moved, this method is triggered; a new position must be
		passed to that Fahrzeug
		:return:
		'''

		for mes in self.consumer:
			mes = mes.value.decode()
			currentFZPosDict = json.loads(mes);
			fzInQuesetion = currentFZPosDict["vehicleId"]
			taskForFahrzeug = self.fzIdToTask[fzInQuesetion];

			nextX, nextY, finished = self.calculateNextXAndY(taskForFahrzeug,currentFZPosDict)

			if finished and taskForFahrzeug.onHoldBecauseOfBattery:
				print("fz",fzInQuesetion,"is charged up and ready to rumble")
				taskForFahrzeug.resume()
				self.sendNextPositionToFahrzeug(fzInQuesetion, nextX, nextY,charge = True)
			elif finished:
				print("woohoo! fahrzeug",fzInQuesetion,"finished its task",taskForFahrzeug)
				taskForFahrzeug.finish()
				self.assignTaskToFahrzeug(self.fahrzeuge[fzInQuesetion]);
			else:
				self.sendNextPositionToFahrzeug(fzInQuesetion,nextX,nextY)




	def sendNextPositionToFahrzeug(self, id, x, y, charge = False):
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
			"x": str(x),
			"y": str(y),
			"timestamp": str(datetime.datetime.now()),
			"charge":charge
		}

		mes = str.encode(json.dumps(positionDict));
		print('app sends',mes)
		self.producer.send('nextPositions', mes)
		self.producer.flush()




