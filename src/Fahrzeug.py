from .basicFuncs import *;
import threading



class Fahrzeug():
	'''
	Class representing vehicles in this simulation
	'''
	def __init__(self, id,x,y,secondsToPerformMove,secondsForRecharge,movesUntilRecharge, visual,logsRoot, tileSize = -1):
		self.x = x;
		self.y = y;
		self.visual = visual;
		self.charging = False;
		self.id = str(id);
		self.secondsToPerformMove = secondsToPerformMove;
		self.nextPositionConsumer = KafkaConsumer('nextPositions')
		self.newTaskConsumer = KafkaConsumer('newTasks')
		self.producer = KafkaProducer(bootstrap_servers='localhost:9092')
		self.movesUntilRecharge = movesUntilRecharge
		self.secondsForRecharge=secondsForRecharge;
		self.logsRoot = logsRoot;
		self.logFile = open(logsRoot+"/"+self.id+".txt","w")
		self.logFile.write("Car with id " + str(id) + " intialized\n");
		self.currentTask = "-1";

		self.stepsForCurrentTask = 0;
		self.finishes = 0;


		if visual:
			self.carNormal = pg.image.load("./src/img/carNormal.png")
			self.carNormal = pg.transform.scale(self.carNormal, (int(tileSize * 0.95), int(tileSize * 0.95)))

			self.carLowBattery = pg.image.load("./src/img/carLowBattery.png")
			self.carLowBattery = pg.transform.scale(self.carLowBattery, (int(tileSize * 0.95), int(tileSize * 0.95)))

			self.carCharging = pg.image.load("./src/img/carLowBattery.png")
			self.carCharging = pg.transform.scale(self.carLowBattery, (int(tileSize * 0.4), int(tileSize * 0.4)))
		else:
			if secondsToPerformMove < 0.001:
				self.secondsToPerformMove = 0.001
		self.battery = self.movesUntilRecharge;

	def initThreads(self):
		self.newTaskThread = threading.Thread(target=self.listenForNewTask)
		self.newTaskThread.start()
		self.listeningThread = threading.Thread(target=self.listenForNextPosition)
		self.listeningThread.start()




	def finish(self):

		print("recd finish",self.id,self.currentTask)
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
		for mes in self.nextPositionConsumer:
			self.nextPositionConsumer.consumer_timeout_ms=10000
			mesStr = mes.value.decode()
			mes = json.loads(mesStr);
			if str(self.id) != mes["vehicleId"]: continue;
			if int(mes["x"]) == -1 and int(mes["y"]) == -1:
				print("received desist")
				break;


			while mes["taskId"] != self.currentTask:
				time.sleep(0.1);
				print("Wires crossed in task generation; sleeping")

			self.logFile.write("Car " + self.id + " received message: " + mesStr+" in context of task " + self.currentTask+"\n");

			self.x = int(mes["x"]);
			self.y = int(mes["y"]);
			if mes["charge"]:
				self.charging = True;
				self.logFile.write("Car " + self.id + " is charging\n");
				if self.visual:
					time.sleep(self.secondsForRecharge);
				self.battery=self.movesUntilRecharge;

			else:
				self.charging = False;

				time.sleep(self.secondsToPerformMove);
				self.battery += -1;
				if self.battery <= 0:
					self.sendCriticalBatteryMessage()
			self.sendCurrentPositionToApp()
		print("Done listening for new positions "+self.id,self.currentTask)

	def listenForNewTask(self):
		'''
		Each time a message appears in the newTasks topic that is germane to this Fahrzeug,
		this method will be triggered
		:return:
		'''

		for mes in self.newTaskConsumer:
			self.newTaskConsumer.consumer_timeout_ms = 10000
			mesStr = mes.value.decode()
			mes = json.loads(mesStr);
			if str(self.id) != mes["vehicleId"]: continue;
			if mes["startX"] == mes["startY"] == -1:
				break;
			if self.currentTask != "-1":
				self.logFile.write("Car " + self.id + " finished task " + self.currentTask + " in " + str(self.stepsForCurrentTask) + " steps\n\n\n")
			self.stepsForCurrentTask = 0;
			self.logFile.write("Car " + self.id + " received new task: " + mesStr+"\n");
			self.currentTask = mes["taskId"];
		print("Done listening for new tasks",self.id)



	def draw(self, screen, tileSize):
		if self.charging:
			screen.blit(self.carCharging, (self.x * tileSize, self.y * tileSize))
		elif self.battery > 0:
			screen.blit(self.carNormal, (self.x * tileSize, self.y * tileSize))
		else:
			screen.blit(self.carLowBattery, (self.x * tileSize, self.y * tileSize))



	def sendCriticalBatteryMessage(self):
		'''
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

	def sendCurrentPositionToApp(self):
		'''
		This method pushes a message into the updateAppWithCurrentPositions topic for the app to consume
		:return:
		'''

		positionDict = {
			"vehicleId":self.id,
			"x":str(self.x),
			"y":str(self.y),
			"timestamp":str(datetime.datetime.now())
		}

		self.stepsForCurrentTask += 1;
		positionDictJson = json.dumps(positionDict)
		self.logFile.write("Car "+self.id+" sent current pos: "+positionDictJson+" in context of task " + self.currentTask+"\n")
		self.producer.send('updateAppWithCurrentPositions', str.encode(positionDictJson))#
		self.producer.flush()
