def recommend_shelters(affected_population: int) -> dict:
    """
    Recommend shelters based on affected population.
    """

    shelters_needed = max(1, affected_population // 200)

    shelter_type = "Community Hall"

    if affected_population > 500:
        shelter_type = "School + Stadium"

    elif affected_population > 200:
        shelter_type = "Government School"

    else:
        shelter_type = "Community Hall"

    return {
        "shelters_needed": shelters_needed,
        "capacity_required": affected_population,
        "recommended_shelter": shelter_type
    }
