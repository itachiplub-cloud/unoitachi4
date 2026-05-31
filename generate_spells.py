from card_utils import add_card
import json

starter_spells = [
    # 🔹 Common
    ("pulse", 90, "common"),
    ("blink", 85, "common"),
    ("gust", 80, "common"),
    ("echo", 75, "common"),
    ("tap", 70, "common"),

    # 🔸 Rare
    ("burn", 120, "rare"),
    ("flare", 115, "rare"),
    ("ripple", 110, "rare"),
    ("ignite", 105, "rare"),
    ("drift", 100, "rare"),

    # 🔮 Epic
    ("mimic", 180, "epic"),
    ("shockwave", 175, "epic"),
    ("crush", 170, "epic"),
    ("warp", 165, "epic"),
    ("nova", 160, "epic"),

    # 👑 Legendary
    ("stun", 250, "legendary"),
    ("gravity", 240, "legendary"),
    ("storm", 230, "legendary"),
    ("fracture", 220, "legendary"),
    ("obliterate", 210, "legendary")
]

for i, (power, value, rarity) in enumerate(starter_spells):
    file_id = f"starter_spell_{i:02d}"
    card_json = json.dumps({
        "power": power,
        "value": value,
        "rarity": rarity
    })
    success = add_card(file_id, card_json)
    print(f"{power.title()} added: {'✅' if success else '❌'}")
