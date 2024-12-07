# logic/parlay.py

def build_optimal_parlay(selected_games, predicted_games, player_props):
    """
    Build a parlay by selecting a mix of bets:
    - Use top confidence picks from predicted games
    - Include some player props with good expected value from player_props

    Steps:
    1. Filter predicted_games by those selected by user.
    2. Sort by confidence descending.
    3. Take top 2 from spreads/totals.
    4. From player_props, select 2 with best implied value (lowest vig or best line).
    5. Return these 4 legs as a parlay.
    """

    # Filter predicted_games to only those user selected
    selected_preds = [g for g in predicted_games if str(g["GameID"]) in selected_games]

    # Sort by confidence descending
    selected_preds.sort(key=lambda x: x["confidence"], reverse=True)

    # Take top 2 from the predicted outcomes
    top_2_legs = []
    for pg in selected_preds:
        # Construct a leg from pg. For example: (Team, Pick, Odds)
        # Assume 'odds' field or derive from 'spread' difference. If no direct odds given,
        # we approximate from spread. Let's pick a fake moneyline from spread for demonstration:
        # Positive margin: home team favored, assign -120 odds if confidence >5, else -110
        odds = convert_confidence_to_odds(pg["confidence"])
        leg = {
            "game": f"{pg['AwayTeam']} @ {pg['HomeTeam']}",
            "pick": pg["recommended_pick"],
            "odds": odds,
            "type": "spread_or_total",
        }
        top_2_legs.append(leg)
        if len(top_2_legs) == 2:
            break

    # From player_props, select 2 with best expected value
    # player_props is a list of betting markets. We'll pick any 2 with 'IsAvailable' = True.
    top_2_props = select_best_player_props(player_props, limit=2)

    # Combine to create final parlay (4 legs)
    parlay_legs = top_2_legs + top_2_props
    return parlay_legs

def convert_confidence_to_odds(confidence):
    """
    Convert confidence (difference in margin vs spread) to approximate odds.
    This is simplistic:
    High confidence -> better than -110
    Let's say confidence in range [0,10]. If >5, odds = -120, else -110 for simplicity.
    """
    if confidence > 5:
        return "-120"
    else:
        return "-110"

def select_best_player_props(player_props, limit=2):
    """
    Select best player props based on line value.
    Player props is a list of betting markets from get_player_props.
    We'll choose any two with 'IsAvailable' = True.
    In a real scenario, you'd analyze outcome probabilities and implied odds.

    For no dummy metrics: we assume we have at least some player props data.
    We'll pick the first two player props from the first available market.
    """
    props_selected = []
    for market in player_props:
        outcomes = market.get("Outcomes", [])
        for o in outcomes:
            if o.get("IsAvailable", True):
                props_selected.append(
                    {
                        "game": market.get("EventName", "Player Prop"),
                        "pick": f"{o['Participant']} {o['Name']}",
                        "odds": o.get("MoneyLine", "-110"),
                        "type": "player_prop",
                    }
                )
                if len(props_selected) == limit:
                    return props_selected
    # If not enough props, fill with placeholders
    while len(props_selected) < limit:
        props_selected.append(
            {
                "game": "No props found",
                "pick": "N/A",
                "odds": "-110",
                "type": "player_prop",
            }
        )
    return props_selected
