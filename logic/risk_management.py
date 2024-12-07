def calculate_stakes(parlay_legs, bankroll=1000):
    """
    Use a simple proportional betting strategy:
    - Allocate a fixed percentage of the bankroll based on overall parlay confidence.

    Steps:
    1. Estimate parlay probability based on individual leg probabilities.
    2. Calculate expected value.
    3. Determine stake as a percentage of bankroll based on confidence.

    For simplicity:
    Assume each leg has an independent probability:
    - 'spread_or_total' type legs have a 55% chance.
    - 'player_prop' type legs have a 60% chance.
    """
    # Calculate individual probabilities
    probabilities = []
    for leg in parlay_legs:
        if leg["type"] == "spread_or_total":
            prob = 0.55
        elif leg["type"] == "player_prop":
            prob = 0.60
        else:
            prob = 0.50  # default
        probabilities.append(prob)

    # Calculate parlay probability (product of individual probabilities)
    parlay_prob = 1
    for p in probabilities:
        parlay_prob *= p

    # Calculate parlay odds (assuming American odds, e.g., -110 -> 1.909 decimal)
    # For simplicity, multiply decimal odds
    total_decimal_odds = 1
    for leg in parlay_legs:
        american_odds = int(leg["odds"])
        decimal_odds = american_to_decimal(american_odds)
        total_decimal_odds *= decimal_odds

    # Calculate expected value
    expected_value = parlay_prob * total_decimal_odds - 1

    # Determine stake based on expected value and parlay probability
    if expected_value > 0:
        # Allocate a percentage proportional to the expected value
        stake_fraction = min(expected_value, 0.05)  # cap at 5% of bankroll
    else:
        stake_fraction = 0.01  # minimum 1% if no positive EV

    stake = bankroll * stake_fraction
    return round(stake, 2)

def american_to_decimal(american_odds):
    """
    Convert American odds to decimal odds.
    """
    if american_odds > 0:
        return 1 + (american_odds / 100)
    else:
        return 1 + (100 / abs(american_odds))
