import re


def analyze_incident(disaster_report: str) -> dict:
    """
    Analyze the disaster report and estimate
    disaster type, severity and affected population.
    """

    report = disaster_report.lower()

    # --------------------------
    # Detect disaster type
    # --------------------------

    disaster_type = "Unknown"

    disaster_keywords = {
        "Flood": ["flood", "waterlogging", "overflow"],
        "Earthquake": ["earthquake", "quake", "tremor"],
        "Cyclone": ["cyclone", "storm", "hurricane"],
        "Fire": ["fire", "blaze", "smoke"],
        "Landslide": ["landslide"],
        "Heatwave": ["heatwave", "extreme heat"],
        "Tsunami": ["tsunami"],
        "Building Collapse": ["collapsed building", "building collapse"],
        "Chemical Leak": ["chemical leak", "gas leak"],
        "Industrial Accident": ["factory accident", "industrial accident"]
    }

    for disaster, keywords in disaster_keywords.items():
        if any(word in report for word in keywords):
            disaster_type = disaster
            break

    # --------------------------
    # Estimate affected population
    # --------------------------

    affected_population = 100

    numbers = re.findall(r"\d+", report)

    if numbers:
        affected_population = int(numbers[0])

    # --------------------------
    # Estimate severity
    # --------------------------

    severity = "Low"

    if affected_population >= 500:
        severity = "High"

    elif affected_population >= 200:
        severity = "Medium"

    critical_keywords = [
        "collapsed",
        "trapped",
        "stranded",
        "injured",
        "dead",
        "missing",
        "critical",
        "severe"
    ]

    if any(word in report for word in critical_keywords):
        severity = "High"

    return {
        "disaster_type": disaster_type,
        "severity": severity,
        "affected_population": affected_population
    }
