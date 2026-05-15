@echo off
setlocal EnableDelayedExpansion

REM Configuration
set "PATRONS=10 20 40 60 100"
set "ALGORITHMS=0 1 2 3 4"
set "SEEDS=42 123 999"
set "SWITCH_TIME=0"
set "RESULTS_DIR=results"
set "BUILD_DIR=build_output"

if not exist "%RESULTS_DIR%" mkdir "%RESULTS_DIR%"
if not exist "%RESULTS_DIR%\fcfs" mkdir "%RESULTS_DIR%\fcfs"
if not exist "%RESULTS_DIR%\sjf" mkdir "%RESULTS_DIR%\sjf"
if not exist "%RESULTS_DIR%\priority" mkdir "%RESULTS_DIR%\priority"
if not exist "%RESULTS_DIR%\mlfq" mkdir "%RESULTS_DIR%\mlfq"
if not exist "%RESULTS_DIR%\hrrn" mkdir "%RESULTS_DIR%\hrrn"
if not exist "%BUILD_DIR%" mkdir "%BUILD_DIR%"

echo Compiling...
javac -d "%BUILD_DIR%" src\barScheduling\*.java 2>nul
if errorlevel 1 (
    echo Compilation failed.
    exit /b 1
)

for %%n in (%PATRONS%) do (
    for %%seed in (%SEEDS%) do (
        for %%alg in (%ALGORITHMS%) do (
            if %%alg==0 set "ALG_LABEL=FCFS"
            if %%alg==1 set "ALG_LABEL=SJF"
            if %%alg==2 set "ALG_LABEL=PRIORITY"
            if %%alg==3 set "ALG_LABEL=MLFQ"
            if %%alg==4 set "ALG_LABEL=HRRN"
            if %%alg==0 set "ALG_DIR=fcfs"
            if %%alg==1 set "ALG_DIR=sjf"
            if %%alg==2 set "ALG_DIR=priority"
            if %%alg==3 set "ALG_DIR=mlfq"
            if %%alg==4 set "ALG_DIR=hrrn"

            echo Running: patrons=%%n alg=!ALG_LABEL! seed=%%seed

            java -cp "%BUILD_DIR%" barScheduling.SchedulingSimulation %%n %%alg %SWITCH_TIME% %%seed > "%RESULTS_DIR%\!ALG_LABEL!_n%%n_s%%seed!.log" 2>&1

            set "DST=%RESULTS_DIR%\!ALG_DIR!\!ALG_LABEL!_n%%n_s%%seed!.csv"
            if not exist "!DST!" (
                echo ERROR: expected results file not found: !DST!
                exit /b 1
            )
        )
    )
)

echo All experiments complete. Results in: %RESULTS_DIR%
endlocal
