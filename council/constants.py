"""PAI Council constants."""

MIN_EXPERTS = 4
MAX_EXPERTS = 6
OPTIMAL_EXPERTS = 4

DEBATE_WORDS_MIN = 100
DEBATE_WORDS_MAX = 150
QUICK_WORDS_MIN = 30
QUICK_WORDS_MAX = 50

# ~1.3 tokens per word; headroom for markdown
DEBATE_MAX_TOKENS = 400
ROUND_3_MAX_TOKENS = 220
QUICK_MAX_TOKENS = 150
SYNTHESIS_MAX_TOKENS = 2500
COMPOSE_MAX_TOKENS = 2000

PAI_CONVERGENCE_MIN = 3

DEFAULT_SYNTHESIS_FORMAT = "config/_shared/synthesis_format_pai.md"

DEFAULT_PERSPECTIVE_SLOTS = [
    {
        "slot": "Builder",
        "traits": "technical, enthusiastic, systematic",
        "purpose": "Has built things in this domain; defends what works in practice.",
    },
    {
        "slot": "Skeptic",
        "traits": "skeptical, meticulous, adversarial",
        "purpose": "Challenges assumptions and finds flaws others overlook.",
    },
    {
        "slot": "Pragmatist",
        "traits": "technical, pragmatic, analytical",
        "purpose": "Focuses on implementation reality, trade-offs, and cost.",
    },
    {
        "slot": "Analyst",
        "traits": "research, analytical, comparative",
        "purpose": "Brings data, precedent, and external evidence to the debate.",
    },
]
