@echo off
setlocal EnableDelayedExpansion

REM Configuration
set "PATRONS=5 10 20 30 50"
set "ALGORITHMS=0 1 2 3"
set "SEEDS=42 123 999 2024 31415"
set "SWITCH_TIME=0"
set "RESULTS_DIR=results"

if not exist "%RESULTS_DIR%" mkdir "%RESULTS_DIR%"

echo Compiling...
javac -d out src\barScheduling\*.java 2>nul
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

            echo Running: patrons=%%n alg=!ALG_LABEL! seed=%%seed

            java -cp out barScheduling.SchedulingSimulation %%n %%alg %SWITCH_TIME% %%seed > "%RESULTS_DIR%!ALG_LABEL!_n%%n_s%%seed!.log" 2>&1

            set "SRC=%RESULTS_DIR%!ALG_LABEL!_results.csv"
            set "DST=%RESULTS_DIR%!ALG_LABEL!_n%%n_s%%seed!.csv"
            if exist "!SRC!" move /Y "!SRC!" "!DST!" >nul
        )
    )
)

echo All experiments complete. Results in: %RESULTS_DIR%
endlocal
