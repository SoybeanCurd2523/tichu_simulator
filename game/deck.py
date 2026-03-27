"""덱 클래스 정의."""

import random

from game.card import Card, SpecialCard, Suit


class Deck:
    """티츄 56장 덱.

    일반 카드 52장(2~A, 4무늬) + 특수 카드 4장.
    """

    def __init__(self) -> None:
        self._cards: list[Card] = []
        self._build()

    def _build(self) -> None:
        """56장 덱을 구성한다."""
        self._cards = []
        # 일반 카드: 2~14(A), 4무늬
        for suit in Suit:
            for rank in range(2, 15):
                self._cards.append(Card(rank=rank, suit=suit))
        # 특수 카드
        self._cards.append(Card.mahjong())
        self._cards.append(Card.dog())
        self._cards.append(Card.phoenix())
        self._cards.append(Card.dragon())

    def shuffle(self) -> None:
        """덱을 섞는다."""
        random.shuffle(self._cards)

    def deal(self, num_players: int = 4) -> list[list[Card]]:
        """카드를 나눠준다.

        Args:
            num_players: 플레이어 수 (기본 4명).

        Returns:
            각 플레이어에게 나눠줄 카드 리스트의 리스트.
        """
        self.shuffle()
        cards_per_player = len(self._cards) // num_players
        hands: list[list[Card]] = []
        for i in range(num_players):
            start = i * cards_per_player
            end = start + cards_per_player
            hands.append(self._cards[start:end])
        return hands

    @property
    def cards(self) -> list[Card]:
        """현재 덱의 카드 목록."""
        return list(self._cards)

    def __len__(self) -> int:
        return len(self._cards)
