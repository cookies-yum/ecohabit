"""
carbon_data.py
Static reference data for EcoHabit — matches the content shown in the
original Base44 prototype (habit list, plant catalog, store catalog,
recycling locations), extended slightly for completeness.
"""

HABITS = [
    {"id": 1, "name": "Take Public Transport", "category": "Transport", "icon": "🚌",
     "desc": "Use bus, train or metro instead of driving", "ecobits": 50, "co2": 2.3, "verify": "checkin"},
    {"id": 2, "name": "Cycle to Work", "category": "Transport", "icon": "🚲",
     "desc": "Bike to your destination instead of using a car", "ecobits": 60, "co2": 2.4, "verify": "photo"},
    {"id": 3, "name": "Carpool With Others", "category": "Transport", "icon": "🚗",
     "desc": "Share a ride instead of driving alone", "ecobits": 35, "co2": 1.6, "verify": "photo"},
    {"id": 4, "name": "Eat a Veggie Meal", "category": "Food", "icon": "🥗",
     "desc": "Choose a plant-based meal over meat", "ecobits": 40, "co2": 3.0, "verify": "photo"},
    {"id": 5, "name": "Buy Local Produce", "category": "Food", "icon": "🍎",
     "desc": "Purchase locally grown food to reduce transport emissions", "ecobits": 20, "co2": 0.8, "verify": "photo"},
    {"id": 6, "name": "Meatless Monday", "category": "Food", "icon": "🥕",
     "desc": "Skip meat entirely for the day", "ecobits": 45, "co2": 3.5, "verify": "checkin"},
    {"id": 7, "name": "Turn Off Lights", "category": "Energy", "icon": "💡",
     "desc": "Switch off lights when leaving a room", "ecobits": 10, "co2": 0.1, "verify": "checkin"},
    {"id": 8, "name": "Unplug Electronics", "category": "Energy", "icon": "🔌",
     "desc": "Unplug devices when not in use", "ecobits": 15, "co2": 0.2, "verify": "checkin"},
    {"id": 9, "name": "Cold Water Wash", "category": "Energy", "icon": "🧺",
     "desc": "Wash laundry on a cold cycle instead of hot", "ecobits": 20, "co2": 0.5, "verify": "checkin"},
    {"id": 10, "name": "Use Reusable Cup", "category": "Waste", "icon": "🥤",
     "desc": "Bring your own cup for coffee or drinks", "ecobits": 15, "co2": 0.1, "verify": "photo"},
    {"id": 11, "name": "Recycle Properly", "category": "Waste", "icon": "🗑️",
     "desc": "Sort and recycle your waste correctly", "ecobits": 30, "co2": 0.5, "verify": "photo"},
    {"id": 12, "name": "Compost Food Scraps", "category": "Waste", "icon": "🍂",
     "desc": "Compost instead of sending scraps to landfill", "ecobits": 25, "co2": 0.5, "verify": "photo"},
    {"id": 13, "name": "Shorter Shower", "category": "Water", "icon": "🚿",
     "desc": "Take a 5-minute shower instead of 15 minutes", "ecobits": 25, "co2": 0.6, "verify": "checkin"},
    {"id": 14, "name": "Fix a Leaky Faucet", "category": "Water", "icon": "💧",
     "desc": "Stop a drip before it wastes gallons of water", "ecobits": 20, "co2": 0.3, "verify": "checkin"},
    {"id": 15, "name": "Bring Reusable Bag", "category": "Shopping", "icon": "🛍️",
     "desc": "Use your own shopping bag instead of plastic", "ecobits": 20, "co2": 0.05, "verify": "photo"},
    {"id": 16, "name": "Buy Second-Hand", "category": "Shopping", "icon": "👕",
     "desc": "Choose used over new when you can", "ecobits": 35, "co2": 2.0, "verify": "photo"},
]

CATEGORIES = ["Transport", "Food", "Energy", "Waste", "Water", "Shopping"]

# Comparisons for the "Compare" page — the greener choice vs. the typical one.
COMPARISONS = [
    {"id": 1, "title": "Bus vs. Car", "greener": "Bus (10 km)", "typical": "Car (10 km)",
     "co2_greener": 0.7, "co2_typical": 2.4, "tip": "Public transport spreads emissions across many riders."},
    {"id": 2, "title": "Veggie Meal vs. Beef Meal", "greener": "Vegetarian meal", "typical": "Beef meal",
     "co2_greener": 1.5, "co2_typical": 6.5, "tip": "Beef is one of the most carbon-intensive foods there is."},
    {"id": 3, "title": "Reusable Cup vs. Disposable Cup", "greener": "Reusable cup", "typical": "Single-use cup",
     "co2_greener": 0.02, "co2_typical": 0.11, "tip": "Small per-use savings that add up fast as a daily habit."},
    {"id": 4, "title": "Bike vs. Car", "greener": "Bike (10 km)", "typical": "Car (10 km)",
     "co2_greener": 0.0, "co2_typical": 2.4, "tip": "Zero tailpipe emissions, plus it's free exercise."},
    {"id": 5, "title": "Cold Wash vs. Hot Wash", "greener": "Cold water laundry load", "typical": "Hot water laundry load",
     "co2_greener": 0.1, "co2_typical": 0.6, "tip": "Heating water is most of a laundry load's carbon footprint."},
    {"id": 6, "title": "Reusable Bag vs. Plastic Bag", "greener": "Reusable bag", "typical": "Plastic bag",
     "co2_greener": 0.01, "co2_typical": 0.06, "tip": "One reusable bag replaces hundreds of single-use bags."},
]

# Virtual plant catalog for "My Plants" / EcoStore plant collection.
PLANTS_CATALOG = [
    {"id": 1, "name": "Baby Cactus", "rarity": "Common", "cost": 0, "free_starter": True,
     "desc": "A cute little cactus that grows with your eco habits", "emoji": "🌵"},
    {"id": 2, "name": "Sunflower", "rarity": "Common", "cost": 75, "free_starter": False,
     "desc": "Bright and cheerful, grows towards sustainability", "emoji": "🌻"},
    {"id": 3, "name": "Cherry Blossom", "rarity": "Rare", "cost": 100, "free_starter": False,
     "desc": "Beautiful pink blooms for dedicated eco warriors", "emoji": "🌸"},
    {"id": 4, "name": "Bamboo", "rarity": "Rare", "cost": 120, "free_starter": False,
     "desc": "Fast-growing symbol of resilience", "emoji": "🎍"},
    {"id": 5, "name": "Magical Mushroom", "rarity": "Epic", "cost": 200, "free_starter": False,
     "desc": "A mystical fungus for true eco champions", "emoji": "🍄"},
    {"id": 6, "name": "Rainbow Tree", "rarity": "Legendary", "cost": 500, "free_starter": False,
     "desc": "The legendary rainbow tree - ultra rare!", "emoji": "🌈"},
]

GROWTH_STAGES = 4
ECOBITS_PER_STAGE = 12.5  # 4 stages x 12.5 = 50 ecobits "waters" to fully grow

# EcoStore non-plant items
STORE_ITEMS = [
    {"id": 1, "name": "Eco Warrior Badge", "category": "Digital Badges",
     "desc": "Digital badge showing you've logged 10 habits", "cost": 100},
    {"id": 2, "name": "Planet Protector Badge", "category": "Digital Badges",
     "desc": "Exclusive badge for saving 10kg of CO2", "cost": 250},
    {"id": 3, "name": "Plant a Tree", "category": "Donations",
     "desc": "Donate to plant a real tree in your name", "cost": 500},
    {"id": 4, "name": "Ocean Cleanup Donation", "category": "Donations",
     "desc": "Support ocean plastic cleanup initiatives", "cost": 300},
    {"id": 5, "name": "Bamboo Utensil Set", "category": "Eco Products",
     "desc": "Reusable bamboo fork, knife, and spoon set", "cost": 400},
    {"id": 6, "name": "Reusable Water Bottle", "category": "Eco Products",
     "desc": "Stainless steel eco-friendly water bottle", "cost": 350},
    {"id": 7, "name": "Virtual Farm Tour", "category": "Experiences",
     "desc": "Online tour of a sustainable organic farm", "cost": 200},
    {"id": 8, "name": "Eco Tips Newsletter", "category": "Experiences",
     "desc": "Monthly newsletter with eco-living tips", "cost": 50},
]

STORE_CATEGORIES = ["My Plants", "Digital Badges", "Eco Products", "Donations", "Experiences"]

# Recycling locations (Israel), roughly accurate coordinates for demonstration.
RECYCLING_LOCATIONS = [
    {"name": "Tel Aviv Recycling Center", "type": "Recycling Center", "lat": 32.0853, "lng": 34.7818},
    {"name": "Jerusalem Recycling Center", "type": "Recycling Center", "lat": 31.7683, "lng": 35.2137},
    {"name": "Haifa Recycling Center", "type": "Recycling Center", "lat": 32.7940, "lng": 34.9896},
    {"name": "Be'er Sheva Recycling Center", "type": "Recycling Center", "lat": 31.2530, "lng": 34.7915},
    {"name": "Ramat Gan Public Bins", "type": "Public Recycling Bin", "lat": 32.0684, "lng": 34.8248},
    {"name": "Netanya Public Bins", "type": "Public Recycling Bin", "lat": 32.3215, "lng": 34.8532},
    {"name": "Herzliya Public Bins", "type": "Public Recycling Bin", "lat": 32.1663, "lng": 34.8434},
    {"name": "Ashdod Recycling Center", "type": "Recycling Center", "lat": 31.8014, "lng": 34.6435},
    {"name": "Petah Tikva Public Bins", "type": "Public Recycling Bin", "lat": 32.0917, "lng": 34.8850},
    {"name": "Rishon LeZion Public Bins", "type": "Public Recycling Bin", "lat": 31.9730, "lng": 34.7925},
]

LANGUAGES = [
    {"code": "en", "name": "English", "native": "English", "flag": "GB"},
    {"code": "he", "name": "Hebrew", "native": "עברית", "flag": "IL"},
    {"code": "ar", "name": "Arabic", "native": "العربية", "flag": "SA"},
]


def get_habit(habit_id):
    return next((h for h in HABITS if h["id"] == habit_id), None)


def get_store_item(item_id):
    return next((i for i in STORE_ITEMS if i["id"] == item_id), None)


def get_plant_catalog(catalog_id):
    return next((p for p in PLANTS_CATALOG if p["id"] == catalog_id), None)
