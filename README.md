CPU Scheduling Simulation

## Overview

This project implements and evaluates multiple CPU scheduling algorithms through a concurrent Java simulation based on the **"Allegra the Barman"** scheduling analogy.

In the simulation:

- **Patrons** represent processes
- **Drink orders** represent CPU bursts
- **The barman** represents the CPU scheduler
- **Serving drinks** represents process execution

The project compares the behavior and performance of several scheduling strategies under identical workloads, allowing analysis of scheduling trade-offs such as fairness, throughput, waiting time, response time, and turnaround time.

---

## Scheduling Algorithms

### First Come First Served (FCFS)

Processes are executed in the order they arrive.

**Characteristics**
- Simple and predictable
- Low scheduling overhead
- Susceptible to the convoy effect
- Can produce poor average waiting times

---

### Shortest Job First (SJF)

Processes with the shortest burst time are selected first.

**Characteristics**
- Minimizes average waiting time
- Excellent response-time performance
- Can starve long-running processes
- Requires burst-length knowledge

---

### Priority Scheduling

Processes are executed according to assigned priority levels.

**Characteristics**
- Prioritizes important workloads
- Flexible scheduling policy
- Risk of starvation for low-priority processes

---

### Aging + Burst-Aware Weighted Lottery Scheduling

A custom probabilistic scheduling algorithm developed for this project.

#### Key Features

- Lottery-based process selection
- Dynamic ticket allocation
- Waiting-time aging to reduce starvation
- Burst-aware weighting to favor shorter jobs
- Preserves probabilistic fairness while improving responsiveness

#### Ticket Formula Concept

```text
Tickets = Base Tickets + Aging Bonus + Short Job Bonus
```

This approach combines the fairness benefits of Lottery Scheduling with performance characteristics closer to SJF, while ensuring all processes retain a non-zero probability of execution.

---

## Performance Metrics

The following metrics are collected and analyzed:

- Average Waiting Time
- Average Response Time
- Average Turnaround Time
- Throughput
- Fairness Characteristics
- Starvation Risk

Results are visualized using plots generated from simulation output data.

---

## Project Structure

```text
src/
├── Barman.java
├── Patron.java
├── DrinkOrder.java
├── SchedulingSimulation.java

results/
├── csv/
├── plots/
└── reports/
```

---

## Experimental Evaluation

Each scheduling algorithm is executed using identical workloads and arrival patterns.

Experiments compare:

- FCFS vs SJF
- FCFS vs Priority
- FCFS vs Lottery
- Lottery vs Aging + Burst-Aware Weighted Lottery
- Aging + Burst-Aware Weighted Lottery vs SJF

Generated visualizations include:

- Waiting Time Comparisons
- Response Time Comparisons
- Turnaround Time Comparisons
- Throughput Analysis
- Box Plots
- Error-Bar Charts

---

## Design Goals

The custom scheduler was designed to:

- Improve average waiting time
- Improve response time
- Reduce convoy effects
- Maintain fairness
- Prevent starvation
- Preserve non-preemptive execution
- Remain consistent with classical Lottery Scheduling principles

---

## Key Concepts Demonstrated

- Process Scheduling
- CPU Resource Allocation
- Concurrency and Synchronization
- Scheduling Fairness
- Starvation Prevention
- Probabilistic Scheduling
- Performance Evaluation

---
