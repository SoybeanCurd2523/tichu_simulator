"""hand.py 단위 테스트."""

import pytest

from game.card import Card, SpecialCard, Suit
from game.hand import HandType, HandValidator


# ── 헬퍼 ────────────────────────────────────────────────────────

J, S, P, T = Suit.JADE, Suit.SWORD, Suit.PAGODA, Suit.STAR


def c(rank: int, suit: Suit = J) -> Card:
    """일반 카드 단축 생성."""
    return Card.normal(rank, suit)


phoenix = Card.phoenix
dragon = Card.dragon
dog = Card.dog
mahjong = Card.mahjong


# ══════════════════════════════════════════════════════════════════
#  classify 테스트
# ══════════════════════════════════════════════════════════════════


class TestClassifyEmpty:
    def test_empty_list(self) -> None:
        assert HandValidator.classify([]) is None

    def test_none_for_invalid(self) -> None:
        # 서로 다른 rank 2장 (Phoenix 없이)
        assert HandValidator.classify([c(3), c(7)]) is None


# ── Single ──────────────────────────────────────────────────────


class TestClassifySingle:
    def test_normal_single(self) -> None:
        assert HandValidator.classify([c(5)]) == HandType.SINGLE

    def test_mahjong_single(self) -> None:
        assert HandValidator.classify([mahjong()]) == HandType.SINGLE

    def test_dragon_single(self) -> None:
        assert HandValidator.classify([dragon()]) == HandType.SINGLE

    def test_dog_single(self) -> None:
        assert HandValidator.classify([dog()]) == HandType.SINGLE

    def test_phoenix_single(self) -> None:
        assert HandValidator.classify([phoenix()]) == HandType.SINGLE


# ── Dog/Dragon 제약 ─────────────────────────────────────────────


class TestDogDragonRestriction:
    """Dog, Dragon은 싱글로만 낼 수 있다."""

    def test_dog_in_pair_invalid(self) -> None:
        assert HandValidator.classify([dog(), c(5)]) is None

    def test_dog_in_triple_invalid(self) -> None:
        assert HandValidator.classify([dog(), c(5), c(5, S)]) is None

    def test_dragon_in_pair_invalid(self) -> None:
        assert HandValidator.classify([dragon(), c(5)]) is None

    def test_dragon_in_straight_invalid(self) -> None:
        cards = [dragon(), c(10), c(11), c(12), c(13)]
        assert HandValidator.classify(cards) is None


# ── Pair ────────────────────────────────────────────────────────


class TestClassifyPair:
    def test_normal_pair(self) -> None:
        assert HandValidator.classify([c(7), c(7, S)]) == HandType.PAIR

    def test_phoenix_pair(self) -> None:
        assert HandValidator.classify([phoenix(), c(9)]) == HandType.PAIR

    def test_different_ranks_not_pair(self) -> None:
        assert HandValidator.classify([c(3), c(4)]) is None


# ── Triple ──────────────────────────────────────────────────────


class TestClassifyTriple:
    def test_normal_triple(self) -> None:
        assert HandValidator.classify([c(8), c(8, S), c(8, P)]) == HandType.TRIPLE

    def test_phoenix_triple(self) -> None:
        assert HandValidator.classify([phoenix(), c(6), c(6, S)]) == HandType.TRIPLE

    def test_phoenix_with_different_ranks_not_triple(self) -> None:
        assert HandValidator.classify([phoenix(), c(6), c(7)]) is None

    def test_two_cards_not_triple(self) -> None:
        assert HandValidator.classify([c(5), c(5, S), c(6)]) is None


# ── Full House ──────────────────────────────────────────────────


class TestClassifyFullHouse:
    def test_normal_full_house(self) -> None:
        cards = [c(10), c(10, S), c(10, P), c(4), c(4, S)]
        assert HandValidator.classify(cards) == HandType.FULL_HOUSE

    def test_phoenix_makes_2_2_into_full_house(self) -> None:
        # 2+2+Phoenix → 3+2
        cards = [phoenix(), c(9), c(9, S), c(5), c(5, S)]
        assert HandValidator.classify(cards) == HandType.FULL_HOUSE

    def test_phoenix_makes_3_1_into_full_house(self) -> None:
        # 3+1+Phoenix → 3+2
        cards = [phoenix(), c(7), c(7, S), c(7, P), c(3)]
        assert HandValidator.classify(cards) == HandType.FULL_HOUSE

    def test_four_plus_one_not_full_house(self) -> None:
        cards = [c(8), c(8, S), c(8, P), c(8, T), c(3)]
        assert HandValidator.classify(cards) != HandType.FULL_HOUSE

    def test_all_different_not_full_house(self) -> None:
        cards = [c(2), c(3), c(4), c(5), c(6)]
        # 이것은 스트레이트
        assert HandValidator.classify(cards) != HandType.FULL_HOUSE


# ── Straight ────────────────────────────────────────────────────


class TestClassifyStraight:
    def test_basic_5_card_straight(self) -> None:
        cards = [c(3), c(4, S), c(5, P), c(6, T), c(7)]
        assert HandValidator.classify(cards) == HandType.STRAIGHT

    def test_6_card_straight(self) -> None:
        cards = [c(5), c(6, S), c(7, P), c(8, T), c(9), c(10, S)]
        assert HandValidator.classify(cards) == HandType.STRAIGHT

    def test_mahjong_in_straight(self) -> None:
        # 1-2-3-4-5
        cards = [mahjong(), c(2), c(3, S), c(4, P), c(5, T)]
        assert HandValidator.classify(cards) == HandType.STRAIGHT

    def test_ace_high_straight(self) -> None:
        cards = [c(10), c(11, S), c(12, P), c(13, T), c(14)]
        assert HandValidator.classify(cards) == HandType.STRAIGHT

    def test_phoenix_fills_gap(self) -> None:
        # 3-_-5-6-7 → Phoenix가 4를 채움
        cards = [phoenix(), c(3), c(5, S), c(6, P), c(7, T)]
        assert HandValidator.classify(cards) == HandType.STRAIGHT

    def test_phoenix_extends_top(self) -> None:
        # 3-4-5-6-Phoenix → Phoenix가 7이 됨
        cards = [phoenix(), c(3), c(4, S), c(5, P), c(6, T)]
        assert HandValidator.classify(cards) == HandType.STRAIGHT

    def test_duplicate_rank_not_straight(self) -> None:
        cards = [c(3), c(3, S), c(4), c(5, P), c(6)]
        assert HandValidator.classify(cards) is None

    def test_4_cards_not_straight(self) -> None:
        cards = [c(3), c(4, S), c(5, P), c(6, T)]
        assert HandValidator.classify(cards) is None

    def test_gap_too_large_not_straight(self) -> None:
        cards = [c(3), c(4, S), c(5, P), c(8, T), c(9)]
        assert HandValidator.classify(cards) is None

    def test_ace_is_high_only(self) -> None:
        # A-2-3-4-5 → Ace=14이므로 연속이 아님
        cards = [c(14), c(2, S), c(3, P), c(4, T), c(5)]
        assert HandValidator.classify(cards) is None


# ── Straight Flush (폭탄) ──────────────────────────────────────


class TestClassifyStraightFlush:
    def test_basic_straight_flush(self) -> None:
        cards = [c(5, J), c(6, J), c(7, J), c(8, J), c(9, J)]
        assert HandValidator.classify(cards) == HandType.STRAIGHT_FLUSH

    def test_6_card_straight_flush(self) -> None:
        cards = [c(3, S), c(4, S), c(5, S), c(6, S), c(7, S), c(8, S)]
        assert HandValidator.classify(cards) == HandType.STRAIGHT_FLUSH

    def test_mixed_suit_not_straight_flush(self) -> None:
        cards = [c(5, J), c(6, J), c(7, J), c(8, J), c(9, S)]
        result = HandValidator.classify(cards)
        assert result == HandType.STRAIGHT  # 스트레이트이긴 함

    def test_phoenix_cannot_make_straight_flush(self) -> None:
        cards = [phoenix(), c(5, J), c(6, J), c(7, J), c(8, J)]
        result = HandValidator.classify(cards)
        # Phoenix 포함이므로 SF 불가 → 일반 스트레이트
        assert result == HandType.STRAIGHT

    def test_mahjong_cannot_be_in_straight_flush(self) -> None:
        # Mahjong은 특수 카드 → suit 없음 → SF 불가
        cards = [mahjong(), c(2, J), c(3, J), c(4, J), c(5, J)]
        result = HandValidator.classify(cards)
        assert result == HandType.STRAIGHT


# ── Four of a Kind (폭탄) ──────────────────────────────────────


class TestClassifyFourOfAKind:
    def test_basic_four_of_a_kind(self) -> None:
        cards = [c(9, J), c(9, S), c(9, P), c(9, T)]
        assert HandValidator.classify(cards) == HandType.FOUR_OF_A_KIND

    def test_phoenix_cannot_make_four_of_a_kind(self) -> None:
        # Phoenix + 3장 = 4장이지만 폭탄 불가
        cards = [phoenix(), c(9, J), c(9, S), c(9, P)]
        assert HandValidator.classify(cards) is None


# ── Pair Sequence ──────────────────────────────────────────────


class TestClassifyPairSequence:
    def test_basic_pair_sequence(self) -> None:
        # 3-3-4-4
        cards = [c(3), c(3, S), c(4), c(4, S)]
        assert HandValidator.classify(cards) == HandType.PAIR_SEQUENCE

    def test_three_pair_sequence(self) -> None:
        # 5-5-6-6-7-7
        cards = [c(5), c(5, S), c(6), c(6, S), c(7), c(7, S)]
        assert HandValidator.classify(cards) == HandType.PAIR_SEQUENCE

    def test_phoenix_pair_sequence(self) -> None:
        # Phoenix + 3 + 4-4 → 3-3-4-4
        cards = [phoenix(), c(3), c(4), c(4, S)]
        assert HandValidator.classify(cards) == HandType.PAIR_SEQUENCE

    def test_non_consecutive_not_pair_sequence(self) -> None:
        # 3-3-5-5 (4가 빠짐) — 비인접
        cards = [c(3), c(3, S), c(5), c(5, S)]
        assert HandValidator.classify(cards) is None

    def test_non_adjacent_two_pair_not_pair_sequence(self) -> None:
        # 2-2-A-A — 비인접 투페어
        cards = [c(2), c(2, S), c(14), c(14, S)]
        assert HandValidator.classify(cards) is None

    def test_odd_count_not_pair_sequence(self) -> None:
        cards = [c(3), c(3, S), c(4), c(4, S), c(5)]
        assert HandValidator.classify(cards) is None


# ══════════════════════════════════════════════════════════════════
#  can_beat 테스트
# ══════════════════════════════════════════════════════════════════


class TestCanBeatSingle:
    """싱글 비교."""

    def test_higher_beats_lower(self) -> None:
        assert HandValidator.can_beat([c(5)], [c(8)]) is True

    def test_lower_cannot_beat_higher(self) -> None:
        assert HandValidator.can_beat([c(8)], [c(5)]) is False

    def test_same_rank_cannot_beat(self) -> None:
        assert HandValidator.can_beat([c(7)], [c(7, S)]) is False

    def test_dragon_beats_ace(self) -> None:
        assert HandValidator.can_beat([c(14)], [dragon()]) is True

    def test_dragon_beats_phoenix(self) -> None:
        assert HandValidator.can_beat([phoenix()], [dragon()]) is True

    def test_nothing_beats_dragon_single(self) -> None:
        # 일반 카드로 Dragon 싱글을 이길 수 없다
        assert HandValidator.can_beat([dragon()], [c(14)]) is False

    def test_phoenix_beats_by_half(self) -> None:
        # Phoenix는 현재 카드 +0.5
        assert HandValidator.can_beat([c(10)], [phoenix()]) is True

    def test_phoenix_beats_ace(self) -> None:
        assert HandValidator.can_beat([c(14)], [phoenix()]) is True

    def test_phoenix_cannot_beat_dragon(self) -> None:
        assert HandValidator.can_beat([dragon()], [phoenix()]) is False

    def test_mahjong_can_be_beaten(self) -> None:
        assert HandValidator.can_beat([mahjong()], [c(2)]) is True

    def test_card_after_phoenix(self) -> None:
        # Phoenix가 테이블 위에 있을 때 (base_rank=1.5)
        # rank 2 이상이면 이김
        assert HandValidator.can_beat([phoenix()], [c(2)]) is True


class TestCanBeatPair:
    """페어 비교."""

    def test_higher_pair_beats(self) -> None:
        assert HandValidator.can_beat(
            [c(5), c(5, S)], [c(8), c(8, S)]
        ) is True

    def test_lower_pair_cannot_beat(self) -> None:
        assert HandValidator.can_beat(
            [c(8), c(8, S)], [c(5), c(5, S)]
        ) is False

    def test_phoenix_pair_beats(self) -> None:
        # Phoenix+9 페어 vs 7-7 → 9 > 7
        assert HandValidator.can_beat(
            [c(7), c(7, S)], [phoenix(), c(9)]
        ) is True

    def test_pair_cannot_beat_single(self) -> None:
        assert HandValidator.can_beat([c(3)], [c(8), c(8, S)]) is False


class TestCanBeatTriple:
    """트리플 비교."""

    def test_higher_triple_beats(self) -> None:
        assert HandValidator.can_beat(
            [c(6), c(6, S), c(6, P)],
            [c(9), c(9, S), c(9, P)]
        ) is True

    def test_phoenix_triple_beats(self) -> None:
        assert HandValidator.can_beat(
            [c(6), c(6, S), c(6, P)],
            [phoenix(), c(10), c(10, S)]
        ) is True


class TestCanBeatFullHouse:
    """풀하우스 비교."""

    def test_higher_triple_part_wins(self) -> None:
        current = [c(5), c(5, S), c(5, P), c(3), c(3, S)]
        played = [c(8), c(8, S), c(8, P), c(2), c(2, S)]
        assert HandValidator.can_beat(current, played) is True

    def test_lower_triple_part_loses(self) -> None:
        current = [c(8), c(8, S), c(8, P), c(2), c(2, S)]
        played = [c(5), c(5, S), c(5, P), c(3), c(3, S)]
        assert HandValidator.can_beat(current, played) is False


class TestCanBeatStraight:
    """스트레이트 비교."""

    def test_higher_straight_beats(self) -> None:
        current = [c(3), c(4, S), c(5, P), c(6, T), c(7)]
        played = [c(5), c(6, S), c(7, P), c(8, T), c(9)]
        assert HandValidator.can_beat(current, played) is True

    def test_same_length_required(self) -> None:
        current = [c(3), c(4, S), c(5, P), c(6, T), c(7)]
        played = [c(4), c(5, S), c(6, P), c(7, T), c(8), c(9, S)]
        # 길이 다르면 비교 불가
        assert HandValidator.can_beat(current, played) is False

    def test_phoenix_straight_beats(self) -> None:
        current = [c(3), c(4, S), c(5, P), c(6, T), c(7)]
        # Phoenix + 6-7-8-9 → 5(or 10)-6-7-8-9, top=10
        played = [phoenix(), c(6), c(7, S), c(8, P), c(9, T)]
        assert HandValidator.can_beat(current, played) is True


class TestCanBeatPairSequence:
    """연속 페어 비교."""

    def test_higher_pair_sequence_beats(self) -> None:
        current = [c(3), c(3, S), c(4), c(4, S)]
        played = [c(5), c(5, S), c(6), c(6, S)]
        assert HandValidator.can_beat(current, played) is True

    def test_same_length_required(self) -> None:
        current = [c(3), c(3, S), c(4), c(4, S)]
        played = [c(5), c(5, S), c(6), c(6, S), c(7), c(7, S)]
        assert HandValidator.can_beat(current, played) is False


# ── 폭탄(Bomb) 테스트 ──────────────────────────────────────────


class TestCanBeatBomb:
    """폭탄 규칙 테스트."""

    def test_four_of_a_kind_beats_single(self) -> None:
        assert HandValidator.can_beat(
            [c(14)], [c(2, J), c(2, S), c(2, P), c(2, T)]
        ) is True

    def test_four_of_a_kind_beats_pair(self) -> None:
        assert HandValidator.can_beat(
            [c(14), c(14, S)],
            [c(3, J), c(3, S), c(3, P), c(3, T)]
        ) is True

    def test_four_of_a_kind_beats_straight(self) -> None:
        current = [c(10), c(11, S), c(12, P), c(13, T), c(14)]
        played = [c(2, J), c(2, S), c(2, P), c(2, T)]
        assert HandValidator.can_beat(current, played) is True

    def test_four_of_a_kind_beats_full_house(self) -> None:
        current = [c(14), c(14, S), c(14, P), c(13), c(13, S)]
        played = [c(2, J), c(2, S), c(2, P), c(2, T)]
        assert HandValidator.can_beat(current, played) is True

    def test_higher_four_of_a_kind_beats_lower(self) -> None:
        assert HandValidator.can_beat(
            [c(5, J), c(5, S), c(5, P), c(5, T)],
            [c(9, J), c(9, S), c(9, P), c(9, T)]
        ) is True

    def test_lower_four_of_a_kind_loses(self) -> None:
        assert HandValidator.can_beat(
            [c(9, J), c(9, S), c(9, P), c(9, T)],
            [c(5, J), c(5, S), c(5, P), c(5, T)]
        ) is False

    def test_straight_flush_beats_four_of_a_kind(self) -> None:
        four = [c(14, J), c(14, S), c(14, P), c(14, T)]
        sf = [c(2, J), c(3, J), c(4, J), c(5, J), c(6, J)]
        assert HandValidator.can_beat(four, sf) is True

    def test_four_of_a_kind_cannot_beat_straight_flush(self) -> None:
        sf = [c(2, J), c(3, J), c(4, J), c(5, J), c(6, J)]
        four = [c(14, J), c(14, S), c(14, P), c(14, T)]
        assert HandValidator.can_beat(sf, four) is False

    def test_straight_flush_beats_single(self) -> None:
        assert HandValidator.can_beat(
            [dragon()],
            [c(2, J), c(3, J), c(4, J), c(5, J), c(6, J)]
        ) is True

    def test_higher_straight_flush_beats_lower(self) -> None:
        low_sf = [c(3, S), c(4, S), c(5, S), c(6, S), c(7, S)]
        high_sf = [c(8, J), c(9, J), c(10, J), c(11, J), c(12, J)]
        assert HandValidator.can_beat(low_sf, high_sf) is True

    def test_longer_straight_flush_beats_shorter(self) -> None:
        short_sf = [c(8, S), c(9, S), c(10, S), c(11, S), c(12, S)]
        long_sf = [c(3, J), c(4, J), c(5, J), c(6, J), c(7, J), c(8, J)]
        assert HandValidator.can_beat(short_sf, long_sf) is True

    def test_non_bomb_cannot_beat_bomb(self) -> None:
        four = [c(3, J), c(3, S), c(3, P), c(3, T)]
        straight = [c(10), c(11, S), c(12, P), c(13, T), c(14)]
        assert HandValidator.can_beat(four, straight) is False

    def test_bomb_beats_dragon_single(self) -> None:
        assert HandValidator.can_beat(
            [dragon()],
            [c(2, J), c(2, S), c(2, P), c(2, T)]
        ) is True


# ── 교차 유형 비교 불가 ────────────────────────────────────────


class TestCanBeatCrossType:
    """서로 다른 패 유형은 비교할 수 없다 (폭탄 제외)."""

    def test_single_vs_pair(self) -> None:
        assert HandValidator.can_beat([c(3)], [c(14), c(14, S)]) is False

    def test_pair_vs_triple(self) -> None:
        assert HandValidator.can_beat(
            [c(3), c(3, S)], [c(14), c(14, S), c(14, P)]
        ) is False

    def test_triple_vs_full_house(self) -> None:
        assert HandValidator.can_beat(
            [c(3), c(3, S), c(3, P)],
            [c(14), c(14, S), c(14, P), c(2), c(2, S)]
        ) is False

    def test_straight_vs_pair_sequence(self) -> None:
        straight = [c(3), c(4, S), c(5, P), c(6, T), c(7), c(8, S)]
        pair_seq = [c(10), c(10, S), c(11), c(11, S), c(12), c(12, S)]
        assert HandValidator.can_beat(straight, pair_seq) is False

    def test_invalid_hand_returns_false(self) -> None:
        # 유효하지 않은 패는 이길 수 없다
        assert HandValidator.can_beat([c(3)], [c(5), c(7)]) is False
        assert HandValidator.can_beat([c(5), c(7)], [c(3)]) is False


# ── Phoenix 와일드카드 엣지 케이스 ─────────────────────────────


class TestPhoenixWildcard:
    """Phoenix 와일드카드 다양한 상황."""

    def test_phoenix_single_vs_low_card(self) -> None:
        # Phoenix 싱글 vs 3 → 3.5 > 3
        assert HandValidator.can_beat([c(3)], [phoenix()]) is True

    def test_phoenix_in_full_house_2_2(self) -> None:
        # Phoenix + 9-9 + 5-5 → 풀하우스 (9가 트리플)
        cards = [phoenix(), c(9), c(9, S), c(5), c(5, S)]
        assert HandValidator.classify(cards) == HandType.FULL_HOUSE

    def test_phoenix_in_straight_middle(self) -> None:
        # 3-_-5-6-7 → Phoenix가 4를 채움
        cards = [c(3), phoenix(), c(5, S), c(6, P), c(7, T)]
        assert HandValidator.classify(cards) == HandType.STRAIGHT

    def test_phoenix_pair_strength(self) -> None:
        # Phoenix+10 페어 vs 9-9 → 10 > 9
        assert HandValidator.can_beat(
            [c(9), c(9, S)], [phoenix(), c(10)]
        ) is True

    def test_phoenix_pair_cannot_beat_higher(self) -> None:
        # Phoenix+5 페어 vs 8-8 → 5 < 8
        assert HandValidator.can_beat(
            [c(8), c(8, S)], [phoenix(), c(5)]
        ) is False


# ══════════════════════════════════════════════════════════════════
#  없는 조합 검증 (플러쉬, 비인접 투페어)
# ══════════════════════════════════════════════════════════════════


class TestInvalidCombinations:
    """유효하지 않은 조합은 None을 반환해야 한다."""

    def test_flush_not_valid(self) -> None:
        """같은 슈트 비연속 5장은 플러쉬가 아님 → 유효 조합 없음."""
        cards = [c(2, J), c(5, J), c(8, J), c(10, J), c(13, J)]
        assert HandValidator.classify(cards) is None

    def test_flush_4_cards_not_valid(self) -> None:
        """같은 슈트 비연속 4장은 유효 조합 없음."""
        cards = [c(2, J), c(5, J), c(8, J), c(13, J)]
        assert HandValidator.classify(cards) is None

    def test_non_adjacent_two_pair_4_cards(self) -> None:
        """(3,3,7,7) 비인접 투페어 → 유효하지 않음."""
        cards = [c(3), c(3, S), c(7), c(7, S)]
        assert HandValidator.classify(cards) is None

    def test_non_adjacent_two_pair_6_cards(self) -> None:
        """(3,3,7,7,10,10) 비인접 → 유효하지 않음."""
        cards = [c(3), c(3, S), c(7), c(7, S), c(10), c(10, S)]
        assert HandValidator.classify(cards) is None


# ══════════════════════════════════════════════════════════════════
#  Phoenix 와일드카드 제한 검증
# ══════════════════════════════════════════════════════════════════


class TestPhoenixBombRestriction:
    """Phoenix는 폭탄(포카드/스티플)에 사용 불가."""

    def test_phoenix_three_of_kind_not_four_bomb(self) -> None:
        """Phoenix + 같은 rank 3장 = 포카드 폭탄 아님."""
        cards = [phoenix(), c(9, J), c(9, S), c(9, P)]
        assert HandValidator.classify(cards) is None

    def test_phoenix_in_straight_flush_not_bomb(self) -> None:
        """Phoenix + 같은 슈트 4장 연속 = 스티플 폭탄 아님, 스트레이트."""
        cards = [phoenix(), c(5, J), c(6, J), c(7, J), c(8, J)]
        result = HandValidator.classify(cards)
        assert result == HandType.STRAIGHT
        assert result != HandType.STRAIGHT_FLUSH

    def test_phoenix_in_straight_flush_6_not_bomb(self) -> None:
        """Phoenix + 같은 슈트 5장 연속 = 스티플 폭탄 아님, 스트레이트."""
        cards = [phoenix(), c(3, S), c(4, S), c(5, S), c(6, S), c(7, S)]
        result = HandValidator.classify(cards)
        assert result == HandType.STRAIGHT
        assert result != HandType.STRAIGHT_FLUSH


# ══════════════════════════════════════════════════════════════════
#  Mahjong 스트레이트 검증
# ══════════════════════════════════════════════════════════════════


class TestMahjongStraight:
    """Mahjong(1)은 스트레이트 맨 앞에만 사용 가능."""

    def test_mahjong_1_2_3_4_5(self) -> None:
        cards = [mahjong(), c(2), c(3, S), c(4, P), c(5, T)]
        assert HandValidator.classify(cards) == HandType.STRAIGHT

    def test_mahjong_1_2_3_4_5_6_7(self) -> None:
        """7장 Mahjong 스트레이트."""
        cards = [mahjong(), c(2), c(3, S), c(4, P), c(5), c(6, T), c(7)]
        assert HandValidator.classify(cards) == HandType.STRAIGHT

    def test_mahjong_phoenix_straight(self) -> None:
        """Mahjong + Phoenix로 스트레이트 (1-Ph(2)-3-4-5)."""
        cards = [mahjong(), phoenix(), c(3, S), c(4, P), c(5, T)]
        assert HandValidator.classify(cards) == HandType.STRAIGHT

    def test_mahjong_not_in_straight_flush(self) -> None:
        """Mahjong은 특수 카드 → 스티플에 포함 불가."""
        cards = [mahjong(), c(2, J), c(3, J), c(4, J), c(5, J)]
        result = HandValidator.classify(cards)
        assert result == HandType.STRAIGHT
        assert result != HandType.STRAIGHT_FLUSH


# ══════════════════════════════════════════════════════════════════
#  can_beat 강도 비교 추가 검증
# ══════════════════════════════════════════════════════════════════


class TestCanBeatStrengthComparison:
    """각 조합별 강도 비교 규칙 검증."""

    def test_pair_2_loses_to_pair_3(self) -> None:
        assert HandValidator.can_beat(
            [c(2), c(2, S)], [c(3), c(3, S)]
        ) is True

    def test_pair_a_beats_pair_k(self) -> None:
        assert HandValidator.can_beat(
            [c(13), c(13, S)], [c(14), c(14, S)]
        ) is True

    def test_triple_strength(self) -> None:
        assert HandValidator.can_beat(
            [c(5), c(5, S), c(5, P)],
            [c(6), c(6, S), c(6, P)]
        ) is True

    def test_full_house_triple_rank_matters(self) -> None:
        """풀하우스 강도는 트리플 rank으로만 비교."""
        # 333+AA vs 444+22 → 444가 이김 (트리플 4 > 3)
        current = [c(3), c(3, S), c(3, P), c(14), c(14, S)]
        played = [c(4), c(4, S), c(4, P), c(2), c(2, S)]
        assert HandValidator.can_beat(current, played) is True

    def test_straight_same_length_higher_top(self) -> None:
        current = [c(2), c(3, S), c(4, P), c(5, T), c(6)]
        played = [c(3), c(4, S), c(5, P), c(6, T), c(7)]
        assert HandValidator.can_beat(current, played) is True

    def test_pair_seq_same_length_higher_top(self) -> None:
        current = [c(2), c(2, S), c(3), c(3, S)]
        played = [c(3, P), c(3, T), c(4), c(4, S)]
        assert HandValidator.can_beat(current, played) is True

    def test_pair_seq_different_length_cannot_beat(self) -> None:
        """연속 페어 길이가 다르면 비교 불가."""
        current = [c(3), c(3, S), c(4), c(4, S)]
        played = [c(5), c(5, S), c(6), c(6, S), c(7), c(7, S)]
        assert HandValidator.can_beat(current, played) is False

    def test_four_bomb_2222_less_than_3333(self) -> None:
        assert HandValidator.can_beat(
            [c(2, J), c(2, S), c(2, P), c(2, T)],
            [c(3, J), c(3, S), c(3, P), c(3, T)]
        ) is True

    def test_sf_length_beats_rank(self) -> None:
        """SF끼리: 길이 우선, 같은 길이면 rank."""
        short_high = [c(8, S), c(9, S), c(10, S), c(11, S), c(12, S)]
        long_low = [c(2, J), c(3, J), c(4, J), c(5, J), c(6, J), c(7, J)]
        assert HandValidator.can_beat(short_high, long_low) is True
