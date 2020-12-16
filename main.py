from src import *

secondsToPerformMove = 0.1;
secondsForCharge =  1;
movesUntilRecharge = 10;
numChargingStations = 1;
boardLength = 10;
tileSize = 50

visual = False
np.random.seed(1)

numCars = 15;
numTasks = 31;

#initialize app, initialize all threads which listen to the kafka topics
app = RoutenSteuerung(numCars,numTasks,numChargingStations,movesUntilRecharge,secondsToPerformMove,secondsForCharge,boardLength, visual, tileSize,logsRoute="./logs_for_"+str(numCars)+"_cars_AND_"+str(numTasks)+"_tasks_AND_"+str(numChargingStations)+"_chargingStations_AND_"+str(boardLength)+"_boardLen");
app.initThreads()

#initialize each car, initialize all threads for each car which listen to the kafka topics
fahrzeuge = app.generateFahrzeuge();
for f in fahrzeuge:
	f.initThreads()
	print("Initialized car ", f.id)
time.sleep(1);

if visual:
	doVisual(app, fahrzeuge,boardLength,tileSize)
else:
	app.beginSimulation();

#after the simulation is completed, the various threads are joined and the finishing protocols are executed
app.listeningThread.join()
app.lowBatteryListeningThread.join()
app.finish()
for f in fahrzeuge:
	f.listeningThread.join()
	f.newTaskThread.join();
	f.finish();




