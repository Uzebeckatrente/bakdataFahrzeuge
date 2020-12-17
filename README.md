# bakdataFahrzeuge


To run this project, simply navigate to the root directory and execute the command python3 main.py from your terminal

## Non-visual mode
The non-visual mode fulfils all of the functionalty of the visual mode, without the visual aspect. Its interpretation relies solely on console and log-file output. This is structured in the following manner:

1: When the script is started (as previously described), first the Kafka Streams app is initialized with the number of cars, tasks, charging stations, board size, etc. The number of cars are then initialized accordingly, each with a unique id. Furthermore, each car has its own log-file, as does the streaming app (this is entitled main.txt). These can be found at ./logs_for_{numCars}_cars_AND_{numTasks}_tasks_AND_{numChargingStations}_chargingStations_AND_{boardLen}_boardLen/logForCar-{id}.txt for the id of that car. For example, logs_for_15_cars_AND_31_tasks_AND_1_chargingStations_AND_10_boardLen is for a run with 15 cars, 31 tasks, 1 charging station, and a board length of 10. When a car has been successfully initialized, it logs "Car with id {id} intialized". It then begins listening on the "nextPositions" Kafka topic.

1a: After the initialization of each car, a task is assigned to that car (assuming that there are more tasks than cars). That task starts at a random location and ends at a different random location. This event is logged.

2: While the car has not yet reached the starting location for the task:

  2a: The app sends the next square it needs to go to into the Kafka Topic "nextPositions", marking the message with the car's id
  
  2b: The car listens to all incoming messages on "nextPositions"; when it receives a message with its assigned id, it moves to that square and sends a message back to the app requesting its next square. Each transaction is logged.
  
3: When the car reaches the initial square, 2 (above) repeats itself, except for the ending square rather than beginning square.

4: When the car reaches the final destination, this is logged. If there are remaining tasks to be done, then the app creates a new task, starting at a random location and ending at a different random location. This event is logged. 2 (above) is repeated.

*At any time if the car has low battery, then it sends a message to the criticalBatteryTopic topic. This is logged. The app recceives this message, and rather than direct it towards the next target according to its task, it directs it towards the nearest charging station. Once it arrives, it sends a message to the car to charge. This is logged. Then it resumes directing the car to its assigned target.

All communication between the Streaming App and each car happens via Kafka Topics. There is no direct communication between the Stream App object and the Fahrzeug objects.

## Visual mode
The visual mode provides a visual representation of the simulation. Represented are cars, charging stations, and their targets. The target of each car is indicated by a red x, marking the spot to which it must travel. There is an arrow drawn from each car to its respective target (if it currently has one). Once the visual mode has loaded, you must press the space bar for it to begin running.

The visual mode creates the same log files as does the non-visual mode.

## Documentation of Code

There are two classes which are of primary importance. RoutenSteuerung, and Fahrzeug

Fahrzeug is the class represents each car. There are {numCars} instances of it in each simulation. Each Fahrzeug, upon initialization, listens to the Kafka topic "newTasks" as well as "nextPositions". In newTasks, it is informed when it begins a new task (although this is not strictly necessary, as it is told every move by the streaming app). In nextPositions, it is informed where is shall move next - when it performs this move, it sends a message to the topic "updateAppWithCurrentPositions". When its battery is running low, it sends a message to the topic "criticalBatteryTopic". Eventually, when all tasks have been exhausted, it finishes.

RoutenSteuerung is the Streaming App class. There is a single instance of this per simulation. Each Fahrzeug communicates with it - thus, it is a bit of a bottleneck. If this application were to be made scalable, it would make sense to distribute some of the load borne by RoutenSteuerung - perhaps there could be several worker nodes which all synchronize periodically with a central unit. It listens to the topics "updateAppWithCurrentPositions" and "criticalBatteryTopic". In the former, it consumes messages produced by Fahrzeuge which tell the central unit where there have gone, such that it can tell them their next square to go. In the latter, it consumes messages produced by Fahrzeuge which tell the central unit that they have low battery, so that it can direct them towards the nearest charging station. It produces responses to these messages into the channels "newTasks" and "nextPositions". The former tells the Fahrzeuge when they are beginning a new task, and the latter tells them which position they must next go to.

There is a persistent bug in this code, which manifests itself for large values of {numCars} and {numTasks} in non-visual mode. This is because there is a single topic being shared by many different cars; in non-visual mode, each move is executed extremely quickly, which can lead to messages getting crossed up, and ultimately deadlock. It is hard to determine exactly when this happens - runs with the same hyperparameters will alternately deadlock or not. One solution for this would be to create a topic for the updates of each individual car, rather than sharing a topic, according to the present architecture. This would afford better scalability, and would make it less likely for messages to become eroded.

Synchronicity is maintained via task and Fahrzeug id's, which are passed in every message in topic "updateAppWithCurrentPositions".


## Sample log-files

In this repository, there are several samples of logs created by runs of the code with various different parameters. For example, the log-files in "./logs_for_100_cars_AND_30_tasks_AND_1_chargingStations_AND_10_boardLen" contain log files for each of the 100 Fahrzeuge involved, as well as a main log-file, from the perspective of the streaming app. Running a new simulation with the same parameters will overwrite any previous logs.

## Dependencies

It has several dependencies; these are listed in requirements.txt

## Runtime Parameters

There are several run-time parameters which you may tweak in the header of main.py. Most important are:

numCars: the number of cars in the simulation
numTasks: the number of tasks which they must accomplish
movesUntilRecharge: the number of moves they can make before they need to go and find the nearest charging port
boardLength: the number of squares on each side of the board
visual: whether you would like to include the visual pygame simulation

![Screenshot from simulation](./src/img/sim.png)
