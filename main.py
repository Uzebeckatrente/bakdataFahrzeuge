from src import *

secondsToPerformMove = 0.1;
secondsForCharge =  1;
movesUntilRecharge = 10;
numChargingStations = 1;
boardLength = 10;
tileSize = 50

visual = False
np.random.seed(1)

numCars = 100;
numTasks = 25;

for numCars in [100]:
	for numTasks in [200]:
		app = RoutenSteuerung(numCars,numTasks,numChargingStations,movesUntilRecharge,secondsToPerformMove,secondsForCharge,boardLength, visual, tileSize,logsRoute="./logs_for_"+str(numCars)+"_cars_AND_"+str(numTasks)+"_tasks_AND_"+str(numChargingStations)+"_chargingStations_AND_"+str(boardLength)+"_boardLen");
		app.initThreads()
		fahrzeuge = app.generateFahrzeuge();#only used for GUI
		for f in fahrzeuge:
			f.initThreads()
			print("Initialized car ", f.id)
		time.sleep(1);

		if visual:
			doVisual(app, fahrzeuge,boardLength,tileSize)
		else:
			app.beginSimulation();
		app.listeningThread.join()
		app.lowBatteryListeningThread.join()
		app.finish()
		for f in fahrzeuge:
			f.listeningThread.join()
			f.newTaskThread.join();
			f.finish();




