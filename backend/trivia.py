"""Yale trivia: a short multiple-choice game Handsome Dan offers when a customer has been quiet for a minute.

The questions and answers live HERE, in a checked list, not in the AI's imagination. The agent reads each question
out exactly as given and the code decides whether an answer is right, so the chatbot can never invent a Yale "fact"
or mark a correct answer wrong. A round is 3 questions; the score is kept for the current visit only.
"""

import random
import re
from dataclasses import dataclass, field

from models import TriviaOption, TriviaQuestion, TriviaResult

ROUND_LENGTH = 3
LETTERS = "ABCD"
MAX_PLAYERS = 1000


@dataclass(frozen=True)
class Item:
    question: str
    answer: str
    wrong: tuple[str, str, str]
    fact: str
    shop_search: str | None = None  # a word to search the shop for after the answer, like "bulldog"


BANK: list[Item] = [
    Item("In what year was Yale founded?", "1701", ("1636", "1754", "1776"),
         "Yale began in 1701, which makes it the third-oldest college in the United States.", None),
    Item("Yale is named after which early benefactor?", "Elihu Yale", ("Eli Whitney", "Ezra Stiles", "Noah Webster"),
         "Elihu Yale's gift in 1718 is why Yale students are still called Elis.", None),
    Item("What does Yale's motto, Lux et Veritas, mean?", "Light and Truth", ("Courage and Honor", "Wisdom and Faith", "Strength and Duty"),
         "Lux et Veritas is on the Yale crest, and you'll spot it on plenty of our gear.", "crest"),
    Item("In which Connecticut city is Yale?", "New Haven", ("Hartford", "Stamford", "Mystic"),
         "New Haven is also home to the famous Yale Bowl.", None),
    Item("Which songwriter, Yale class of 1913, wrote the fight song Bulldog?", "Cole Porter", ("Irving Berlin", "George Gershwin", "Richard Rodgers"),
         "Cole Porter wrote Bulldog and Bingo Eli Yale while he was a student.", None),
    Item("What kind of animal is Handsome Dan, Yale's mascot?", "A bulldog", ("A bear", "A bobcat", "A bison"),
         "Handsome Dan was the first live college mascot in the United States.", "bulldog"),
    Item("How many residential colleges does Yale have?", "14", ("10", "12", "16"),
         "Every Yale undergraduate belongs to one of them, and we have gear for lots of them.", "college"),
    Item("What is the Harvard-Yale football game called?", "The Game", ("The Classic", "The Rivalry Bowl", "The Big Blue"),
         "The two teams have played since 1875.", "harvard"),
    Item("Which Yale a cappella group, founded in 1909, is the oldest senior a cappella group in the country?", "The Whiffenpoofs",
         ("The Spizzwinks", "The Baker's Dozen", "The Duke's Men"),
         "The Whiffenpoofs sing a song called The Whiffenpoof Song, which became a hit in the 1940s.", None),
    Item("Which Yale library has translucent marble walls and holds a Gutenberg Bible?", "The Beinecke Library", ("Sterling Memorial Library", "Bass Library", "Cross Campus Library"),
         "The marble is cut thin enough to let in a soft golden light.", None),
    Item("Which president graduated from Yale in 1948 and captained its baseball team?", "George H. W. Bush", ("John F. Kennedy", "Ronald Reagan", "Dwight Eisenhower"),
         "He played in the first two College World Series.", None),
    Item("Which computer-programming pioneer earned her Yale PhD in 1934 and has a residential college named after her?", "Grace Hopper", ("Ada Lovelace", "Katherine Johnson", "Margaret Hamilton"),
         "Grace Hopper College is one of Yale's fourteen residential colleges, and we have gear for it.", "grace hopper"),
]


@dataclass
class State:
    order: list[int] = field(default_factory=list)  # which BANK items this round, in order
    position: int = 0  # how many of this round have been asked
    current: dict | None = None  # the question waiting for an answer: letter -> text, plus the right letter and item index
    score: int = 0
    answered: int = 0
    used: set[int] = field(default_factory=set)  # questions already seen this visit, so a new round brings new ones


_players: dict[str, State] = {}


def _state(key: str) -> State:
    if key not in _players:
        if len(_players) >= MAX_PLAYERS:
            _players.pop(next(iter(_players)))
        _players[key] = State()
    return _players[key]


def reset() -> None:
    _players.clear()


def start(key: str) -> TriviaQuestion:
    """The next question. Starts a new round when none is going, and re-asks the question already waiting."""
    s = _state(key)
    if s.current is None:
        if not s.order or s.position >= len(s.order):  # a fresh round
            fresh = [i for i in range(len(BANK)) if i not in s.used] or list(range(len(BANK)))
            if len(fresh) < ROUND_LENGTH:
                s.used.clear()
                fresh = list(range(len(BANK)))
            s.order = random.sample(fresh, ROUND_LENGTH)
            s.position, s.score, s.answered = 0, 0, 0
        index = s.order[s.position]
        item = BANK[index]
        texts = [item.answer, *item.wrong]
        random.shuffle(texts)
        s.current = {"index": index, "options": dict(zip(LETTERS, texts)), "right": LETTERS[texts.index(item.answer)]}
        s.used.add(index)
    index, options = s.current["index"], s.current["options"]
    return TriviaQuestion(
        number=s.position + 1,
        of=ROUND_LENGTH,
        question=BANK[index].question,
        options=[TriviaOption(letter=l, text=t) for l, t in options.items()],
        how_to_answer="Reply with the letter A, B, C or D.",
    )


def _pick(answer: str, options: dict[str, str]) -> str | None:
    text = answer.strip()
    m = re.fullmatch(r"\(?([A-Da-d])[).:]?", text)
    if m:
        return m.group(1).upper()
    lowered = text.lower()
    matches = [l for l, t in options.items() if lowered and (lowered == t.lower() or lowered in t.lower().split("/"))]
    return matches[0] if len(matches) == 1 else None


def answer(key: str, reply: str) -> TriviaResult:
    s = _state(key)
    if s.current is None:
        return TriviaResult(valid=False, message="There's no trivia question waiting. Offer to start a round with start_trivia.")
    options = s.current["options"]
    letter = _pick(reply, options)
    if letter is None:
        return TriviaResult(valid=False, message="That wasn't one of the choices. Ask them to reply with A, B, C or D, and read the question again.")
    item = BANK[s.current["index"]]
    right = s.current["right"]
    correct = letter == right
    s.answered += 1
    s.score += correct
    s.position += 1
    s.current = None
    over = s.position >= ROUND_LENGTH
    return TriviaResult(
        valid=True,
        correct=correct,
        correct_letter=right,
        correct_text=options[right],
        fun_fact=item.fact,
        score=s.score,
        answered=s.answered,
        round_over=over,
        shop_search=item.shop_search if over or correct else None,
        message="Round over: give the final score and offer to shop or play again." if over else "Say whether they were right, share the fun fact, and offer the next question.",
    )


def waiting(key: str) -> bool:
    return key in _players and _players[key].current is not None
