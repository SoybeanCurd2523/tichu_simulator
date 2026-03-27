# Tichu Simulator

A command-line Tichu card game simulator written in Python. Play the classic 4-player partnership trick-taking card game against AI opponents, or run large-scale AI-vs-AI simulations to analyze strategies and card statistics.

## Features

- **4-Player Game** -- Play as 1 human (Player 0) with 3 AI teammates/opponents
- **CLI Interface** -- Interactive card selection, Grand/Small Tichu declarations, Dragon recipient choice, and auto-pass detection
- **AI Strategy** -- Team-aware play (Dog pass to partner, Tichu support), combo prioritization (straights > pairs > singles), bomb usage decisions, and strategic passing
- **Simulation Mode** -- Run thousands of AI-only games and collect per-round statistics on special cards, Tichu success rates, bomb impact, and more

## Installation

```bash
python -m venv tichu
source tichu/bin/activate   # Linux/macOS
pip install -r requirements.txt
```

Requires Python 3.10+.

## Usage

### Play a game (human vs AI)

```bash
python main.py
```

You control Player 0 (Team 0 with AI\_2). Team 1 is AI\_1 and AI\_3. First team to 1000 points wins.

### Run AI simulation

```bash
python simulate.py --games 1000
python simulate.py --games 500 --save-csv          # save raw data to results.csv
python simulate.py --games 10 --verbose             # print each round
```

**Options:**

| Flag | Description |
|------|-------------|
| `--games N` | Number of games to simulate (default: 1000) |
| `--save-csv` | Save raw per-player-per-round data to `results.csv` |
| `--verbose` | Print round-by-round results |

**Statistics output** (9 categories):

1. Average finish by special card count
2. Average finish by individual special card
3. Grand Tichu success rate by special count
4. Grand Tichu success rate by card combination
5. Small Tichu success rate by special count
6. Small Tichu success rate by card combination
7. Average finish by hand strength (avg rank buckets)
8. 1-2 finish occurrence rate
9. Bomb holders vs non-holders average finish

## Project Structure

```
tichu_simulator/
├── main.py                 # CLI game entry point (human vs AI)
├── simulate.py             # AI-only simulation & statistics
├── game/
│   ├── card.py             # Card, Suit, SpecialCard definitions
│   ├── deck.py             # 56-card deck
│   ├── hand.py             # Hand classification & validation
│   ├── player.py           # Player base class with AI logic
│   ├── human_player.py     # Human player CLI input
│   ├── game.py             # Game loop & trick resolution
│   └── scoring.py          # Round scoring & Tichu bonuses
├── tests/
│   ├── test_card.py        # Card representation tests
│   ├── test_hand.py        # Hand validation tests
│   ├── test_game.py        # Game logic integration tests
│   ├── test_player_ai.py   # AI strategy tests
│   ├── test_human_player.py# Human input tests
│   ├── test_dragon_recipient.py  # Dragon trick recipient tests
│   └── test_auto_pass.py   # Auto-pass & bomb prompt tests
├── requirements.txt
└── pytest.ini
```

## Running Tests

```bash
pytest
```

---

This project was built with assistance from Claude Code (Anthropic).
