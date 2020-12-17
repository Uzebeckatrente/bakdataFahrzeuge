from .basicFuncs import pg;

class ChargingStation():
	'''
	A class representing the charging ports
	'''
	def __init__(self, x,y, visual,tileSize):
		self.x=x;
		self.y=y;
		if visual:
			self.gasStationImage = pg.image.load("./src/img/gasPump.png")
			self.gasStationImage = pg.transform.scale(self.gasStationImage, (int(tileSize * 0.95), int(tileSize * 0.95)))


	def draw(self, screen, tileSize):
		screen.blit(self.gasStationImage, (self.x * tileSize, self.y * tileSize))