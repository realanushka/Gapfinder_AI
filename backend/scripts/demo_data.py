"""Sample Class 10 Science material for the demo account (Plan Step 12.1).

Kept as plain data so the seed script stays readable and so the demo content can
be swapped for another subject without touching the seeding logic.
"""

# (chapter, section, page, text)
NOTES_CHUNKS: list[tuple[str, str, int, str]] = [
    (
        "Chapter 6 Life Processes",
        "6.1 Nutrition",
        88,
        "Photosynthesis is the process by which green plants make food using carbon dioxide "
        "and water in the presence of sunlight and chlorophyll. The raw materials are carbon "
        "dioxide, taken in through stomata, and water, absorbed by the roots. The products are "
        "glucose and oxygen. Chlorophyll in the chloroplast absorbs sunlight and gives leaves "
        "their green colour.",
    ),
    (
        "Chapter 6 Life Processes",
        "6.1 Nutrition",
        89,
        "Photosynthesis happens in two stages. In the light reaction, chlorophyll absorbs light "
        "energy and water is split into hydrogen and oxygen; the oxygen is released as a "
        "by-product. In the dark reaction, the hydrogen is used to reduce carbon dioxide into "
        "glucose. The light reaction needs light, while the dark reaction does not.",
    ),
    (
        "Chapter 6 Life Processes",
        "6.2 Respiration",
        93,
        "Respiration releases energy from glucose. Aerobic respiration takes place in the "
        "presence of oxygen inside the mitochondria and breaks glucose down completely into "
        "carbon dioxide and water, releasing a large amount of energy. The energy is stored in "
        "molecules of ATP.",
    ),
    (
        "Chapter 6 Life Processes",
        "6.2 Respiration",
        94,
        "Anaerobic respiration happens without oxygen. In yeast, glucose is converted into "
        "ethanol and carbon dioxide, which is used in brewing and baking. In our muscle cells "
        "during vigorous exercise, glucose is converted into lactic acid, and the build-up of "
        "lactic acid causes cramps.",
    ),
    (
        "Chapter 6 Life Processes",
        "6.3 Transportation",
        97,
        "In human beings, blood is carried by arteries, veins and capillaries. Arteries carry "
        "blood away from the heart and have thick elastic walls because the blood flows under "
        "high pressure. Veins carry blood back to the heart and have valves that stop the blood "
        "flowing backwards.",
    ),
    (
        "Chapter 6 Life Processes",
        "6.3 Transportation",
        99,
        "Plants transport water and minerals through the xylem and food through the phloem. "
        "Transpiration is the loss of water vapour from the leaves, and it creates a suction "
        "pull that draws water upward from the roots. Translocation is the transport of soluble "
        "products of photosynthesis through the phloem, and it requires energy.",
    ),
]

SYLLABUS_TEXT = (
    "Class 10 Science — Unit 2: Life Processes\n"
    "1. Nutrition\n"
    "   1.1 Autotrophic nutrition and photosynthesis\n"
    "   1.2 Heterotrophic nutrition\n"
    "2. Respiration\n"
    "   2.1 Aerobic respiration\n"
    "   2.2 Anaerobic respiration\n"
    "3. Transportation\n"
    "   3.1 Transportation in human beings\n"
    "   3.2 Transportation in plants\n"
)

PAST_PAPER_TEXT = (
    "Section A\n"
    "Q1. Write the balanced chemical equation for photosynthesis and name its raw materials.\n"
    "Q2. Describe the two stages of photosynthesis and state where each occurs.\n"
    "Q3. Why does the light reaction require water? Explain what happens to the oxygen.\n"
    "Q4. Compare aerobic and anaerobic respiration in human muscle cells.\n"
    "Q5. Name the products of anaerobic respiration in yeast.\n"
    "Q6. Explain why arteries have thicker walls than veins.\n"
)

# (topic, [subtopics]) -- what the LLM would extract from SYLLABUS_TEXT, written
# out so the demo account can be seeded without any API keys.
TOPIC_TREE: list[tuple[str, list[str]]] = [
    ("Nutrition", ["Autotrophic nutrition and photosynthesis", "Heterotrophic nutrition"]),
    ("Respiration", ["Aerobic respiration", "Anaerobic respiration"]),
    ("Transportation", ["Transportation in human beings", "Transportation in plants"]),
]

# Questions per topic name: (question, options|None, correct_answer, explanation,
# chunk index into NOTES_CHUNKS).
QUESTIONS: dict[str, list[tuple[str, dict | None, str, str, int]]] = {
    "Nutrition": [
        (
            "Which pigment absorbs the sunlight used in photosynthesis?",
            {"A": "Chlorophyll", "B": "Haemoglobin", "C": "Carotene", "D": "Melanin"},
            "A",
            "Chlorophyll in the chloroplast absorbs sunlight and gives leaves their green colour.",
            0,
        ),
        (
            "During the light reaction, water is split to release which gas?",
            {"A": "Carbon dioxide", "B": "Oxygen", "C": "Nitrogen", "D": "Hydrogen sulphide"},
            "B",
            "In the light reaction water is split into hydrogen and oxygen, and the oxygen is released.",
            1,
        ),
        (
            "Name the two stages of photosynthesis and say which one needs light.",
            None,
            "The light reaction, which needs light, and the dark reaction, which does not.",
            "Photosynthesis has a light reaction that requires light and a dark reaction that does not.",
            1,
        ),
    ],
    "Respiration": [
        (
            "Where does aerobic respiration take place in the cell?",
            {"A": "Nucleus", "B": "Ribosome", "C": "Mitochondria", "D": "Chloroplast"},
            "C",
            "Aerobic respiration takes place inside the mitochondria in the presence of oxygen.",
            2,
        ),
        (
            "What causes cramps during vigorous exercise?",
            {
                "A": "Build-up of lactic acid",
                "B": "Excess oxygen",
                "C": "Build-up of ethanol",
                "D": "Loss of ATP",
            },
            "A",
            "In muscle cells glucose becomes lactic acid, and its build-up causes cramps.",
            3,
        ),
    ],
    "Transportation": [
        (
            "Why do arteries have thick elastic walls?",
            {
                "A": "Because blood flows under high pressure",
                "B": "Because they carry blood to the heart",
                "C": "Because they contain valves",
                "D": "Because they carry food",
            },
            "A",
            "Arteries carry blood away from the heart under high pressure, so their walls are thick and elastic.",
            4,
        ),
        (
            "Which tissue transports the soluble products of photosynthesis?",
            {"A": "Xylem", "B": "Phloem", "C": "Stomata", "D": "Epidermis"},
            "B",
            "Translocation of the soluble products of photosynthesis happens through the phloem.",
            5,
        ),
    ],
}

# Three attempts showing improvement, so the dashboard is interesting on first
# login (Plan Step 12.2). Values are the fraction of that topic answered right.
ATTEMPT_SCORES: dict[str, list[float]] = {
    "Nutrition": [0.33, 0.67, 1.0],
    "Respiration": [0.5, 0.5, 1.0],
    "Transportation": [0.5, 1.0, 1.0],
}

ATTEMPT_REASONS: dict[str, list[str]] = {
    "Nutrition": [
        "You got 2 of 3 questions on Nutrition wrong, mostly about the light reaction.",
        "You are improving on Nutrition, but the light reaction still trips you up.",
        "You answered all 3 questions on Nutrition correctly.",
    ],
    "Respiration": [
        "You got 1 of 2 questions on Respiration wrong, around anaerobic respiration.",
        "Anaerobic respiration in muscle cells is still the weak spot.",
        "You answered all 2 questions on Respiration correctly.",
    ],
    "Transportation": [
        "You got 1 of 2 questions on Transportation wrong, about plant transport.",
        "You answered all 2 questions on Transportation correctly.",
        "You answered all 2 questions on Transportation correctly.",
    ],
}
