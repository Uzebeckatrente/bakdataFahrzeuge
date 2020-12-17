from .basicFuncs import *;

class Task():
	'''
	The task class represents a start and an end position. It has a unique id,
		and knows which car to which it is assigned.
	'''
	def __init__(self, startX, startY, stopX, stopY, assignedTo, taskId, tileSize):
		'''
		Initialization of the each Task object
		:param startX: X position of the square on which this task starts
		:param startY: Y position of the square on which this task starts
		:param stopX: X position of the square on which this task ends
		:param stopY: Y position of the square on which this task ends
		:param assignedTo: id of car to which it is assigned
		:param taskId: unique task id
		:param tileSize: size of squares of board so it knows how to draw itself (only for visual mode)
		'''

		# assign passed values as instance variables in Task object
		self.startX = startX;
		self.startY = startY;
		self.stopX = stopX;
		self.stopY = stopY;
		self.taskId = taskId;
		self.assignedTo = assignedTo;


		#initialize task parameters
		self.onHoldBecauseOfBattery = 0; #car assigned to task does not need a recharge at this instant
		self.active = True; #Task is initialized upon assignment
		self.initialPositionReached = False;
		self.charging = False;

		#initialize values and load images, only relevant to visual-mode
		self.targetImageEnd = pg.image.load("./src/img/endX.png")
		self.targetImageStart = pg.image.load("./src/img/startX.png")
		self.targetImageEnd = pg.transform.scale(self.targetImageEnd, (int(tileSize * 0.95), int(tileSize * 0.95)))
		self.targetImageStart = pg.transform.scale(self.targetImageStart, (int(tileSize * 0.95), int(tileSize * 0.95)))

	def putOnHoldBecauseOfBattery(self):
		'''
		This task now has the priority of pointing its car to the nearest charging port, rather than its final destination
		:return:
		'''
		self.onHoldBecauseOfBattery = True;
	def resume(self):
		'''
		This task no longer has the priority of pointing its car to the nearest charging port;
		The streams app may now resume guiding its assigned car towards its final destination
		:return:
		'''
		self.onHoldBecauseOfBattery = False;


	def finish(self):
		'''
		If the end position of task has been reached, then the task is set to inactive
		:return:
		'''
		self.active = False;

	def arriveAtInitialPosition(self):
		self.initialPositionReached = True;



	def draw(self, screen, tileSize):
		'''
		The task draws itself in pygame by indicating its start position with a white X, and its end position with a red X
		:param screen:
		:param tileSize:
		:return:
		'''
		screen.blit(self.targetImageEnd, (self.stopX * tileSize, self.stopY * tileSize))
		screen.blit(self.targetImageStart, (self.startX * tileSize, self.startY * tileSize))

	def __str__(self):
		return "start: "+str((self.startX,self.startY))+"stop: "+str((self.stopX,self.stopY))