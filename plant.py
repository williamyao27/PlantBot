# ==================================================================================================
# Contains all the behaviors for the PlantBot to run the plant minigame in the server.
# ==================================================================================================
import discord
from discord.ext import tasks
import pickle
import random

# Constants
FRUIT_MARKET = {
    ":apple:": 1.0,
    ":green_apple:": 1.1,
    ":banana:": 0.5,
    ":tangerine:": 1.2,
    ":grapes:": 4.0,
    ":strawberry:": 0.4,
    ":avocado:": 3.0,
    ":coconut:": 5.0,
    ":cheese:": 6.0,
    ":cookie:": 1.5,
    ":fish:": 7.5,
    ":gem:": 50.0,
}


class PlantManager:
    """Creates and manages the server plant.
    """
    def __init__(self, gid):
        """Initialize the PlantManager for this server.
        """
        # Store gid for this manager so it can be pickled to the proper file
        self.__gid = gid

        # Find and load this server's plant information from pickle
        try:
            self.__load()
        except FileNotFoundError:
            # If no pickle file is found for this server, then initialize a new plant
            self.__reset_plant()
            self.__reset_economy()

        # Start tick cycles
        self.tick.start()

    def __reset_plant(self) -> None:
        """Initialize the stats of the plant for this PlantManager.
        """
        self.__name = "Plant"
        self.__hydration = 100.
        self.__happiness = 50.
        self.__alive = True
        self.__death_cause = None
        self.__fruits = []

    def __reset_economy(self) -> None:
        """Initialize the economy for this PlantManager.
        """
        self.__economy = {}
        self.__inventories = {}
        self.__assets = {}
        self.__market = FRUIT_MARKET.copy()

    def __mood(self) -> str:
        """Return a string describing this plant's mood based on its happiness level.
        """
        if self.__happiness <= 1:
            return "Depressed"
        elif 0 < self.__happiness <= 20:
            return "Sad"
        elif 20 < self.__happiness <= 40:
            return "Wilting"
        elif 40 < self.__happiness <= 60:
            return "Mediocre"
        elif 60 < self.__happiness <= 80:
            return "Happy"
        elif 80 < self.__happiness <= 100:
            return "Joyous"

    def __adjust_market(self) -> None:
        """Adjust the price market for all fruits in this server.
        """
        for fruit in self.__market:
            new_price = self.__market[fruit]

            # Push price back to normal
            if new_price < FRUIT_MARKET[fruit]:
                new_price += 0.1

            # Fluctuation with general inflation
            new_price *= random.uniform(0.97, 1.05)

            self.__market[fruit] = new_price

    def __add_wealth(self, uid, amount) -> None:
        """Add the given amount of money to the account of the user with uid.
        """
        # Initialize account if needed
        if uid not in self.__economy:
            self.__economy[uid] = 0.

        # Add amount
        self.__economy[uid] += amount

    def __get_inventory(self, aid) -> list:
        """Return the inventory for the user with aid. If no inventory exists for the user yet,
        create and return an empty one.
        """
        # Create inventory if needed
        if aid not in self.__inventories:
            self.__inventories[aid] = []

        return self.__inventories[aid]

    async def __summary(self, ctx) -> None:
        """Send summary of statistics for this server's plant.
        """
        if self.__alive:
            # Generate fruit string first
            fruit_str = " ".join(self.__fruits)

            # Summary of plant statistics and available fruit
            await ctx.send(":potted_plant:\n")
            await ctx.send(f"*{self.__name}*\n"
                           f"**Hydration:** {round(self.__hydration, 2)}%\n"
                           f"**Happiness:** {round(self.__happiness, 2)}% ({self.__mood()})\n"
                           f"**Fruits:** {fruit_str if fruit_str != '' else 'None'}")
        else:
            # Death overview
            await ctx.send(":skull:\n")
            await ctx.send(f"*{self.__name}*\n"
                           f"**Plant died due to {self.__death_cause}**.")

    async def __respawn(self, ctx) -> None:
        """Respawn this server's plant.
        """
        if self.__alive:
            await ctx.send(f"Cannot respawn the plant because {self.__name} is still alive.")
        else:
            self.__reset_plant()
            await ctx.send("Respawned the plant.")

    async def __set_name(self, ctx, *args) -> None:
        """Set name for this server's plant and send notification.
        """
        if len(args) >= 2:
            old_name = self.__name
            self.__name = " ".join(args[1:])  # Combine all remaining arguments into name
            await ctx.send(f"{old_name} renamed to {self.__name}.")
        else:
            # INVALID USAGE
            await ctx.send("`$plant name <name>`")

    async def __water(self, ctx) -> None:
        """Increment hydration for this server's plant and send notification.
        """
        if self.__alive:
            self.__hydration += 10.
            await ctx.send(f"Thanks for watering {self.__name}! "
                           f"Its hydration is {round(self.__hydration, 2)}%.")
        else:
            await ctx.send(f"You cannot water {self.__name} because it died.")

    async def __pet(self, ctx) -> None:
        """Increment happiness for this server's plant and send notification.
        """
        if self.__alive:
            self.__happiness = min(self.__happiness + 10., 100.)
            await ctx.send(f"Thanks for petting {self.__name}! "
                           f"Its happiness is {round(self.__happiness, 2)}%.")
        else:
            await ctx.send(f"You cannot pet {self.__name} because it died.")

    async def __harvest(self, ctx) -> None:
        """Harvest all fruit from the plant to the caller's inventory and send notification showing
        what fruit were harvested.
        """
        aid = ctx.author.id
        inventory = self.__get_inventory(aid)

        if len(self.__fruits) > 0:
            # Add all fruits to harvester inventory
            inventory.extend(self.__fruits)
            await ctx.send(f"You harvested the plant, receiving: {' '.join(self.__fruits)}")

            # Reset fruits on plant
            self.__fruits.clear()
        else:
            # No fruit
            await ctx.send(f"There are no fruit to harvest.")

    async def __check_inventory(self, ctx) -> None:
        """Send a message displaying the caller's inventory.
        """
        aid = ctx.author.id
        inventory = self.__get_inventory(aid)

        # Send message
        if len(inventory) > 0:
            await ctx.send(f"Your inventory: {' '.join(inventory)}")
        else:
            await ctx.send(f"Your inventory is empty.")

    async def __check_wealth(self, ctx, *args) -> None:
        """Send a message indicating either the caller or all server membes' wealth.
        """
        aid = ctx.author.id

        # Initialize account if needed
        if aid not in self.__economy:
            self.__economy[aid] = 0.

        # Option 1: Report all members' wealth
        if len(args) >= 2:
            if args[1] == "all":
                str_so_far = "**Server bank accounts:**"
                for uid in self.__economy.keys():
                    user = await ctx.guild.fetch_member(uid)
                    str_so_far += f"\n**{user.display_name}** has ${round(self.__economy[uid], 2)}."
                await ctx.send(str_so_far)
            else:
                # INVALID USAGE
                await ctx.send("`$plant bank [all]`")

        # Option 2 (default): Report caller's wealth and rank
        else:
            # Find rank by sorting a copied dictionary and finding index of uid
            sorted_economy = sorted(self.__economy, key=self.__economy.get, reverse=True)
            rank = sorted_economy.index(aid) + 1  # Add 1 to start counting from 1

            # Report info
            await ctx.send(f"**{ctx.author.display_name}** has "
                           f"${round(self.__economy[aid], 2)} "
                           f"(Rank: {rank}).")

    async def __check_market(self, ctx) -> None:
        """Send a message displaying the current prices for all fruit in the server market.
        """
        str_so_far = "**Fruit market prices:**"
        for fruit in self.__market:
            str_so_far += "\n" + fruit + " $" + str(round(self.__market[fruit], 2))
        await ctx.send(str_so_far)

    async def __sell(self, ctx, *args) -> None:
        """Sell the type and number of fruit from the caller's inventory based on args.
        """
        aid = ctx.author.id
        inventory = self.__get_inventory(aid)

        # Set flags
        sell_all = False
        target_fruit = None
        num = None

        # Option 1: Specify exact type and amount of fruit to sell
        if len(args) >= 3:
            try:
                num = int(args[2])  # Number of fruits to sell
            except ValueError:
                # INVALID USAGE
                await ctx.send("`<num> must be a valid number`")
                return
            target_fruit = ":" + args[1] + ":"  # Type of fruit to sell in emoji form

        # Option 2: Sell all fruit
        elif len(args) == 2 and args[1] == "all":
            sell_all = True

        # Default: INVALID USAGE
        else:
            await ctx.send("`$plant sell <fruit> <num> or $plant sell all`")
            return

        # Sell any fruit if sell_all, or sell all of the given fruit until num reached or none left
        num_sold = 0
        total_sale = 0.
        inventory_copy = inventory[:]
        for fruit in inventory_copy:
            if sell_all or (fruit == target_fruit and num_sold < num):
                inventory.remove(fruit)  # Remove the fruit from caller's inventory
                total_sale += self.__market[fruit]  # Add sale money
                self.__market[fruit] = self.__market[fruit] * 0.8  # Demand falls
                num_sold += 1

        if num_sold == 0:
            # Did not sell anything
            await ctx.send("No fruits were sold.")
        else:
            # Report sale information and new balance
            self.__add_wealth(aid, total_sale)
            await ctx.send(f"You sold {num_sold} " + ("fruit" if sell_all else target_fruit) +
                           f" for ${round(total_sale, 2)}. "
                           f"You now have ${round(self.__economy[aid], 2)}.")

    async def process_cmd(self, ctx, *args) -> None:
        """Process any call to the $plant command for this server.
        """
        # If no arguments, then show stats for the plant
        if len(args) == 0:
            await self.__summary(ctx)
            return

        # Otherwise, process command intent
        match args[0]:
            case "respawn" | "r":
                await self.__respawn(ctx)
            case "water" | "w":
                await self.__water(ctx)
            case "pet" | "p":
                await self.__pet(ctx)
            case "name" | "n":
                await self.__set_name(ctx, *args)
            case "harvest" | "h":
                await self.__harvest(ctx)
            case "inventory" | "i":
                await self.__check_inventory(ctx)
            case "bank" | "b":
                await self.__check_wealth(ctx, *args)
            case "market" | "m":
                await self.__check_market(ctx)
            case "sell" | "s":
                await self.__sell(ctx, *args)
            case other:
                # Unknown command, react with ?
                await ctx.message.add_reaction("❓")

    @tasks.loop(seconds=30)
    async def tick(self) -> None:
        """Re-evaluate plant stats for this new time period.
        """
        if self.__alive:
            # Lose hydration (100% per 30,000 seconds = 8.33 hrs)
            self.__hydration = self.__hydration - 0.1

            # Kill plant if over or underhydrated
            if self.__hydration > 200:
                self.__death_cause = "overwatering"
                self.__alive = False
            if self.__hydration < 0:
                self.__death_cause = "underwatering"
                self.__alive = False

            # Lose happiness (exponential decay)
            self.__happiness = self.__happiness * 0.9925

            # Each tick, try to generate fruit for the plant based on happiness probability
            # At 100% happiness, fruit probability per tick is 25%
            if len(self.__fruits) < 20 and (random.random() <= self.__happiness / 400):
                # Choose random fruit from fruit market
                self.__fruits.append(random.choice(list(FRUIT_MARKET.keys())))

        # Adjust market
        self.__adjust_market()

        # Save plant information in pickle file
        self.__dump()

    def __dump(self) -> None:
        """Write the relevant attributes of this server's plant as a dictionary into the pickle file
         whose name is given by the guild id. If there is no such pickle file, create it.
        """
        attributes = {
            "name": self.__name,
            "hydration": self.__hydration,
            "happiness": self.__happiness,
            "alive": self.__alive,
            "death_cause": self.__death_cause,
            "fruit": self.__fruits,
            "economy": self.__economy,
            "inventories": self.__inventories,
            "assets": self.__assets,
            "market": self.__market,
        }

        with open(f"plant_managers/{self.__gid}.pickle", "wb") as fp:
            pickle.dump(attributes, fp)

    def __load(self) -> None:
        """Set attributes of this server's plant with the dictionary from its pickle file, whose
        name is given by the guild id.
        """
        with open(f"plant_managers/{self.__gid}.pickle", "rb") as fp:
            attributes = pickle.load(fp)

        self.__name = attributes["name"]
        self.__hydration = attributes["hydration"]
        self.__happiness = attributes["happiness"]
        self.__alive = attributes["alive"]
        self.__death_cause = attributes["death_cause"]
        self.__fruits = attributes["fruit"]
        self.__economy = attributes["economy"]
        self.__inventories = attributes["inventories"]
        self.__assets = attributes["assets"]
        self.__market = attributes["market"]
