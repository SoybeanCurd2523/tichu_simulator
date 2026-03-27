"""후공 시 낼 수 있는 카드 없음 자동 패스 테스트."""

from unittest.mock import patch

import pytest

from game.card import Card, SpecialCard, Suit
from game.human_player import HumanPlayer


J, S, P, T = Suit.JADE, Suit.SWORD, Suit.PAGODA, Suit.STAR


def c(rank: int, suit: Suit = J) -> Card:
    return Card.normal(rank, suit)


phoenix = Card.phoenix
dragon = Card.dragon
dog = Card.dog
mahjong = Card.mahjong


# ══════════════════════════════════════════════════════════════════
#  자동 패스 (낼 수 있는 카드 없음)
# ══════════════════════════════════════════════════════════════════


class TestAutoPass:
    """후공 시 낼 수 있는 카드가 없으면 자동 패스."""

    def test_no_playable_cards_auto_pass(self) -> None:
        """테이블 싱글 A(14) 대비 손패에 이길 카드 없음 → 자동 패스."""
        p = HumanPlayer(name="Test", team=0)
        p.receive_cards([c(3), c(5), c(7)])
        # 테이블에 Ace, effective rank 14.0
        result = p.select_play([c(14)], 14.0)
        assert result is None

    def test_auto_pass_message(self, capsys) -> None:
        """자동 패스 시 안내 메시지 출력."""
        p = HumanPlayer(name="Test", team=0)
        p.receive_cards([c(3), c(5)])
        p.select_play([c(14)], 14.0)
        output = capsys.readouterr().out
        assert "낼 수 있는 카드가 없습니다. 자동 패스합니다." in output

    def test_no_auto_pass_when_playable(self) -> None:
        """낼 수 있는 카드 있으면 자동 패스하지 않음 (일반 입력 흐름)."""
        p = HumanPlayer(name="Test", team=0)
        p.receive_cards([c(3), c(5), c(14)])
        # 테이블에 10 → A로 이길 수 있음 → 일반 입력
        with patch("builtins.input", return_value="2"):
            result = p.select_play([c(10)], 10.0)
        assert result == [c(14)]

    def test_pair_no_playable_auto_pass(self) -> None:
        """테이블 페어에 맞는 카드 없음 → 자동 패스."""
        p = HumanPlayer(name="Test", team=0)
        p.receive_cards([c(3), c(5), c(7)])
        table = [c(10, J), c(10, S)]
        result = p.select_play(table, None)
        assert result is None

    def test_lead_never_auto_pass(self) -> None:
        """선공은 자동 패스 안 됨."""
        p = HumanPlayer(name="Test", team=0)
        p.receive_cards([c(3)])
        with patch("builtins.input", return_value="0"):
            result = p.select_play(None)
        assert result == [c(3)]


# ══════════════════════════════════════════════════════════════════
#  폭탄 보유 시 선택
# ══════════════════════════════════════════════════════════════════


class TestAutoPassWithBomb:
    """낼 수 있는 카드 없지만 폭탄 보유 시 선택 UI."""

    def _player_with_bomb(self) -> HumanPlayer:
        """손패: ♣3, ♠3, ♦3, ♥3 (4-of-a-kind 폭탄) + ♣2."""
        p = HumanPlayer(name="Test", team=0)
        p.receive_cards([
            c(2, J),
            c(3, J), c(3, S), c(3, P), c(3, T),
        ])
        return p

    def test_bomb_prompt_shown(self, capsys) -> None:
        """폭탄 보유 + 일반 카드 없음 → 폭탄 안내 메시지."""
        p = self._player_with_bomb()
        # 테이블에 A → 2,3으로는 싱글로 못 이김. 3 폭탄은 가능.
        with patch("builtins.input", return_value="n"):
            result = p.select_play([c(14)], 14.0)
        output = capsys.readouterr().out
        assert "낼 수 있는 카드가 없지만 폭탄을 보유 중입니다." in output

    def test_bomb_decline_passes(self) -> None:
        """폭탄 사용 거절(n) → 패스."""
        p = self._player_with_bomb()
        with patch("builtins.input", return_value="n"):
            result = p.select_play([c(14)], 14.0)
        assert result is None

    def test_bomb_accept_allows_play(self) -> None:
        """폭탄 사용 수락(y) → 카드 선택 가능."""
        p = self._player_with_bomb()
        # y로 폭탄 사용 선택 → 이후 폭탄 카드 번호 입력
        # 카드 순서: [♣2, ♣3, ♠3, ♦3, ♥3] → 인덱스 1 2 3 4가 폭탄
        with patch("builtins.input", side_effect=["y", "1 2 3 4"]):
            result = p.select_play([c(14)], 14.0)
        assert result is not None
        assert len(result) == 4
        assert all(int(card.rank) == 3 for card in result)

    def test_bomb_against_pair(self) -> None:
        """페어에 대해 일반 카드 없지만 폭탄으로 이길 수 있음."""
        p = self._player_with_bomb()
        table = [c(14, J), c(14, S)]  # Ace 페어
        # 3 페어로는 못 이김. 3 폭탄은 가능.
        with patch("builtins.input", return_value="n"):
            result = p.select_play(table, None)
        assert result is None  # 거절했으므로 패스

    def test_no_bomb_prompt_when_normal_play_exists(self) -> None:
        """일반 플레이 가능하면 폭탄 프롬프트 안 나옴."""
        p = HumanPlayer(name="Test", team=0)
        p.receive_cards([
            c(3, J), c(3, S), c(3, P), c(3, T),
            c(14),  # Ace로 이길 수 있음
        ])
        with patch("builtins.input", return_value="4"):
            result = p.select_play([c(10)], 10.0)
        assert result == [c(14)]
