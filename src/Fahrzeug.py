from .basicFuncs import *;
import threading



class Fahrzeug():
	'''
	Class representing vehicles in this simulation
	'''
	def __init__(self, id,x,y,secondsToPerformMove,secondsForRecharge,movesUntilRecharge, visual, tileSize = -1):
		self.x = x;
		self.y = y;
		self.visual = visual;
		self.charging = False;
		self.id = str(id);
		self.secondsToPerformMove = secondsToPerformMove;
		self.consumer = KafkaConsumer('nextPositions')
		self.producer = KafkaProducer(bootstrap_servers='localhost:9092')
		self.movesUntilRecharge = movesUntilRecharge
		self.secondsForRecharge=secondsForRecharge;
		listeningThread = threading.Thread(target = self.listenForNextPosition)
		listeningThread.start()

		if visual:
			print(os.listdir("./src/img/"))
			self.carNormal = pg.image.load("./src/img/carNormal.png")
			self.carNormal = pg.transform.scale(self.carNormal, (int(tileSize * 0.95), int(tileSize * 0.95)))

			self.carLowBattery = pg.image.load("./src/img/carLowBattery.png")
			self.carLowBattery = pg.transform.scale(self.carLowBattery, (int(tileSize * 0.95), int(tileSize * 0.95)))

			self.carCharging = pg.image.load("./src/img/carLowBattery.png")
			self.carCharging = pg.transform.scale(self.carLowBattery, (int(tileSize * 0.4), int(tileSize * 0.4)))

		self.battery = self.movesUntilRecharge;

	def listenForNextPosition(self):
		'''
		Each time a message appears in the nextPositions queue that is germane to this Fahrzeug,
		this method will be triggered
		:return:
		'''
		print("fz",self.id,"is listening")
		for mes in self.consumer:
			mes = mes.value.decode()
			mes = json.loads(mes);
			if str(self.id) != mes["vehicleId"]: continue;
			self.x = int(mes["x"]);
			self.y = int(mes["y"]);
			if mes["charge"]:
				self.charging = True;
				time.sleep(self.secondsForRecharge);
				self.battery=self.movesUntilRecharge;

			else:
				self.charging = False;
				if self.visual:
					time.sleep(self.secondsToPerformMove);
				self.battery += -1;
				if self.battery <= 0:
					self.sendCriticalBatteryMessage()
			self.sendCurrentPositionToApp()

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
		print("fz", self.id, "sent critical battery message: ", positionDictJson)
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

		positionDictJson = json.dumps(positionDict)
		print("fz",self.id,"sent current pos: ",positionDictJson)
		self.producer.send('updateAppWithCurrentPositions', str.encode(positionDictJson))#
		self.producer.flush()
