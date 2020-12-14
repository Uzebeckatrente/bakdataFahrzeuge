from src import *

secondsToPerformMove = 1;
secondsForCharge = 1;
numCars = 5;
numTasks = 10;
movesUntilRecharge = 10;
numChargingStations = 5;
boardLength = 10;
tileSize = 40
# try:
# 	numCars = int(input("NumFahrzeuge: "));
# except:
# 	numCars = 20;
# try:
# 	numTasks = int(input("NumTasks: "))
# except:
# 	numTasks = 5;

# visual = input("Visual? type \"no\" for no, anything else for yes: ") != "no"
visual = False


app = RoutenSteuerung(numCars,numTasks,numChargingStations,movesUntilRecharge,secondsToPerformMove,secondsForCharge,boardLength, visual, tileSize);
if visual:
	doVisual(app,boardLength,tileSize)
else:
	app.beginSimulation();



