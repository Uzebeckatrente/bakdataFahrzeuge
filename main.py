from src import *

secondsToPerformMove = 1;
secondsForCharge = 1;
numCars = 30;
numTasks = 100;
movesUntilRecharge = 10;
numChargingStations = 5;
boardLength = 20;
tileSize = 50
# try:
# 	numCars = int(input("NumFahrzeuge: "));
# except:
# 	numCars = 20;
# try:
# 	numTasks = int(input("NumTasks: "))
# except:
# 	numTasks = 5;

# visual = input("Visual? type \"no\" for no, anything else for yes: ") != "no"
visual = True


app = RoutenSteuerung(numCars,numTasks,numChargingStations,movesUntilRecharge,secondsToPerformMove,secondsForCharge,boardLength, visual, tileSize);
if visual:
	doVisual(app,boardLength,tileSize)
else:
	app.beginSimulation();



