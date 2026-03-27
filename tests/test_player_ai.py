"""AI 전략 단위 테스트."""

import random

import pytest

from game.card import Card, SpecialCard, Suit
from game.hand import HandType, HandValidator
from game.player import (
    GameContext,
    Player,
    _card_strength,
    _count_special_seven,
    _is_special_seven,
)


J, S, P, T = Suit.JADE, Suit.SWORD, Suit.PAGODA, Suit.STAR


def c(rank: int, suit: Suit = J) -> Card:
    return Card.normal(rank, suit)


phoenix = Card.phoenix
dragon = Card.dragon
dog = Card.dog
mahjong = Card.mahjong


def make_player(
    cards: list[Card], team: int = 0, name: str = "AI",
) -> Player:
    p = Player(name=name, team=team)
    p.receive_cards(cards)
    return p


def make_context(
    my_idx: int = 0,
    trick_winner_idx: int | None = None,
    teams: list[int] | None = None,
    tichu: list[bool] | None = None,
    grand_tichu: list[bool] | None = None,
    finished: list[bool] | None = None,
    card_counts: list[int] | None = None,
) -> GameContext:
    return GameContext(
        my_idx=my_idx,
        trick_winner_idx=trick_winner_idx,
        players_team=teams or [0, 1, 0, 1],
        players_tichu=tichu or [False] * 4,
        players_grand_tichu=grand_tichu or [False] * 4,
        players_finished=finished or [False] * 4,
        players_card_count=card_counts or [14] * 4,
    )


def _opponent_ctx() -> GameContext:
    """기본: 상대(P1)가 이기고 있어 플레이 필요."""
    return make_context(my_idx=0, trick_winner_idx=1)


# ══════════════════════════════════════════════════════════
#  특수 카드 7개 판별
# ══════════════════════════════════════════════════════════


class TestSpecialSeven:
    def test_dragon_is_special(self) -> None:
        assert _is_special_seven(dragon()) is True

    def test_phoenix_is_special(self) -> None:
        assert _is_special_seven(phoenix()) is True

    def test_mahjong_is_special(self) -> None:
        assert _is_special_seven(mahjong()) is True

    def test_aces_are_special(self) -> None:
        for suit in Suit:
            assert _is_special_seven(Card.normal(14, suit)) is True

    def test_king_not_special(self) -> None:
        assert _is_special_seven(c(13)) is False

    def test_count(self) -> None:
        cards = [dragon(), phoenix(), mahjong(), c(14, J), c(14, S), c(13)]
        assert _count_special_seven(cards) == 5


# ══════════════════════════════════════════════════════════
#  Grand Tichu 선언 (특수 7개 중 4개 이상)
# ══════════════════════════════════════════════════════════


class TestGrandTichuDecision:
    def test_four_special_declares(self) -> None:
        p = make_player([
            dragon(), phoenix(), mahjong(), c(14, J),
            c(2), c(3), c(4), c(5),
        ])
        assert p.decide_grand_tichu() is True

    def test_three_special_does_not_declare(self) -> None:
        p = make_player([
            dragon(), phoenix(), mahjong(),
            c(2), c(3), c(4), c(5), c(6),
        ])
        assert p.decide_grand_tichu() is False

    def test_all_four_aces(self) -> None:
        p = make_player([
            c(14, J), c(14, S), c(14, P), c(14, T),
            c(2), c(3), c(4), c(5),
        ])
        assert p.decide_grand_tichu() is True

    def test_zero_special(self) -> None:
        p = make_player([c(r) for r in range(2, 10)])
        assert p.decide_grand_tichu() is False


# ══════════════════════════════════════════════════════════
#  Small Tichu 선언 (특수 7개 중 3개 이상)
# ══════════════════════════════════════════════════════════


class TestSmallTichuDecision:
    def test_three_special_declares(self) -> None:
        cards = [dragon(), phoenix(), mahjong()] + [c(r) for r in range(2, 13)]
        p = make_player(cards)
        assert p.decide_tichu() is True

    def test_two_special_does_not(self) -> None:
        cards = [dragon(), phoenix()] + [c(r) for r in range(2, 14)]
        p = make_player(cards)
        assert p.decide_tichu() is False

    def test_grand_tichu_blocks(self) -> None:
        cards = [dragon(), phoenix(), mahjong()] + [c(r) for r in range(2, 13)]
        p = make_player(cards)
        p.grand_tichu_called = True
        assert p.decide_tichu() is False


# ══════════════════════════════════════════════════════════
#  패 교환 전략
# ══════════════════════════════════════════════════════════


class TestCardPassing:
    def test_dog_goes_to_right(self) -> None:
        """Dog → 오른쪽 상대에게."""
        cards = [dog()] + [c(r) for r in range(2, 15)]
        p = make_player(cards)
        left, right, opposite = p.select_pass_cards()
        assert right.special == SpecialCard.DOG

    def test_mahjong_never_passed(self) -> None:
        """Mahjong은 절대 전달 안 함."""
        cards = [mahjong()] + [c(r) for r in range(2, 14)] + [c(14, S)]
        p = make_player(cards)
        left, right, opposite = p.select_pass_cards()
        assert left.special != SpecialCard.MAHJONG
        assert right.special != SpecialCard.MAHJONG
        assert opposite.special != SpecialCard.MAHJONG

    def test_case_c_strongest_to_teammate(self) -> None:
        """특수 카드 2개 이하 → 팀원에게 가장 강한 카드."""
        # Dragon + Phoenix = 특수 2개 → Case C
        cards = [dragon(), phoenix()] + [c(r) for r in range(2, 14)]
        p = make_player(cards)
        left, right, opposite = p.select_pass_cards()
        # Dragon(strength=25)이 팀원에게 감
        assert opposite.special == SpecialCard.DRAGON

    def test_case_ab_weak_to_opponents(self) -> None:
        """특수 카드 3개 이상 → 상대에게 약한 카드들."""
        # Dragon + Phoenix + Mahjong + A♠ = 특수 4개 → Case A/B
        cards = [dragon(), phoenix(), mahjong(), c(14, J)] + [
            c(r) for r in range(2, 12)
        ]
        p = make_player(cards)
        left, right, opposite = p.select_pass_cards()
        pool = sorted(
            (x for x in cards
             if x.special != SpecialCard.DOG
             and x.special != SpecialCard.MAHJONG),
            key=_card_strength,
        )
        assert left == pool[0]   # 1번째 약한
        assert right == pool[1]  # 2번째 약한
        assert opposite == pool[2]  # 3번째 약한 (팀원)

    def test_case_ab_with_dog(self) -> None:
        """Dog 있고 특수 3개 이상 → Dog는 오른쪽, 나머지는 약한 순."""
        # Dog + Dragon + Phoenix + Mahjong = 특수 3개 (Dog 제외)
        cards = [dog(), dragon(), phoenix(), mahjong()] + [
            c(r) for r in range(2, 12)
        ]
        p = make_player(cards)
        left, right, opposite = p.select_pass_cards()
        assert right.special == SpecialCard.DOG
        # 나머지: Dog·Mahjong 제외한 가장 약한 2장
        pool = sorted(
            (x for x in cards
             if x.special != SpecialCard.DOG
             and x.special != SpecialCard.MAHJONG),
            key=_card_strength,
        )
        assert left == pool[0]
        assert opposite == pool[1]

    def test_case_c_with_dog(self) -> None:
        """Dog 있고 특수 2개 이하 → Dog 오른쪽, 팀원에게 최강."""
        # Dog + Phoenix = 특수 1개 (Dog 미포함), Phoenix만 → Case C
        cards = [dog(), phoenix()] + [c(r) for r in range(2, 14)]
        p = make_player(cards)
        left, right, opposite = p.select_pass_cards()
        assert right.special == SpecialCard.DOG
        # 팀원에게 가장 강한 카드 (Phoenix: strength=15)
        assert opposite.special == SpecialCard.PHOENIX


# ══════════════════════════════════════════════════════════
#  Tichu 인식 전략 (패스/플레이 판단)
# ══════════════════════════════════════════════════════════


class TestTichuAwareness:
    def test_my_tichu_never_pass(self) -> None:
        """내가 Tichu → 팀원이 이기고 있어도 패스 안 함."""
        p = make_player([c(14)])
        ctx = make_context(
            my_idx=0, trick_winner_idx=2,
            tichu=[True, False, False, False],
        )
        p.set_game_context(ctx)
        assert p._should_pass() is False

    def test_my_grand_tichu_never_pass(self) -> None:
        """내가 Grand Tichu → 패스 안 함."""
        p = make_player([c(14)])
        ctx = make_context(
            my_idx=0, trick_winner_idx=2,
            grand_tichu=[True, False, False, False],
        )
        p.set_game_context(ctx)
        assert p._should_pass() is False

    def test_teammate_tichu_always_pass(self) -> None:
        """팀원이 Tichu → 무조건 패스."""
        p = make_player([c(14)])
        ctx = make_context(
            my_idx=0, trick_winner_idx=1,
            tichu=[False, False, True, False],
        )
        p.set_game_context(ctx)
        assert p._should_pass() is True

    def test_opponent_tichu_winning_block(self) -> None:
        """상대 Tichu 선언자가 이기고 있음 → 막아야 함."""
        p = make_player([c(14)])
        ctx = make_context(
            my_idx=0, trick_winner_idx=1,
            tichu=[False, True, False, False],
        )
        p.set_game_context(ctx)
        assert p._should_pass() is False

    def test_opponent_tichu_other_opponent_winning_pass(self) -> None:
        """상대 Tichu인데 다른 상대가 이기고 있음 → 패스."""
        p = make_player([c(14)])
        ctx = make_context(
            my_idx=0, trick_winner_idx=3,
            tichu=[False, True, False, False],
        )
        p.set_game_context(ctx)
        assert p._should_pass() is True

    def test_opponent_tichu_teammate_winning_pass(self) -> None:
        """상대 Tichu인데 팀원이 이기고 있음 → 패스."""
        p = make_player([c(14)])
        ctx = make_context(
            my_idx=0, trick_winner_idx=2,
            tichu=[False, True, False, False],
        )
        p.set_game_context(ctx)
        assert p._should_pass() is True

    def test_no_tichu_teammate_winning_pass(self) -> None:
        """아무 Tichu 없음 + 팀원이 이기고 있음 → 패스."""
        p = make_player([c(14)])
        ctx = make_context(my_idx=0, trick_winner_idx=2)
        p.set_game_context(ctx)
        assert p._should_pass() is True

    def test_no_tichu_opponent_winning_play(self) -> None:
        """아무 Tichu 없음 + 상대가 이기고 있음 → 플레이."""
        p = make_player([c(14)])
        ctx = make_context(my_idx=0, trick_winner_idx=1)
        p.set_game_context(ctx)
        assert p._should_pass() is False

    def test_lead_no_trick_winner_no_pass(self) -> None:
        """선공 (trick_winner_idx=None) → 패스 판단 안 함."""
        p = make_player([c(14)])
        ctx = make_context(my_idx=0, trick_winner_idx=None)
        p.set_game_context(ctx)
        assert p._should_pass() is False

    def test_teammate_tichu_lead_dog(self) -> None:
        """팀원 Tichu → 선공 시 Dog로 턴 넘김."""
        p = make_player([dog(), c(3), c(5)])
        ctx = make_context(
            my_idx=0, trick_winner_idx=None,
            tichu=[False, False, True, False],
        )
        p.set_game_context(ctx)
        play = p.select_play(None)
        assert play is not None
        assert play[0].special == SpecialCard.DOG


# ══════════════════════════════════════════════════════════
#  조합 플레이
# ══════════════════════════════════════════════════════════


class TestCombinationPlay:
    def test_follow_pair_with_pair(self) -> None:
        p = make_player([c(5, J), c(5, S), c(9, J), c(9, S)])
        p.set_game_context(_opponent_ctx())
        play = p.select_play([c(3, J), c(3, S)], None)
        assert play is not None
        assert len(play) == 2
        assert HandValidator.classify(play) == HandType.PAIR
        assert all(int(x.rank) == 5 for x in play)

    def test_follow_triple_with_triple(self) -> None:
        p = make_player([
            c(6, J), c(6, S), c(6, P),
            c(10, J), c(10, S), c(10, P),
        ])
        p.set_game_context(_opponent_ctx())
        play = p.select_play([c(4, J), c(4, S), c(4, P)], None)
        assert play is not None
        assert len(play) == 3
        assert HandValidator.classify(play) == HandType.TRIPLE
        assert all(int(x.rank) == 6 for x in play)

    def test_follow_full_house(self) -> None:
        p = make_player([
            c(7, J), c(7, S), c(7, P), c(4, J), c(4, S), c(12, J),
        ])
        p.set_game_context(_opponent_ctx())
        table = [c(5, J), c(5, S), c(5, P), c(3, J), c(3, S)]
        play = p.select_play(table, None)
        assert play is not None
        assert len(play) == 5
        assert HandValidator.classify(play) == HandType.FULL_HOUSE

    def test_follow_straight(self) -> None:
        p = make_player([c(3), c(4), c(5, S), c(6), c(7), c(10)])
        p.set_game_context(_opponent_ctx())
        table = [c(2, S), c(3, S), c(4, P), c(5, T), c(6, S)]
        play = p.select_play(table, None)
        assert play is not None
        assert len(play) == 5
        assert HandValidator.classify(play) == HandType.STRAIGHT

    def test_follow_pair_sequence(self) -> None:
        p = make_player([c(6, J), c(6, S), c(7, J), c(7, S), c(10, J)])
        p.set_game_context(_opponent_ctx())
        table = [c(3, J), c(3, S), c(4, J), c(4, S)]
        play = p.select_play(table, None)
        assert play is not None
        assert len(play) == 4
        assert HandValidator.classify(play) == HandType.PAIR_SEQUENCE

    def test_plays_weakest_pair(self) -> None:
        """여러 페어 중 가장 약한 페어로 응답."""
        p = make_player([
            c(5, J), c(5, S), c(10, J), c(10, S), c(14, J), c(14, S),
        ])
        p.set_game_context(_opponent_ctx())
        play = p.select_play([c(3, J), c(3, S)], None)
        assert play is not None
        assert all(int(x.rank) == 5 for x in play)

    def test_phoenix_in_pair(self) -> None:
        """Phoenix + 카드 = 페어."""
        p = make_player([phoenix(), c(8, J), c(3, S)])
        p.set_game_context(_opponent_ctx())
        play = p.select_play([c(5, J), c(5, S)], None)
        assert play is not None
        assert len(play) == 2
        assert HandValidator.classify(play) == HandType.PAIR
        assert any(x.special == SpecialCard.PHOENIX for x in play)

    def test_phoenix_in_triple(self) -> None:
        """Phoenix + 페어 = 트리플."""
        p = make_player([phoenix(), c(8, J), c(8, S), c(3)])
        p.set_game_context(_opponent_ctx())
        play = p.select_play([c(5, J), c(5, S), c(5, P)], None)
        assert play is not None
        assert len(play) == 3
        assert HandValidator.classify(play) == HandType.TRIPLE
        assert any(x.special == SpecialCard.PHOENIX for x in play)

    def test_phoenix_fills_straight_gap(self) -> None:
        """Phoenix로 스트레이트 빈 자리 채움."""
        # Hand: Phoenix, 3, 4, 6, 7, 10
        # Table straight top=6, need top>6
        # Can make 3-4-Ph(5)-6-7 → top=7
        p = make_player([phoenix(), c(3), c(4), c(6), c(7), c(10)])
        p.set_game_context(_opponent_ctx())
        table = [c(2, S), c(3, S), c(4, P), c(5, T), c(6, T)]
        play = p.select_play(table, None)
        assert play is not None
        assert len(play) == 5
        assert HandValidator.classify(play) == HandType.STRAIGHT
        assert any(x.special == SpecialCard.PHOENIX for x in play)

    def test_no_matching_combo_passes(self) -> None:
        """이길 수 없으면 패스."""
        p = make_player([c(2), c(3)])
        p.set_game_context(_opponent_ctx())
        play = p.select_play([c(10, J), c(10, S)], None)
        assert play is None

    def test_pass_when_cannot_beat_single(self) -> None:
        """싱글도 이길 수 없으면 패스."""
        p = make_player([c(2), c(3)])
        p.set_game_context(_opponent_ctx())
        play = p.select_play([c(14, S)], 14.0)
        assert play is None


# ══════════════════════════════════════════════════════════
#  Phoenix 전략
# ══════════════════════════════════════════════════════════


class TestPhoenixStrategy:
    def test_phoenix_single_beats_ace(self) -> None:
        """상대 A → Phoenix 사용."""
        p = make_player([phoenix(), c(3)])
        p.set_game_context(_opponent_ctx())
        play = p.select_play([c(14, S)], 14.0)
        assert play is not None
        assert play[0].special == SpecialCard.PHOENIX

    def test_phoenix_not_used_against_king(self) -> None:
        """상대 K → A로 대응, Phoenix 아껴둠."""
        p = make_player([phoenix(), c(14)])
        p.set_game_context(_opponent_ctx())
        play = p.select_play([c(13, S)], 13.0)
        assert play is not None
        assert play[0].special != SpecialCard.PHOENIX
        assert int(play[0].rank) == 14

    def test_phoenix_not_wasted_on_low_single(self) -> None:
        """상대 5 → 일반 카드(8)로 대응."""
        p = make_player([phoenix(), c(8)])
        p.set_game_context(_opponent_ctx())
        play = p.select_play([c(5, S)], 5.0)
        assert play is not None
        assert int(play[0].rank) == 8

    def test_phoenix_not_used_when_only_option_but_not_ace(self) -> None:
        """일반 카드로 이길 수 없고 상대가 A가 아니면 Phoenix 미사용."""
        p = make_player([phoenix(), c(3)])
        p.set_game_context(_opponent_ctx())
        play = p.select_play([c(10, S)], 10.0)
        # Phoenix 싱글은 A만 잡으므로, 10에는 미사용
        # Dragon도 없으므로 패스
        assert play is None


# ══════════════════════════════════════════════════════════
#  Dragon 전략
# ══════════════════════════════════════════════════════════


class TestDragonStrategy:
    def test_dragon_beats_ace(self) -> None:
        """일반 카드로 못 이길 때 Dragon 사용."""
        p = make_player([dragon(), c(3)])
        p.set_game_context(_opponent_ctx())
        play = p.select_play([c(14, S)], 14.0)
        assert play is not None
        assert play[0].special == SpecialCard.DRAGON

    def test_dragon_not_used_when_normal_beats(self) -> None:
        """일반 카드로 이길 수 있으면 Dragon 아껴둠."""
        p = make_player([dragon(), c(14)])
        p.set_game_context(_opponent_ctx())
        play = p.select_play([c(10, S)], 10.0)
        assert play is not None
        assert play[0].special != SpecialCard.DRAGON
        assert int(play[0].rank) == 14

    def test_dragon_is_single_only(self) -> None:
        """Dragon은 싱글 최강이지만 페어에는 사용 불가."""
        p = make_player([dragon(), c(3)])
        p.set_game_context(_opponent_ctx())
        play = p.select_play([c(10, J), c(10, S)], None)
        # 페어를 이길 수 없으므로 패스
        assert play is None


# ══════════════════════════════════════════════════════════
#  폭탄 전략
# ══════════════════════════════════════════════════════════


class TestBombStrategy:
    def test_bomb_not_used_without_reason(self) -> None:
        """폭탄 사용 조건 미충족 시 폭탄 미사용."""
        p = make_player([
            c(5, J), c(5, S), c(5, P), c(5, T), c(3),
        ])
        ctx = make_context(my_idx=0, trick_winner_idx=1)
        p.set_game_context(ctx)
        # 테이블 페어(10) — 일반 페어로 이길 수 없음
        play = p.select_play([c(10, J), c(10, S)], None)
        # 폭탄 조건 미충족 → 패스 (should_use_bomb = False)
        assert play is None

    def test_bomb_used_when_my_tichu(self) -> None:
        """내가 Tichu → 폭탄 사용."""
        p = make_player([
            c(5, J), c(5, S), c(5, P), c(5, T), c(3),
        ])
        ctx = make_context(
            my_idx=0, trick_winner_idx=1,
            tichu=[True, False, False, False],
        )
        p.set_game_context(ctx)
        play = p.select_play([c(10, J), c(10, S)], None)
        assert play is not None
        assert len(play) == 4
        assert HandValidator.classify(play) == HandType.FOUR_OF_A_KIND

    def test_bomb_used_to_block_opponent_tichu(self) -> None:
        """상대 Tichu가 이기고 있을 때 폭탄 사용."""
        p = make_player([
            c(5, J), c(5, S), c(5, P), c(5, T), c(3),
        ])
        ctx = make_context(
            my_idx=0, trick_winner_idx=1,
            tichu=[False, True, False, False],
        )
        p.set_game_context(ctx)
        play = p.select_play([c(10, J), c(10, S)], None)
        assert play is not None
        assert HandValidator.classify(play) == HandType.FOUR_OF_A_KIND


# ══════════════════════════════════════════════════════════
#  Small Tichu 타이밍 (통합 테스트)
# ══════════════════════════════════════════════════════════


class TestSmallTichuTiming:
    def test_tichu_declared_before_first_play(self) -> None:
        """Small Tichu는 첫 카드를 내기 직전에 선언된다."""
        from game.game import Game

        game = Game()
        for p in game.players:
            p.reset()

        # P0: Mahjong + Dragon + A♠ + 일반 = 특수 3개 → ST 선언
        game.players[0].receive_cards([
            mahjong(), dragon(), c(14, J), c(2), c(3),
        ])
        game.players[1].receive_cards([c(5), c(6)])
        game.players[2].receive_cards([c(7), c(8)])
        game.players[3].receive_cards([c(9), c(10)])

        assert game.players[0].tichu_called is False
        game._play_tricks(start_idx=0)
        assert game.players[0].tichu_called is True

    def test_no_tichu_at_round_start(self) -> None:
        """라운드 시작 직후에는 Small Tichu 미선언 상태."""
        from game.game import Game

        game = Game()
        first, remaining = game._deal_cards()
        for p in game.players:
            p.reset()
        for i, p in enumerate(game.players):
            p.receive_cards(first[i])
        for p in game.players:
            if p.decide_grand_tichu():
                p.call_grand_tichu()
        for i, p in enumerate(game.players):
            p.receive_cards(remaining[i])
        # 이 시점에서 Small Tichu는 미선언
        for p in game.players:
            if not p.grand_tichu_called:
                assert p.tichu_called is False

    def test_grand_tichu_player_skips_small_tichu(self) -> None:
        """Grand Tichu 선언자는 Small Tichu 체크를 건너뛴다."""
        from game.game import Game

        game = Game()
        for p in game.players:
            p.reset()

        game.players[0].grand_tichu_called = True
        game.players[0].receive_cards([
            mahjong(), dragon(), c(14, J), c(14, S), c(2),
        ])
        game.players[1].receive_cards([c(5), c(6)])
        game.players[2].receive_cards([c(7), c(8)])
        game.players[3].receive_cards([c(9), c(10)])

        game._play_tricks(start_idx=0)
        # Grand Tichu가 있으므로 Small Tichu는 선언 안 됨
        assert game.players[0].tichu_called is False


# ══════════════════════════════════════════════════════════
#  리드 전략
# ══════════════════════════════════════════════════════════


class TestLeadStrategy:
    def test_mahjong_first(self) -> None:
        """Mahjong 보유 시 무조건 Mahjong 리드."""
        p = make_player([mahjong(), c(14), dragon()])
        ctx = make_context(my_idx=0)
        p.set_game_context(ctx)
        play = p.select_play(None)
        assert play is not None
        assert any(x.special == SpecialCard.MAHJONG for x in play)

    def test_dragon_not_lead_single(self) -> None:
        """Dragon은 싱글 리드에 사용 안 함 (일반 카드 있으면)."""
        p = make_player([dragon(), c(5), c(9)])
        ctx = make_context(my_idx=0)
        p.set_game_context(ctx)
        play = p.select_play(None)
        assert play is not None
        # Dragon 싱글이 아닌 일반 카드 또는 조합
        assert play[0].special != SpecialCard.DRAGON

    def test_only_special_left(self) -> None:
        """특수 카드만 남으면 아무거나 리드."""
        p = make_player([dragon()])
        ctx = make_context(my_idx=0)
        p.set_game_context(ctx)
        play = p.select_play(None)
        assert play is not None


# ══════════════════════════════════════════════════════════
#  리드 조합 우선순위
# ══════════════════════════════════════════════════════════


class TestLeadComboPriority:
    def test_lead_straight_over_pair(self) -> None:
        """스트레이트 > 페어 우선순위."""
        # 스트레이트 가능: 3-4-5-6-7, 페어 가능: 10-10
        p = make_player([
            c(3), c(4), c(5, S), c(6), c(7), c(10, J), c(10, S),
        ])
        ctx = make_context(my_idx=0)
        p.set_game_context(ctx)
        play = p.select_play(None)
        assert play is not None
        assert HandValidator.classify(play) == HandType.STRAIGHT

    def test_lead_pair_seq_over_triple(self) -> None:
        """연속 페어 > 트리플 우선순위."""
        p = make_player([
            c(3, J), c(3, S), c(4, J), c(4, S),
            c(8, J), c(8, S), c(8, P),
        ])
        ctx = make_context(my_idx=0)
        p.set_game_context(ctx)
        play = p.select_play(None)
        assert play is not None
        assert HandValidator.classify(play) == HandType.PAIR_SEQUENCE

    def test_lead_full_house_over_triple(self) -> None:
        """풀하우스 > 트리플 우선순위 (트리플+페어 가능 시)."""
        p = make_player([
            c(3, J), c(3, S), c(3, P),
            c(8, J), c(8, S), c(12),
        ])
        ctx = make_context(my_idx=0)
        p.set_game_context(ctx)
        play = p.select_play(None)
        assert play is not None
        assert HandValidator.classify(play) == HandType.FULL_HOUSE

    def test_lead_triple_when_no_pair(self) -> None:
        """페어 없으면 트리플 리드."""
        p = make_player([
            c(3, J), c(3, S), c(3, P), c(7), c(11),
        ])
        ctx = make_context(my_idx=0)
        p.set_game_context(ctx)
        play = p.select_play(None)
        assert play is not None
        assert HandValidator.classify(play) == HandType.TRIPLE

    def test_lead_pair_over_single(self) -> None:
        """페어 > 싱글 우선순위."""
        p = make_player([c(3, J), c(3, S), c(7), c(12)])
        ctx = make_context(my_idx=0)
        p.set_game_context(ctx)
        play = p.select_play(None)
        assert play is not None
        assert HandValidator.classify(play) == HandType.PAIR

    def test_lead_weak_combo_over_strong(self) -> None:
        """강한 카드(A) 미포함 조합 우선."""
        # 약한 페어: 3-3, 강한 페어: A-A
        p = make_player([
            c(3, J), c(3, S), c(14, J), c(14, S), c(7),
        ])
        ctx = make_context(my_idx=0)
        p.set_game_context(ctx)
        play = p.select_play(None)
        assert play is not None
        assert HandValidator.classify(play) == HandType.PAIR
        assert all(int(x.rank) == 3 for x in play)

    def test_lead_mahjong_straight(self) -> None:
        """Mahjong 포함 스트레이트 리드."""
        p = make_player([
            mahjong(), c(2), c(3, S), c(4), c(5), c(10),
        ])
        ctx = make_context(my_idx=0)
        p.set_game_context(ctx)
        play = p.select_play(None)
        assert play is not None
        assert HandValidator.classify(play) == HandType.STRAIGHT
        assert any(x.special == SpecialCard.MAHJONG for x in play)

    def test_mahjong_single_when_no_straight(self) -> None:
        """Mahjong 스트레이트 불가 시 Mahjong 싱글."""
        p = make_player([mahjong(), c(5), c(10)])
        ctx = make_context(my_idx=0)
        p.set_game_context(ctx)
        play = p.select_play(None)
        assert play is not None
        assert len(play) == 1
        assert play[0].special == SpecialCard.MAHJONG

    def test_lead_full_house(self) -> None:
        """풀하우스 리드 (스트레이트/연속페어 불가 시)."""
        p = make_player([
            c(3, J), c(3, S), c(3, P),
            c(5, J), c(5, S), c(12),
        ])
        ctx = make_context(my_idx=0)
        p.set_game_context(ctx)
        play = p.select_play(None)
        assert play is not None
        assert HandValidator.classify(play) == HandType.FULL_HOUSE

    def test_lead_single_fallback(self) -> None:
        """조합 불가 시 가장 약한 싱글 리드."""
        p = make_player([c(3), c(7), c(12)])
        ctx = make_context(my_idx=0)
        p.set_game_context(ctx)
        play = p.select_play(None)
        assert play is not None
        assert len(play) == 1
        assert int(play[0].rank) == 3

    def test_lead_strong_combo_when_only_option(self) -> None:
        """약한 조합 없으면 강한 카드 포함 조합 사용."""
        # A-A 페어만 가능 (약한 조합 없음)
        p = make_player([c(14, J), c(14, S), c(7)])
        ctx = make_context(my_idx=0)
        p.set_game_context(ctx)
        play = p.select_play(None)
        assert play is not None
        assert HandValidator.classify(play) == HandType.PAIR
        assert all(int(x.rank) == 14 for x in play)


# ══════════════════════════════════════════════════════════
#  통합: 전체 게임 실행
# ══════════════════════════════════════════════════════════


class TestIntegration:
    def test_game_runs_with_new_ai(self) -> None:
        """강화된 AI로 전체 게임이 정상 종료."""
        from game.game import Game

        for seed in range(10):
            random.seed(seed)
            game = Game()
            winner = game.run()
            assert winner in (0, 1)

    def test_round_scores_sum_correctly(self) -> None:
        """라운드 점수가 정상적으로 누적."""
        from game.game import Game

        random.seed(42)
        game = Game()
        scores = game.play_round()
        assert 0 in scores and 1 in scores
