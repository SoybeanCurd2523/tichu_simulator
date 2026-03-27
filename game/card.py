"""카드 클래스 정의.

티츄 덱은 56장으로 구성된다:
- 일반 카드 52장: 2~A(14), 4가지 슈트(Jade, Sword, Pagoda, Star)
- 특수 카드 4장: Mahjong(1), Dog, Phoenix, Dragon
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from functools import total_ordering


class Suit(Enum):
    """카드 슈트(무늬)."""
    JADE = auto()      # 옥 (녹색)
    SWORD = auto()     # 검 (검정)
    PAGODA = auto()    # 탑 (파랑)
    STAR = auto()      # 별 (빨강)


class SpecialCard(Enum):
    """특수 카드 종류."""
    MAHJONG = auto()   # 참새 — 가장 낮은 카드(1), 선공 결정
    DOG = auto()       # 개 — 턴을 파트너에게 넘김, 단독으로만 사용
    PHOENIX = auto()   # 봉황 — 와일드카드, 싱글 시 직전 카드 +0.5
    DRAGON = auto()    # 용 — 싱글 최강 카드

    @property
    def base_rank(self) -> float:
        """특수 카드의 기본 rank 값."""
        ranks: dict[SpecialCard, float] = {
            SpecialCard.DOG: 0.0,
            SpecialCard.MAHJONG: 1.0,
            SpecialCard.PHOENIX: 1.5,  # 기본값; 싱글 플레이 시 동적으로 변경
            SpecialCard.DRAGON: 25.0,
        }
        return ranks[self]


@total_ordering
@dataclass(frozen=True)
class Card:
    """티츄 카드.

    일반 카드는 rank(2~14)와 suit를 가진다.
    특수 카드는 special 필드로 구분하며, rank는 자동 설정된다.

    Attributes:
        rank: 카드 세기. 일반 카드 2~14(A), 특수 카드는 base_rank 사용.
        suit: 카드 슈트. 일반 카드만 가진다.
        special: 특수 카드 종류. None이면 일반 카드.
    """
    rank: float
    suit: Suit | None = None
    special: SpecialCard | None = None

    def __post_init__(self) -> None:
        if self.special is None and self.suit is None:
            raise ValueError("일반 카드는 suit가 필요합니다.")
        if self.special is not None and self.suit is not None:
            raise ValueError("특수 카드는 suit를 가질 수 없습니다.")
        if self.special is None and (not isinstance(self.rank, (int, float))
                                     or not (2 <= self.rank <= 14)):
            raise ValueError(f"일반 카드의 rank는 2~14여야 합니다: {self.rank}")

    @staticmethod
    def normal(rank: int, suit: Suit) -> Card:
        """일반 카드를 생성한다."""
        return Card(rank=rank, suit=suit)

    @staticmethod
    def dragon() -> Card:
        """Dragon 특수 카드를 생성한다."""
        return Card(rank=SpecialCard.DRAGON.base_rank, special=SpecialCard.DRAGON)

    @staticmethod
    def phoenix() -> Card:
        """Phoenix 특수 카드를 생성한다."""
        return Card(rank=SpecialCard.PHOENIX.base_rank, special=SpecialCard.PHOENIX)

    @staticmethod
    def dog() -> Card:
        """Dog 특수 카드를 생성한다."""
        return Card(rank=SpecialCard.DOG.base_rank, special=SpecialCard.DOG)

    @staticmethod
    def mahjong() -> Card:
        """Mahjong(참새) 특수 카드를 생성한다."""
        return Card(rank=SpecialCard.MAHJONG.base_rank, special=SpecialCard.MAHJONG)

    @property
    def is_special(self) -> bool:
        """특수 카드 여부."""
        return self.special is not None

    def phoenix_rank(self, current_top_rank: float) -> float:
        """Phoenix를 싱글로 낼 때의 실제 rank.

        Phoenix는 현재 테이블 위 최고 카드보다 +0.5 높게 동작한다.
        단, Dragon은 이길 수 없다.

        Args:
            current_top_rank: 현재 테이블 최고 카드의 rank.

        Returns:
            Phoenix의 실효 rank 값.

        Raises:
            ValueError: Phoenix 카드가 아닌 경우.
        """
        if self.special != SpecialCard.PHOENIX:
            raise ValueError("Phoenix 카드만 호출할 수 있습니다.")
        return current_top_rank + 0.5

    @property
    def points(self) -> int:
        """카드의 점수 가치.

        점수 규칙:
        - 5: 5점
        - 10: 10점
        - K(13): 10점
        - Dragon: +25점
        - Phoenix: -25점
        - 나머지: 0점
        """
        if self.special == SpecialCard.DRAGON:
            return 25
        if self.special == SpecialCard.PHOENIX:
            return -25
        if self.rank == 5:
            return 5
        if self.rank == 10 or self.rank == 13:
            return 10
        return 0

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Card):
            return NotImplemented
        return (self.rank, self.suit, self.special) == (other.rank, other.suit, other.special)

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Card):
            return NotImplemented
        return self.rank < other.rank

    def __hash__(self) -> int:
        return hash((self.rank, self.suit, self.special))

    def __str__(self) -> str:
        if self.special:
            names = {
                SpecialCard.MAHJONG: "Mahjong",
                SpecialCard.DOG: "Dog",
                SpecialCard.PHOENIX: "Phoenix",
                SpecialCard.DRAGON: "Dragon",
            }
            return names[self.special]
        suit_symbols = {
            Suit.JADE: "♣",
            Suit.SWORD: "♠",
            Suit.PAGODA: "♦",
            Suit.STAR: "♥",
        }
        rank_names = {11: "J", 12: "Q", 13: "K", 14: "A"}
        rank_str = rank_names.get(int(self.rank), str(int(self.rank)))
        return f"{suit_symbols[self.suit]}{rank_str}"

    def __repr__(self) -> str:
        return f"Card({self})"
