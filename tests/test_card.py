"""card.py 단위 테스트."""

import pytest

from game.card import Card, SpecialCard, Suit


# ── 일반 카드 생성 ──────────────────────────────────────────────


class TestNormalCardCreation:
    """일반 카드 생성 테스트."""

    def test_create_with_rank_and_suit(self) -> None:
        card = Card.normal(2, Suit.JADE)
        assert card.rank == 2
        assert card.suit == Suit.JADE
        assert card.special is None

    def test_create_ace(self) -> None:
        card = Card.normal(14, Suit.STAR)
        assert card.rank == 14

    def test_all_suits(self) -> None:
        for suit in Suit:
            card = Card.normal(7, suit)
            assert card.suit == suit

    def test_all_ranks(self) -> None:
        for rank in range(2, 15):
            card = Card.normal(rank, Suit.SWORD)
            assert card.rank == rank

    def test_reject_rank_below_2(self) -> None:
        with pytest.raises(ValueError, match="2~14"):
            Card.normal(1, Suit.JADE)

    def test_reject_rank_above_14(self) -> None:
        with pytest.raises(ValueError, match="2~14"):
            Card.normal(15, Suit.JADE)

    def test_reject_no_suit(self) -> None:
        with pytest.raises(ValueError, match="suit가 필요"):
            Card(rank=5)

    def test_is_special_false(self) -> None:
        card = Card.normal(10, Suit.PAGODA)
        assert card.is_special is False


# ── 특수 카드 생성 ──────────────────────────────────────────────


class TestSpecialCardCreation:
    """특수 카드 생성 테스트."""

    def test_dragon(self) -> None:
        d = Card.dragon()
        assert d.special == SpecialCard.DRAGON
        assert d.rank == 25.0
        assert d.suit is None
        assert d.is_special is True

    def test_phoenix(self) -> None:
        p = Card.phoenix()
        assert p.special == SpecialCard.PHOENIX
        assert p.rank == 1.5
        assert p.is_special is True

    def test_dog(self) -> None:
        dog = Card.dog()
        assert dog.special == SpecialCard.DOG
        assert dog.rank == 0.0
        assert dog.is_special is True

    def test_mahjong(self) -> None:
        m = Card.mahjong()
        assert m.special == SpecialCard.MAHJONG
        assert m.rank == 1.0
        assert m.is_special is True

    def test_reject_special_with_suit(self) -> None:
        with pytest.raises(ValueError, match="suit를 가질 수 없"):
            Card(rank=25.0, suit=Suit.STAR, special=SpecialCard.DRAGON)


# ── 점수 계산 ───────────────────────────────────────────────────


class TestPoints:
    """카드 점수 테스트."""

    def test_five_gives_5_points(self) -> None:
        for suit in Suit:
            assert Card.normal(5, suit).points == 5

    def test_ten_gives_10_points(self) -> None:
        assert Card.normal(10, Suit.JADE).points == 10

    def test_king_gives_10_points(self) -> None:
        assert Card.normal(13, Suit.SWORD).points == 10

    def test_dragon_gives_25_points(self) -> None:
        assert Card.dragon().points == 25

    def test_phoenix_gives_minus_25_points(self) -> None:
        assert Card.phoenix().points == -25

    def test_zero_point_cards(self) -> None:
        zero_ranks = [2, 3, 4, 6, 7, 8, 9, 11, 12, 14]
        for rank in zero_ranks:
            assert Card.normal(rank, Suit.STAR).points == 0

    def test_dog_zero_points(self) -> None:
        assert Card.dog().points == 0

    def test_mahjong_zero_points(self) -> None:
        assert Card.mahjong().points == 0

    def test_total_deck_points_equal_100(self) -> None:
        """전체 덱 56장의 점수 합은 항상 100점이어야 한다."""
        total = 0
        for suit in Suit:
            for rank in range(2, 15):
                total += Card.normal(rank, suit).points
        total += Card.dragon().points
        total += Card.phoenix().points
        total += Card.dog().points
        total += Card.mahjong().points
        assert total == 100


# ── Phoenix +0.5 동작 ──────────────────────────────────────────


class TestPhoenixRank:
    """Phoenix의 +0.5 rank 동작 테스트."""

    def test_phoenix_beats_by_half(self) -> None:
        phoenix = Card.phoenix()
        assert phoenix.phoenix_rank(10.0) == 10.5

    def test_phoenix_over_ace(self) -> None:
        phoenix = Card.phoenix()
        assert phoenix.phoenix_rank(14.0) == 14.5

    def test_phoenix_over_mahjong(self) -> None:
        phoenix = Card.phoenix()
        assert phoenix.phoenix_rank(1.0) == 1.5

    def test_phoenix_rank_on_non_phoenix_raises(self) -> None:
        card = Card.normal(7, Suit.JADE)
        with pytest.raises(ValueError, match="Phoenix"):
            card.phoenix_rank(5.0)

    def test_phoenix_cannot_beat_dragon(self) -> None:
        """Phoenix rank는 Dragon(25) 아래에 머문다."""
        phoenix = Card.phoenix()
        dragon = Card.dragon()
        effective = phoenix.phoenix_rank(14.0)  # 14.5
        assert effective < dragon.rank


# ── 비교 및 정렬 ───────────────────────────────────────────────


class TestComparison:
    """카드 비교/정렬 테스트."""

    def test_higher_rank_is_greater(self) -> None:
        low = Card.normal(3, Suit.JADE)
        high = Card.normal(10, Suit.JADE)
        assert low < high
        assert high > low

    def test_equal_rank_cards_are_equal(self) -> None:
        a = Card.normal(7, Suit.JADE)
        b = Card.normal(7, Suit.JADE)
        assert a == b

    def test_different_suit_same_rank_not_equal(self) -> None:
        a = Card.normal(7, Suit.JADE)
        b = Card.normal(7, Suit.STAR)
        assert a != b

    def test_sorting_order(self) -> None:
        cards = [
            Card.normal(14, Suit.STAR),
            Card.normal(2, Suit.JADE),
            Card.dragon(),
            Card.dog(),
            Card.normal(7, Suit.SWORD),
        ]
        sorted_cards = sorted(cards)
        ranks = [c.rank for c in sorted_cards]
        assert ranks == [0.0, 2, 7, 14, 25.0]

    def test_dragon_is_highest(self) -> None:
        dragon = Card.dragon()
        ace = Card.normal(14, Suit.STAR)
        assert dragon > ace

    def test_dog_is_lowest(self) -> None:
        dog = Card.dog()
        two = Card.normal(2, Suit.JADE)
        assert dog < two

    def test_frozen_immutable(self) -> None:
        card = Card.normal(5, Suit.JADE)
        with pytest.raises(AttributeError):
            card.rank = 10  # type: ignore[misc]


# ── __str__ / __repr__ ─────────────────────────────────────────


class TestStringRepresentation:
    """문자열 표현 테스트."""

    def test_normal_card_str(self) -> None:
        assert str(Card.normal(14, Suit.STAR)) == "♥A"
        assert str(Card.normal(2, Suit.JADE)) == "♣2"
        assert str(Card.normal(11, Suit.SWORD)) == "♠J"
        assert str(Card.normal(12, Suit.PAGODA)) == "♦Q"
        assert str(Card.normal(13, Suit.STAR)) == "♥K"

    def test_special_card_str(self) -> None:
        assert str(Card.dragon()) == "Dragon"
        assert str(Card.phoenix()) == "Phoenix"
        assert str(Card.dog()) == "Dog"
        assert str(Card.mahjong()) == "Mahjong"

    def test_repr(self) -> None:
        card = Card.normal(7, Suit.JADE)
        assert repr(card) == "Card(♣7)"


# ── 해시 및 집합 사용 ──────────────────────────────────────────


class TestHashing:
    """해시/집합 사용 테스트."""

    def test_same_card_same_hash(self) -> None:
        a = Card.normal(5, Suit.JADE)
        b = Card.normal(5, Suit.JADE)
        assert hash(a) == hash(b)

    def test_usable_in_set(self) -> None:
        cards = {Card.normal(5, Suit.JADE), Card.normal(5, Suit.JADE)}
        assert len(cards) == 1

    def test_special_cards_in_set(self) -> None:
        cards = {Card.dragon(), Card.dragon(), Card.phoenix()}
        assert len(cards) == 2
