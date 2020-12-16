from .basicFuncs import *;

class Task():
	def __init__(self, startX, startY, stopX, stopY, assignedTo, taskId, tileSize):
		self.startX = startX;
		self.startY = startY;
		self.stopX = stopX;
		self.stopY = stopY;
		self.taskId = taskId;
		self.assignedTo = assignedTo;
		self.onHoldBecauseOfBattery = 0;
		self.active = True;
		self.initialPositionReached = False;
		self.charging = False;

		self.targetImageEnd = pg.image.load("./src/img/endX.png")
		self.targetImageStart = pg.image.load("./src/img/startX.png")
		self.targetImageEnd = pg.transform.scale(self.targetImageEnd, (int(tileSize * 0.95), int(tileSize * 0.95)))
		self.targetImageStart = pg.transform.scale(self.targetImageStart, (int(tileSize * 0.95), int(tileSize * 0.95)))

	def putOnHoldBecauseOfBattery(self):
		self.onHoldBecauseOfBattery = True;
	def resume(self):
		self.onHoldBecauseOfBattery = False;
	def finish(self):
		self.active = False;

	def arriveAtInitialPosition(self):
		self.initialPositionReached = True;

	def __str__(self):
		return "start: "+str((self.startX,self.startY))+"stop: "+str((self.stopX,self.stopY))

	def draw(self, screen, tileSize):
		screen.blit(self.targetImageEnd, (self.stopX * tileSize, self.stopY * tileSize))
		screen.blit(self.targetImageStart, (self.startX * tileSize, self.startY * tileSize))