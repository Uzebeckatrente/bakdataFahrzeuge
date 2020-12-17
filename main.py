from src import *
np.random.seed(1)

#run-time parameters relevant for visual mode
secondsToPerformMove = 0.1;
secondsForCharge =  0.1;
tileSize = 50



#run-time parameters relevant for both visual and non-visual mode
visual = True
movesUntilRecharge = 10;
numChargingStations = 1;
boardLength = 4;
numCars = 5;
numTasks = 4;
if movesUntilRecharge < boardLength:
	raise ValueError("The length of the board is longer than the number of moves until recharge. This might lead to deadlock if a car"
					 "can not span the board in a single charge and perpetually goes to and from the charging station")

#initialize app, initialize all threads which listen to the kafka topics
logsRoute = "./logs_for_"+str(numCars)+"_cars_AND_"+\
			str(numTasks)+"_tasks_AND_"+str(numChargingStations)+\
			"_chargingStations_AND_"+str(boardLength)+"_boardLen"
app = RoutenSteuerung(numCars,
					  numTasks,numChargingStations,movesUntilRecharge,
					  secondsToPerformMove,secondsForCharge,boardLength, visual,
					  tileSize,logsRoute=logsRoute);
app.initThreads()

#initialize each car, initialize all threads for each car which listen to the kafka topics
print("Generating cars...")
fahrzeuge = app.generateFahrzeuge();
for f in fahrzeuge:
	f.initThreads()
	print("Initialized car ", f.id)
time.sleep(1);

if visual:
	try:
		doVisual(app, fahrzeuge,boardLength,tileSize)
	except Exception as e:
		print(e);
		print("This system is unable to handle graphics - please try again in visual mode")
		exit(-1);
else:
	app.beginSimulation();

#after the simulation is completed, the various threads are joined and the finishing protocols are executed
app.listeningThread.join()
app.finish()
for f in fahrzeuge:
	f.listeningThread.join()
	f.newTaskThread.join();
	f.finish();




