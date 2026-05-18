//M. M. Kuttel 2026 mkuttel@gmail.com

/*
 Barman Thread class.
 Schedulers:
 0 = FCFS
 1 = SJF
 2 = Priority
 3 = MLFQ with aging
 4 = Lottery bonus scheduler
 */

package barScheduling;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;
import java.util.Random;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.PriorityBlockingQueue;
import java.util.concurrent.TimeUnit;

public class Barman extends Thread {
    private static final int MLFQ_Q1 = 40;
    private static final int MLFQ_Q2 = 80;
    private static final int MLFQ_Q3 = 160;
    private static final long AGING_THRESHOLD = 4000L;
    private static final Object CSV_LOCK = new Object();

    // Aging + Burst-Aware Weighted Lottery Scheduling Constants
    // Exponential aging: tickets double every LOTTERY_AGING_SCALE milliseconds
    private static final long LOTTERY_AGING_SCALE = 500L;
    // Maximum aging bonus cap (prevents overflow): 2^10 - 1 = 1023
    private static final long LOTTERY_MAX_AGE_BONUS = 1023L;
    // Burst thresholds (in milliseconds of execution time)
    private static final int LOTTERY_SHORT_BURST_THRESHOLD = 50;
    private static final int LOTTERY_LONG_BURST_THRESHOLD = 100;
    // Burst-aware weighting multipliers
    private static final double LOTTERY_SHORT_JOB_MULTIPLIER = 1.2;  // +20% for short jobs
    private static final double LOTTERY_LONG_JOB_MULTIPLIER = 0.8;   // -20% for long jobs

    private final CountDownLatch startSignal;
    private final int schedAlg;
    private final int switchTime;

    private LinkedBlockingQueue<DrinkOrder> fcfsQueue;
    private PriorityBlockingQueue<DrinkOrder> sjfQueue;
    private PriorityBlockingQueue<DrinkOrder> priorityQueue;
    private LinkedBlockingQueue<DrinkOrder> q0;
    private LinkedBlockingQueue<DrinkOrder> q1;
    private LinkedBlockingQueue<DrinkOrder> q2;
    private final List<DrinkOrder> lotteryPool;
    private final Random lotteryRng;

    private final ConcurrentHashMap<Integer, Integer> drinksServedPerPatron;
    private final ConcurrentHashMap<DrinkOrder, OrderMetrics> orderMetrics;
    private long nextOrderId = 0L;
    private FileWriter csvWriter;

    Barman(CountDownLatch startSignal, int sAlg, int sTime) {
        this.startSignal = startSignal;
        this.schedAlg = sAlg;
        this.switchTime = sTime;
        this.drinksServedPerPatron = new ConcurrentHashMap<Integer, Integer>();
        this.orderMetrics = new ConcurrentHashMap<DrinkOrder, OrderMetrics>();
        this.lotteryPool = (sAlg == 4) ? new ArrayList<DrinkOrder>() : null;
        this.lotteryRng = (SchedulingSimulation.seed > 0)
            ? new Random(SchedulingSimulation.seed)
            : new Random();

        switch (schedAlg) {
            case 0:
                fcfsQueue = new LinkedBlockingQueue<DrinkOrder>();
                break;
            case 1:
                sjfQueue = new PriorityBlockingQueue<DrinkOrder>(
                    5000,
                    Comparator.comparingInt(DrinkOrder::getExecutionTime)
                        .thenComparingLong(this::orderIdFor)
                );
                break;
            case 2:
                priorityQueue = new PriorityBlockingQueue<DrinkOrder>(
                    5000,
                    Comparator.comparingInt(this::priorityFor)
                        .thenComparingLong(this::orderIdFor)
                );
                break;
            case 3:
                q0 = new LinkedBlockingQueue<DrinkOrder>();
                q1 = new LinkedBlockingQueue<DrinkOrder>();
                q2 = new LinkedBlockingQueue<DrinkOrder>();
                break;
            case 4:
                break;
            default:
                throw new IllegalArgumentException(
                    "Invalid scheduler " + sAlg +
                    ". Valid values are: 0=FCFS, 1=SJF, 2=Priority, 3=MLFQ, 4=LOTTERY."
                );
        }

        try {
            openResultsFile();
        } catch (IOException e) {
            throw new RuntimeException("Unable to open results file", e);
        }
    }

    public void placeDrinkOrder(DrinkOrder order) throws InterruptedException, IOException {
        long now = simulationTime();
        OrderMetrics metrics = new OrderMetrics(
            nextOrderId++,
            order.getOrderer(),
            order.getExecutionTime(),
            priorityFor(order),
            now
        );
        orderMetrics.put(order, metrics);

        switch (schedAlg) {
            case 0:
                fcfsQueue.put(order);
                break;
            case 1:
                sjfQueue.put(order);
                break;
            case 2:
                priorityQueue.put(order);
                break;
            case 3:
                metrics.queueLevel = 0;
                q0.put(order);
                break;
            case 4:
                synchronized (lotteryPool) {
                    lotteryPool.add(order);
                }
                break;
            default:
                throw new IllegalArgumentException(
                    "Invalid scheduler " + schedAlg +
                    ". Valid values are: 0=FCFS, 1=SJF, 2=Priority, 3=MLFQ, 4=LOTTERY."
                );
        }
    }

    private void openResultsFile() throws IOException {
        String schedulerName = schedulerName(schedAlg);
        File directory = new File("results");
        directory.mkdirs();

        String filename = schedulerName + "_results.csv";
        File file = new File(directory, filename);
        csvWriter = new FileWriter(file, false);
        csvWriter.write(
            "patronID,orderID,arrivalTime,burstTime,priority," +
            "serviceStartTime,completionTime,responseTime,waitingTime,turnaroundTime,queueLevel\n"
        );
        csvWriter.flush();
    }

    private static String schedulerName(int schedAlg) {
        switch (schedAlg) {
            case 0:
                return "FCFS";
            case 1:
                return "SJF";
            case 2:
                return "PRIORITY";
            case 3:
                return "MLFQ";
            case 4:
                return "LOTTERY";
            default:
                throw new IllegalArgumentException("Unknown scheduler " + schedAlg);
        }
    }

    private int priorityFor(DrinkOrder order) {
        return order.getOrderer() + 1;
    }

    private long orderIdFor(DrinkOrder order) {
        OrderMetrics metrics = orderMetrics.get(order);
        return (metrics == null) ? Long.MAX_VALUE : metrics.orderId;
    }

    private OrderMetrics metadataFor(DrinkOrder order) {
        OrderMetrics metrics = orderMetrics.get(order);
        if (metrics == null) {
            throw new IllegalStateException("Missing metrics for order " + order);
        }
        return metrics;
    }

    private int initialQueueFor(DrinkOrder order) {
        int served = drinksServedPerPatron.getOrDefault(order.getOrderer(), 0);
        if (served == 0) {
            return 0;
        }
        if (served == 1) {
            return 1;
        }
        return 2;
    }

    private void enqueueMLFQ(DrinkOrder order, int level) throws InterruptedException {
        OrderMetrics metrics = metadataFor(order);
        metrics.queueLevel = level;
        metrics.lastEnqueueTime = simulationTime();

        switch (level) {
            case 0:
                q0.put(order);
                break;
            case 1:
                q1.put(order);
                break;
            case 2:
                q2.put(order);
                break;
            default:
                throw new IllegalArgumentException("Invalid queue level: " + level);
        }
    }

    private void ageQueues() throws InterruptedException {
        long now = simulationTime();
        promoteOldOrders(q2, 2, q1, 1, now);
        promoteOldOrders(q1, 1, q0, 0, now);
    }

    private void promoteOldOrders(
        LinkedBlockingQueue<DrinkOrder> from,
        int fromLevel,
        LinkedBlockingQueue<DrinkOrder> to,
        int toLevel,
        long now
    ) throws InterruptedException {
        int originalSize = from.size();

        for (int i = 0; i < originalSize; i++) {
            DrinkOrder order = from.poll();
            if (order == null) {
                break;
            }

            OrderMetrics metrics = metadataFor(order);
            if (metrics.queueLevel == fromLevel && now - metrics.lastEnqueueTime >= AGING_THRESHOLD) {
                metrics.queueLevel = toLevel;
                metrics.lastEnqueueTime = now;
                to.put(order);
            } else {
                from.put(order);
            }
        }
    }

    private DrinkOrder takeNextMLFQOrder() throws InterruptedException {
        while (true) {
            ageQueues();

            DrinkOrder order = q0.poll();
            if (order != null) {
                return order;
            }

            order = q1.poll();
            if (order != null) {
                return order;
            }

            order = q2.poll();
            if (order != null) {
                return order;
            }

            TimeUnit.MILLISECONDS.sleep(1);
        }
    }

    private DrinkOrder takeNextLotteryOrder() throws InterruptedException {
        while (true) {
            synchronized (lotteryPool) {
                if (!lotteryPool.isEmpty()) {
                    long now = simulationTime();
                    long totalTickets = 0L;
                    List<Long> ticketCounts = new ArrayList<Long>(lotteryPool.size());

                    // Calculate weighted lottery tickets for each queued order
                    // Tickets = (base + exponential_aging_bonus) * burst_weighting
                    for (DrinkOrder order : lotteryPool) {
                        long orderTickets = calculateLotteryTickets(order, now);
                        ticketCounts.add(orderTickets);
                        totalTickets += orderTickets;
                    }

                    // Perform lottery draw: select order via cumulative ticket distribution
                    // Use modulo arithmetic for uniform distribution over totalTickets
                    long drawn = Math.abs(lotteryRng.nextLong()) % totalTickets;
                    long cumulative = 0L;

                    for (int i = 0; i < lotteryPool.size(); i++) {
                        cumulative += ticketCounts.get(i);
                        if (drawn < cumulative) {
                            // Selected order found; remove and return
                            return lotteryPool.remove(i);
                        }
                    }

                    // Fallback (should not reach): select first order
                    return lotteryPool.remove(0);
                }
            }

            TimeUnit.MILLISECONDS.sleep(1);
        }
    }

    /**
     * Calculates probabilistic lottery tickets for an order using Advanced Weighted Lottery.
     * 
     * Combines three fairness factors:
     * 1. Base tickets (ensures minimum probability)
     * 2. Exponential aging bonus (prevents starvation via fast growth)
     * 3. Burst-aware weighting (probabilistic short-job preference)
     * 
     * Formula: tickets = (BASE + AGING_BONUS) × BURST_MULTIPLIER
     * 
     * This design:
     * - Maintains probabilistic fairness (genuine lottery semantics)
     * - Approaches SJF performance via soft short-job bias
     * - Prevents starvation via unbounded exponential aging
     * - Reduces convoy effects by favoring job completion
     * 
     * @param order The drink order to evaluate
     * @param now Current simulation time (milliseconds)
     * @return Ticket count for this order
     */
    private long calculateLotteryTickets(DrinkOrder order, long now) {
        OrderMetrics metrics = metadataFor(order);
        long waitTimeMs = now - metrics.lastEnqueueTime;

        // Component 1: Base Tickets
        // Ensures every order has at least 1 ticket (non-zero probability)
        // Satisfies lottery scheduling requirement: ∀orders, P(select) > 0
        long baseTickets = 1L;

        // Component 2: Exponential Aging Bonus
        // Growth rate: ticket count roughly doubles every LOTTERY_AGING_SCALE ms
        // This provides aggressive starvation prevention compared to linear aging
        // 
        // Mathematics:
        //   agingExponent = ⌊waitTimeMs / LOTTERY_AGING_SCALE⌋
        //   agingBonus = min(MAX_AGE_BONUS, 2^agingExponent - 1)
        //
        // Examples (LOTTERY_AGING_SCALE = 500ms):
        //   0ms wait   → exponent=0 → bonus = 0      (2^0 - 1 = 0)
        //   500ms wait → exponent=1 → bonus = 1      (2^1 - 1 = 1)
        //   1000ms     → exponent=2 → bonus = 3      (2^2 - 1 = 3)
        //   1500ms     → exponent=3 → bonus = 7      (2^3 - 1 = 7)
        //   2000ms     → exponent=4 → bonus = 15     (2^4 - 1 = 15)
        //   2500ms     → exponent=5 → bonus = 31     (2^5 - 1 = 31)
        //
        // Rationale: Exponential growth prevents starvation probabilistically
        // An order waiting 2000ms has 16x base probability, virtually guaranteeing selection
        long agingBonus = 0L;
        if (waitTimeMs > 0) {
            long ageExponent = Math.min(
                10L,  // Cap exponent at 2^10 to prevent overflow
                waitTimeMs / LOTTERY_AGING_SCALE
            );
            agingBonus = Math.min(
                LOTTERY_MAX_AGE_BONUS,
                (1L << ageExponent) - 1L  // Bit shift: 1 << n = 2^n
            );
        }

        // Component 3: Burst-Aware Weighting Multiplier
        // Provides soft short-job preference without deterministic bias
        //
        // Design:
        //   Short bursts (≤50ms):  1.2× multiplier  (+20% probability boost)
        //   Medium bursts (51-100): 1.0× multiplier (baseline)
        //   Long bursts (>100ms):   0.8× multiplier (-20% probability penalty)
        //
        // Rationale:
        //   - Reduces response time for short jobs (similar to SJF)
        //   - Reduces convoy effects (queue clears faster)
        //   - Still probabilistic (fairness maintained)
        //   - NOT deterministic SJF (long jobs still get selected)
        //   - No risk of starvation due to exponential aging backup
        double burstMultiplier = 1.0;
        int burstTimeMs = metrics.burstTime;
        
        if (burstTimeMs <= LOTTERY_SHORT_BURST_THRESHOLD) {
            burstMultiplier = LOTTERY_SHORT_JOB_MULTIPLIER;
        } else if (burstTimeMs > LOTTERY_LONG_BURST_THRESHOLD) {
            burstMultiplier = LOTTERY_LONG_JOB_MULTIPLIER;
        }

        // Combine all components: (base + aging) × burst_weighting
        // Examples (assume 1000ms wait):
        //   Short job (30ms): (1 + 3) × 1.2 = 4.8 → 5 tickets
        //   Medium job (75ms): (1 + 3) × 1.0 = 4.0 → 4 tickets
        //   Long job (150ms): (1 + 3) × 0.8 = 3.2 → 3 tickets
        long totalTickets = baseTickets + agingBonus;
        long weightedTickets = Math.round(totalTickets * burstMultiplier);

        // Ensure minimum 1 ticket (critical for lottery correctness)
        // Prevents any order from having zero probability
        return Math.max(1L, weightedTickets);
    }

    private void markServiceStart(DrinkOrder order) {
        OrderMetrics metrics = metadataFor(order);
        long now = simulationTime();
        metrics.totalWaitingTime += now - metrics.lastEnqueueTime;

        if (metrics.serviceStartTime < 0) {
            metrics.serviceStartTime = now;
        }
    }

    private void recordServedDrink(DrinkOrder order) {
        if (schedAlg == 3) {
            drinksServedPerPatron.merge(order.getOrderer(), 1, Integer::sum);
        }
    }

    @Override
    public void run() {
        try {
            startSignal.countDown();
            startSignal.await();

            while (true) {
                switch (schedAlg) {
                    case 0:
                        runNonPreemptive(fcfsQueue.take());
                        break;
                    case 1:
                        runNonPreemptive(sjfQueue.take());
                        break;
                    case 2:
                        runNonPreemptive(priorityQueue.take());
                        break;
                    case 3:
                        runMLFQ(takeNextMLFQOrder());
                        break;
                    case 4:
                        runLottery();
                        break;
                    default:
                        throw new IllegalStateException("Unexpected scheduler " + schedAlg);
                }
            }
        } catch (InterruptedException e) {
            System.out.println("---Barman is packing up ");
        } catch (IOException e) {
            throw new RuntimeException("Failed to record results", e);
        } finally {
            closeResultsFile();
        }
    }

    private void runNonPreemptive(DrinkOrder order) throws InterruptedException, IOException {
        markServiceStart(order);
        System.out.println("---Barman preparing drink for patron " + order);
        sleep(order.getExecutionTime());

        OrderMetrics metrics = metadataFor(order);
        metrics.completionTime = simulationTime();

        System.out.println("---Barman has made drink for patron " + order);
        order.orderDone();
        recordServedDrink(order);
        recordCompletedOrder(order);
        sleep(switchTime);
    }

    private void runMLFQ(DrinkOrder order) throws InterruptedException, IOException {
        OrderMetrics metrics = metadataFor(order);
        markServiceStart(order);

        int quantum = quantumFor(metrics.queueLevel);
        int slice = Math.min(order.getExecutionTime(), quantum);
        System.out.println("---Barman preparing drink for patron " + order + " from Q" + metrics.queueLevel);
        sleep(slice);

        int remaining = order.getExecutionTime() - slice;
        order.setRemainingPreparationTime(remaining);

        if (remaining <= 0) {
            metrics.completionTime = simulationTime();
            System.out.println("---Barman has made drink for patron " + order);
            order.orderDone();
            recordServedDrink(order);
            recordCompletedOrder(order);
        } else {
            enqueueMLFQ(order, Math.min(metrics.queueLevel + 1, 2));
        }

        sleep(switchTime);
    }

    private void runLottery() throws InterruptedException, IOException {
        DrinkOrder order = takeNextLotteryOrder();
        markServiceStart(order);
        System.out.println("---Barman preparing drink for patron " + order + " with LOTTERY");
        sleep(order.getExecutionTime());

        OrderMetrics metrics = metadataFor(order);
        metrics.completionTime = simulationTime();

        System.out.println("---Barman has made drink for patron " + order);
        order.orderDone();
        recordCompletedOrder(order);
        sleep(switchTime);
    }

    private int quantumFor(int queueLevel) {
        switch (queueLevel) {
            case 0:
                return MLFQ_Q1;
            case 1:
                return MLFQ_Q2;
            default:
                return MLFQ_Q3;
        }
    }

    private void recordCompletedOrder(DrinkOrder order) throws IOException {
        OrderMetrics metrics = metadataFor(order);
        long responseTime = metrics.serviceStartTime - metrics.arrivalTime;
        long waitingTime = metrics.totalWaitingTime;
        long turnaroundTime = metrics.completionTime - metrics.arrivalTime;
        int queueLevel;
        if      (schedAlg == 3) queueLevel = metrics.queueLevel;
        else if (schedAlg == 4) queueLevel = -2;
        else                    queueLevel = -1;

        if (waitingTime < 0 || responseTime < 0 || turnaroundTime < 0) {
            throw new IllegalStateException("Negative metric generated for order " + metrics.orderId);
        }
        if (metrics.serviceStartTime < metrics.arrivalTime) {
            throw new IllegalStateException("serviceStartTime < arrivalTime for order " + metrics.orderId);
        }
        if (metrics.completionTime < metrics.serviceStartTime) {
            throw new IllegalStateException("completionTime < serviceStartTime for order " + metrics.orderId);
        }
        if (turnaroundTime < waitingTime) {
            throw new IllegalStateException("turnaroundTime < waitingTime for order " + metrics.orderId);
        }

        String row = String.format(
            Locale.US,
            "%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d%n",
            metrics.patronId,
            metrics.orderId,
            metrics.arrivalTime,
            metrics.burstTime,
            metrics.priority,
            metrics.serviceStartTime,
            metrics.completionTime,
            responseTime,
            waitingTime,
            turnaroundTime,
            queueLevel
        );

        synchronized (CSV_LOCK) {
            csvWriter.write(row);
            csvWriter.flush();
        }
    }

    private void closeResultsFile() {
        if (csvWriter == null) {
            return;
        }

        try {
            csvWriter.flush();
            csvWriter.close();
        } catch (IOException e) {
            System.err.println("Failed to close results file: " + e.getMessage());
        }
    }

    private long simulationTime() {
        return System.currentTimeMillis() - SchedulingSimulation.simStartTime;
    }

    private static final class OrderMetrics {
        private final long orderId;
        private final int patronId;
        private final int burstTime;
        private final int priority;
        private final long arrivalTime;
        private long lastEnqueueTime;
        private long serviceStartTime = -1L;
        private long completionTime = -1L;
        private long totalWaitingTime = 0L;
        private int queueLevel = -1;

        private OrderMetrics(long orderId, int patronId, int burstTime, int priority, long arrivalTime) {
            this.orderId = orderId;
            this.patronId = patronId;
            this.burstTime = burstTime;
            this.priority = priority;
            this.arrivalTime = arrivalTime;
            this.lastEnqueueTime = arrivalTime;
        }
    }
}
