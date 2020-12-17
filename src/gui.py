import itertools
import random
import math

from .RoutenSteuerung import *;
random.seed(1771);



def arrow(screen, lcolor, tricolor, start, end, trirad, thickness=2):
	'''
	Draws an arrow of a particular color from one coordinate to another
	adapted from stackoverflow user Alec Alameddine
	:param screen:
	:param lcolor:
	:param tricolor:
	:param start:
	:param end:
	:param trirad:
	:param thickness:
	:return:
	'''
	rad = 180;
	pg.draw.line(screen, lcolor, start, end, thickness)
	rotation = (math.atan2(start[1] - end[1], end[0] - start[0])) + math.pi / 2
	pg.draw.polygon(screen, tricolor, ((end[0] + trirad * 4 * math.sin(rotation),
										end[1] + trirad * 4 * math.cos(rotation)),
									   (end[0] + trirad * 4 * math.sin(rotation - 120 * rad),
										end[1] + trirad * 4 * math.cos(rotation - 120 * rad)),
									   (end[0] + trirad * 4 * math.sin(rotation + 120 * rad),
										end[1] + trirad * 4 * math.cos(rotation + 120 * rad))))

def doVisual(app, fahrzeuge, numTilesSide, tileSize):
	'''
	Basic pygame chess-board boilerplate, updates every 60th of a second
	:param app: RoutenSteuerung instance
	:param numTilesSide: size of board
	:param tileSize: how big each tile is
	:return:
	'''

	counterDown = 60;
	try:


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
		raise Exception("Something went wrong in the initialization of pygame... This is unprecedented")



	def wasSpacePressed():
		'''
		Determine whether spaced was pressed
		:return:
		'''
		keys = pg.key.get_pressed()
		if keys[pg.K_SPACE]:
			return True;
		return False;


	#Functionality for quitting if simulation is finished or the window is x'ed out of
	spaceCounter = 0
	game_exit = False
	simulationStarted = False
	while not game_exit and counterDown > 0:
		for event in pg.event.get():
			if event.type == pg.QUIT:
				game_exit = True
		if not simulationStarted:
			if wasSpacePressed() and spaceCounter == 0:
				app.beginSimulation()
				simulationStarted = True

		#app persists for 1 second after simulation is done
		if app.finished:
			counterDown += -1;

		#draw background
		screen.fill((60, 70, 90))
		screen.blit(background, (0, 0))
		app.draw(screen, tileSize);

		#draw cars
		for fz in fahrzeuge:
			fz.draw(screen, tileSize)
			#draw arrows from car to target stop/start
			if fz.id in app.fzIdToTask and app.fzIdToTask[fz.id] != None:
				if not app.fzIdToTask[fz.id].onHoldBecauseOfBattery:
					targetX = app.fzIdToTask[fz.id].stopX
					targetY = app.fzIdToTask[fz.id].stopY;
					if not app.fzIdToTask[fz.id].initialPositionReached:
						taskStartX = app.fzIdToTask[fz.id].startX
						taskStartY = app.fzIdToTask[fz.id].startY;
						arrow(screen, (220, 123, 40), (0, 255, 0), ((fz.x + 0.5) * tileSize, (fz.y + 0.5) * tileSize), ((taskStartX + 0.5) * tileSize, (taskStartY + 0.5) * tileSize), 2);
						arrow(screen, (220, 123, 40), (0, 255, 0), ((taskStartX + 0.5) * tileSize, (taskStartY + 0.5) * tileSize), ((targetX + 0.5) * tileSize, (targetY + 0.5) * tileSize), 2);
					else:
						arrow(screen, (220, 123, 40), (0, 255, 0), ((fz.x + 0.5) * tileSize, (fz.y + 0.5) * tileSize), ((targetX + 0.5) * tileSize, (targetY + 0.5) * tileSize), 2);

				else:
					nearestStation = app.findNearestChargingPort(fz.x, fz.y);
					arrow(screen, (255, 0, 0), (255, 0, 30), ((fz.x + 0.5) * tileSize, (fz.y + 0.5) * tileSize), ((nearestStation.x + 0.5) * tileSize, (nearestStation.y + 0.5) * tileSize), 2);

		pg.display.update()
		clock.tick(60)

	pg.quit()