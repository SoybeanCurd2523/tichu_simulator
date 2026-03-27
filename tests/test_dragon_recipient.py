"""Dragon 트릭 수령자 선택 테스트."""

from unittest.mock import patch

import pytest

from game.card import Card, SpecialCard, Suit
from game.game import Game
from game.hand import HandType, HandValidator
from game.human_player import HumanPlayer
from game.player import Player


J, S, P, T = Suit.JADE, Suit.SWORD, Suit.PAGODA, Suit.STAR


def c(rank: int, suit: Suit = J) -> Card:
    return Card.normal(rank, suit)


phoenix = Card.phoenix
dragon = Card.dragon
dog = Card.dog
mahjong = Card.mahjong


# ══════════════════════════════════════════════════════════════════
#  AI Dragon 수령자 전략
# ══════════════════════════════════════════════════════════════════


class TestAIDragonRecipient:
    """AI choose_dragon_recipient 전략 테스트."""

    def _make_player(self, cards: list[Card]) -> Player:
        p = Player(name="AI", team=0)
        p.receive_cards(cards)
        return p

    def test_prefers_fewer_cards(self) -> None:
        """손패가 적은 상대를 선택한다."""
        p = self._make_player([dragon()])
        opponents = [(1, "Opp_A", 3), (3, "Opp_B", 9)]
        result = p.choose_dragon_recipient(opponents, [])
        assert result == 1  # 3장인 Opp_A

    def test_prefers_fewer_cards_reversed(self) -> None:
        """순서와 무관하게 손패가 적은 쪽을 선택."""
        p = self._make_player([dragon()])
        opponents = [(3, "Opp_B", 9), (1, "Opp_A", 2)]
        result = p.choose_dragon_recipient(opponents, [])
        assert result == 1  # 2장인 Opp_A

    def test_tied_cards_stronger_trick_play(self) -> None:
        """손패 수 동률 → 트릭에서 강한 카드 낸 상대."""
        p = self._make_player([dragon()])
        opponents = [(1, "Opp_A", 5), (3, "Opp_B", 5)]
        trick_log = [
            (1, [c(3)]),   # Opp_A: 약한 카드
            (3, [c(14)]),  # Opp_B: 강한 카드 (A)
        ]
        result = p.choose_dragon_recipient(opponents, trick_log)
        assert result == 3  # 강한 카드 낸 Opp_B

    def test_tied_cards_no_trick_log(self) -> None:
        """손패 수 동률, 트릭 로그 없음 → 첫 번째 상대."""
        p = self._make_player([dragon()])
        opponents = [(1, "Opp_A", 5), (3, "Opp_B", 5)]
        result = p.choose_dragon_recipient(opponents, [])
        assert result == 1  # 첫 번째

    def test_tied_cards_only_one_in_trick(self) -> None:
        """동률, 한 상대만 트릭에 참여 → 그 상대 선택."""
        p = self._make_player([dragon()])
        opponents = [(1, "Opp_A", 5), (3, "Opp_B", 5)]
        trick_log = [(3, [c(7)])]  # Opp_B만 참여
        result = p.choose_dragon_recipient(opponents, trick_log)
        assert result == 3


# ══════════════════════════════════════════════════════════════════
#  Game._choose_dragon_recipient 통합
# ══════════════════════════════════════════════════════════════════


class TestGameDragonRecipient:
    """Game이 올바르게 Player에 위임하는지 테스트."""

    def test_single_active_opponent_auto(self) -> None:
        """활성 상대가 1명이면 자동 선택 (player 메서드 호출 없음)."""
        game = Game()
        # P1(팀1) 완료, P3(팀1) 활성
        game.players[1].finished = True
        game.players[3].receive_cards([c(5), c(6)])
        recipient = game._choose_dragon_recipient(0)
        assert recipient == 3

    def test_both_finished_fallback(self) -> None:
        """상대 모두 완료 → 아무 상대 선택."""
        game = Game()
        game.players[1].finished = True
        game.players[3].finished = True
        recipient = game._choose_dragon_recipient(0)
        assert game.players[recipient].team == 1

    def test_delegates_to_player_with_card_counts(self) -> None:
        """활성 상대 2명 → 손패 적은 쪽으로 위임."""
        game = Game()
        game.players[1].receive_cards([c(3)])          # 1장
        game.players[3].receive_cards([c(5), c(6)])    # 2장
        game.players[0].receive_cards([dragon()])
        recipient = game._choose_dragon_recipient(0)
        assert recipient == 1  # 1장인 P1

    def test_dragon_trick_integration(self) -> None:
        """Dragon 트릭이 손패 적은 상대에게 가는 통합 테스트."""
        game = Game()
        for p in game.players:
            p.reset()

        # P0: Dragon(25) + extra → Dragon 리드로 이김
        # P1(팀1): 1장, P3(팀1): 3장 → P1에게 줘야 함
        game.players[0].receive_cards([dragon(), c(2)])
        game.players[1].receive_cards([c(3)])
        game.players[2].receive_cards([mahjong(), c(14)])
        game.players[3].receive_cards([c(5), c(6), c(7)])

        # Mahjong 보유자(P2)부터 시작
        tricks_won, finish_order = game._play_tricks(start_idx=2)

        # Dragon이 포함된 트릭이 P1에게 갔는지 확인
        dragon_in_p1 = any(
            any(card.special == SpecialCard.DRAGON for card in trick)
            for trick in tricks_won["P1"]
        )
        assert dragon_in_p1, "Dragon 트릭이 손패 적은 P1에게 가야 함"


# ══════════════════════════════════════════════════════════════════
#  HumanPlayer Dragon 수령자 UI
# ══════════════════════════════════════════════════════════════════


class TestHumanDragonRecipient:
    """HumanPlayer.choose_dragon_recipient UI 테스트."""

    def _make_human(self) -> HumanPlayer:
        p = HumanPlayer(name="Human", team=0)
        p.receive_cards([dragon()])
        return p

    def test_select_first_opponent(self) -> None:
        """첫 번째 상대 선택."""
        p = self._make_human()
        opponents = [(1, "AI_1", 3), (3, "AI_3", 9)]
        with patch("builtins.input", return_value="1"):
            result = p.choose_dragon_recipient(opponents, [])
        assert result == 1

    def test_select_second_opponent(self) -> None:
        """두 번째 상대 선택."""
        p = self._make_human()
        opponents = [(1, "AI_1", 3), (3, "AI_3", 9)]
        with patch("builtins.input", return_value="2"):
            result = p.choose_dragon_recipient(opponents, [])
        assert result == 3

    def test_invalid_then_valid(self) -> None:
        """잘못된 입력 후 올바른 입력."""
        p = self._make_human()
        opponents = [(1, "AI_1", 3), (3, "AI_3", 9)]
        with patch("builtins.input", side_effect=["0", "3", "abc", "1"]):
            result = p.choose_dragon_recipient(opponents, [])
        assert result == 1

    def test_hint_shown_for_fewer_cards(self, capsys) -> None:
        """손패 적은 상대에 '← 손패 적음' 힌트 표시."""
        p = self._make_human()
        opponents = [(1, "AI_1", 3), (3, "AI_3", 9)]
        with patch("builtins.input", return_value="1"):
            p.choose_dragon_recipient(opponents, [])
        output = capsys.readouterr().out
        assert "← 손패 적음" in output
        # AI_1(3장)에만 힌트
        lines = output.strip().split("\n")
        ai1_line = [l for l in lines if "AI_1" in l][0]
        ai3_line = [l for l in lines if "AI_3" in l][0]
        assert "← 손패 적음" in ai1_line
        assert "← 손패 적음" not in ai3_line

    def test_no_hint_when_equal_cards(self, capsys) -> None:
        """손패 수 같으면 힌트 없음."""
        p = self._make_human()
        opponents = [(1, "AI_1", 5), (3, "AI_3", 5)]
        with patch("builtins.input", return_value="1"):
            p.choose_dragon_recipient(opponents, [])
        output = capsys.readouterr().out
        assert "← 손패 적음" not in output
