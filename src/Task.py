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

		self.targetImage = pg.image.load("./src/img/x.png")
		self.targetImage = pg.transform.scale(self.targetImage, (int(tileSize * 0.95), int(tileSize * 0.95)))

	def putOnHoldBecauseOfBattery(self):
		self.onHoldBecauseOfBattery = True;
	def resume(self):
		self.onHoldBecauseOfBattery = False;
	def finish(self):
		self.active = False;

	def __str__(self):
		return "start: "+str((self.startX,self.startY))+"stop: "+str((self.stopX,self.stopY))

	def draw(self, screen, tileSize):
		screen.blit(self.targetImage, (self.stopX * tileSize, self.stopY * tileSize))