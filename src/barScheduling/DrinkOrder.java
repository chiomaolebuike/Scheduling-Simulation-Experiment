//M. M. Kuttel 2026 mkuttel@gmail.com
//DrinkOrder.java - represents a single order of a drink by a patron
//YOU MAY NOT ALTER THIS CLASS

package barScheduling;

import java.util.Random;
import java.util.concurrent.atomic.AtomicBoolean;

public class DrinkOrder {

    // preparation time for drink assumes milliseconds are seconds
    // otherwise simulation would be realtime!
    public enum Drink {
        Tequila("Tequila shot", 20, 3),
        Vodka("Vodka shot", 20, 3),
        BottledBeer("Beer", 25, 100),
        Cider("Cider", 25, 100),
        WineRed("Red Wine", 25, 150),
        WineWhite("White Wine", 25, 150),
        GinAndTonic("Gin and Tonic", 40, 110),
        DraftBeer("Draft Beer", 50, 100),
        Martini("Martini", 60, 110),
        Cosmopolitan("Cosmopolitan", 65, 50),
        BloodyMary("Bloody Mary", 70, 150),
        Margarita("Margarita", 75, 80),
        Mojito("Mojito", 75, 110),
        PinaColada("Pina Colada", 100, 120),
        B52("B52", 200, 10);

        private final String name;
        private final int preparationTime;
        private final int imbibingTime;

        Drink(String name, int preparationTime, int drinkingTime) {
            this.name = name;
            this.preparationTime = preparationTime;
            this.imbibingTime = drinkingTime;
        }

        public String getName() {
            return name;
        }

        public int getPreparationTime() {
            return preparationTime;
        }

        public int getImbibingTime() {
            return imbibingTime;
        }

        @Override
        public String toString() {
            return name;
        }
    }

    private final Drink drink;
    private int prepTime;
    private final int orderer;

    public static Random random = new Random();
    private final AtomicBoolean orderComplete;

    public DrinkOrder(int patron) {
        this(patron, random.nextInt(Drink.values().length));
    }

    public DrinkOrder(int patron, int i) {
        Drink[] drinks = Drink.values();
        drink = drinks[i];
        orderComplete = new AtomicBoolean(false);
        orderer = patron;
        prepTime = drink.getPreparationTime();
    }

    public int getOrderer() {
        return orderer;
    }

    public String getDrinkName() {
        return drink.getName();
    }

    public int getExecutionTime() {
        return prepTime;
    }

    public int getImbibingTime() {
        return drink.getImbibingTime();
    }

    public void setRemainingPreparationTime(int timeLeft) {
        prepTime = timeLeft;
    }

    public static Drink getRandomDrink() {
        Drink[] drinks = Drink.values();
        int randomIndex = random.nextInt(drinks.length);
        return drinks[randomIndex];
    }

    public synchronized void orderDone() {
        orderComplete.set(true);
        this.notifyAll();
    }

    public synchronized void waitForOrder() throws InterruptedException {
        while (!orderComplete.get()) {
            this.wait();
        }
    }

    @Override
    public String toString() {
        return orderer + ": " + drink.getName();
    }
}
