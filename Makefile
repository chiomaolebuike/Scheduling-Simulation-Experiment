JAVAC = javac
JAVA = java
SRC = src/barScheduling/*.java
BIN = build_output
MAIN = barScheduling.SchedulingSimulation

$(BIN):
	mkdir -p $(BIN)

compile: $(BIN)
	$(JAVAC) -d $(BIN) $(SRC)

run: compile
	$(JAVA) -cp $(BIN) $(MAIN) $(ARGS)

experiments:
	cmd /c run_experiments.bat

clean:
	rm -rf $(BIN)
	rm -rf results
