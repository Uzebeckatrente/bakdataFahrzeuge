import itertools
import random
import math

from .RoutenSteuerung import *;
random.seed(1771);



def arrow(screen, lcolor, tricolor, start, end, trirad, thickness=2):  # adapted from stackoverflow user Alec Alameddine
	rad = 180;
	pg.draw.line(screen, lcolor, start, end, thickness)
	rotation = (math.atan2(start[1] - end[1], end[0] - start[0])) + math.pi / 2
	pg.draw.polygon(screen, tricolor, ((end[0] + trirad * 4 * math.sin(rotation),
										end[1] + trirad * 4 * math.cos(rotation)),
									   (end[0] + trirad * 4 * math.sin(rotation - 120 * rad),
										end[1] + trirad * 4 * math.cos(rotation - 120 * rad)),
									   (end[0] + trirad * 4 * math.sin(rotation + 120 * rad),
										end[1] + trirad * 4 * math.cos(rotation + 120 * rad))))

def doVisual(app, numTilesSide, tileSize):
	'''
	Basic pygame chess-board boilerplate, updates every 60th of a second
	:param app:
	:param numTilesSide:
	:param tileSize:
	:return:
	'''

	visual = True;
	try:

		if visual:

			pg.init()

			BLACK = pg.Color(240, 240, 230, 50)
			WHITE = pg.Color(40, 40, 40, 50)

			screen = pg.display.set_mode((tileSize * numTilesSide, tileSize * numTilesSide))
			clock = pg.time.Clock()
			colors = itertools.cycle((WHITE, BLACK))
			background = pg.Surface((tileSize * numTilesSide, tileSize * numTilesSide))
			for y in range(0, numTilesSide):
				for x in range(0, numTilesSide):
					rect = (x * tileSize, y * tileSize, tileSize, tileSize)
					pg.draw.rect(background, next(colors), rect)
				next(colors)
	except:
		pass


	def wasSpacePressed():
		keys = pg.key.get_pressed()
		if keys[pg.K_SPACE]:
			return True;
		return False;


	spaceCounter = 0
	game_exit = False
	simulationStarted = False
	while not game_exit:
		if visual:
			for event in pg.event.get():
				if event.type == pg.QUIT:
					game_exit = True
		if not simulationStarted:
			if wasSpacePressed() and spaceCounter == 0:
				app.beginSimulation()
				simulationStarted = True



		if visual:
			screen.fill((60, 70, 90))
			screen.blit(background, (0, 0))

			app.draw(screen, tileSize);
			pg.display.update()

			clock.tick(60)

	pg.quit()