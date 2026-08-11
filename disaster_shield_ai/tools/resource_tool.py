def calculate_resources(
    disaster_type: str,
    severity: str,
    affected_population: int
) -> dict:
    """
    Estimate emergency resources required.
    """

    food_kits = affected_population

    medical_kits = affected_population

    rescue_teams = max(1, affected_population // 100)

    ambulances = max(1, affected_population // 50)

    doctors = max(2, affected_population // 100)

    volunteers = max(10, affected_population // 25)

    boats = 0
    helicopters = 0
    fire_engines = 0

    if disaster_type == "Flood":
        boats = max(1, affected_population // 150)

    elif disaster_type == "Cyclone":
        helicopters = max(1, affected_population // 250)

    elif disaster_type == "Fire":
        fire_engines = max(1, affected_population // 100)

    # -----------------------------
    # Priority Level
    # -----------------------------

    if affected_population >= 1000:
        priority_level = "🚨 NATIONAL EMERGENCY"

    elif severity.lower() == "high":
        priority_level = "🔴 CRITICAL"

    elif severity.lower() == "medium":
        priority_level = "🟡 MEDIUM"

    else:
        priority_level = "🟢 LOW"

    return {

        "priority_level": priority_level,

        "food_kits": food_kits,

        "medical_kits": medical_kits,

        "rescue_teams": rescue_teams,

        "ambulances": ambulances,

        "doctors": doctors,

        "volunteers": volunteers,

        "boats": boats,

        "helicopters": helicopters,

        "fire_engines": fire_engines

    }
