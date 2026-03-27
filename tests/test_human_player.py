"""HumanPlayer CLI 입력 테스트."""

from unittest.mock import patch

import pytest

from game.card import Card, SpecialCard, Suit
from game.human_player import HumanPlayer, format_card, format_cards


def c(rank: int, suit: Suit = Suit.JADE) -> Card:
    return Card.normal(rank, suit)


class TestFormatCard:
    def test_normal_card(self) -> None:
        assert format_card(c(14, Suit.SWORD)) == "[ ♠ A ]"

    def test_normal_card_two_digit(self) -> None:
        assert format_card(c(10, Suit.STAR)) == "[ ♥ 10 ]"

    def test_special_card(self) -> None:
        assert format_card(Card.dragon()) == "[ Dragon ]"
        assert format_card(Card.phoenix()) == "[ Phoenix ]"

    def test_format_cards_multiple(self) -> None:
        cards = [c(5), c(10, Suit.STAR), Card.dragon()]
        assert format_cards(cards) == "[ ♣ 5 ]  [ ♥ 10 ]  [ Dragon ]"


@pytest.fixture
def player() -> HumanPlayer:
    p = HumanPlayer(name="Test", team=0)
    p.receive_cards([c(3), c(5), c(7), c(9), c(11)])
    return p


class TestInputYesNo:
    def test_yes(self, player: HumanPlayer) -> None:
        with patch("builtins.input", return_value="y"):
            assert player._input_yes_no("test? ") is True

    def test_no(self, player: HumanPlayer) -> None:
        with patch("builtins.input", return_value="n"):
            assert player._input_yes_no("test? ") is False

    def test_invalid_then_yes(self, player: HumanPlayer) -> None:
        with patch("builtins.input", side_effect=["x", "maybe", "y"]):
            assert player._input_yes_no("test? ") is True


class TestInputCardIndices:
    def test_single_index(self, player: HumanPlayer) -> None:
        with patch("builtins.input", return_value="2"):
            result = player._input_card_indices("pick: ", count=1)
            assert result == [2]

    def test_multiple_indices(self, player: HumanPlayer) -> None:
        with patch("builtins.input", return_value="0 2 4"):
            result = player._input_card_indices("pick: ", count=3)
            assert result == [0, 2, 4]

    def test_comma_separated(self, player: HumanPlayer) -> None:
        with patch("builtins.input", return_value="1,3"):
            result = player._input_card_indices("pick: ", count=2)
            assert result == [1, 3]

    def test_out_of_range_then_valid(self, player: HumanPlayer) -> None:
        with patch("builtins.input", side_effect=["10", "2"]):
            result = player._input_card_indices("pick: ", count=1)
            assert result == [2]

    def test_duplicate_then_valid(self, player: HumanPlayer) -> None:
        with patch("builtins.input", side_effect=["2 2", "2 3"]):
            result = player._input_card_indices("pick: ", count=2)
            assert result == [2, 3]

    def test_wrong_count_then_valid(self, player: HumanPlayer) -> None:
        with patch("builtins.input", side_effect=["0 1", "0"]):
            result = player._input_card_indices("pick: ", count=1)
            assert result == [0]

    def test_allow_empty(self, player: HumanPlayer) -> None:
        with patch("builtins.input", return_value=""):
            result = player._input_card_indices("pick: ", allow_empty=True)
            assert result == []

    def test_non_numeric_then_valid(self, player: HumanPlayer) -> None:
        with patch("builtins.input", side_effect=["abc", "0"]):
            result = player._input_card_indices("pick: ", count=1)
            assert result == [0]


class TestDecideGrandTichu:
    def test_accepts_grand_tichu(self) -> None:
        p = HumanPlayer(name="Test", team=0)
        p.receive_cards([c(r) for r in range(7, 15)])  # 8장
        with patch("builtins.input", return_value="y"):
            assert p.decide_grand_tichu() is True

    def test_declines_grand_tichu(self) -> None:
        p = HumanPlayer(name="Test", team=0)
        p.receive_cards([c(r) for r in range(7, 15)])
        with patch("builtins.input", return_value="n"):
            assert p.decide_grand_tichu() is False


class TestDecideTichu:
    def test_accepts_tichu(self) -> None:
        p = HumanPlayer(name="Test", team=0)
        p.receive_cards([c(r) for r in range(2, 16) if r <= 14])
        with patch("builtins.input", return_value="y"):
            assert p.decide_tichu() is True


class TestSelectPassCards:
    def test_selects_three_cards(self, player: HumanPlayer) -> None:
        # 0번(♣3), 2번(♣7), 4번(♣J) 선택
        with patch("builtins.input", side_effect=["0", "2", "4"]):
            result = player.select_pass_cards()
            assert len(result) == 3
            assert result[0] == c(3)   # 왼쪽
            assert result[1] == c(7)   # 오른쪽
            assert result[2] == c(11)  # 맞은편

    def test_duplicate_card_rejected(self, player: HumanPlayer) -> None:
        # 0번을 두 번 선택하면 거부 후 다시 입력
        with patch("builtins.input", side_effect=["0", "0", "1", "2"]):
            result = player.select_pass_cards()
            assert len(result) == 3


class TestSelectPlay:
    def test_lead_single(self, player: HumanPlayer) -> None:
        with patch("builtins.input", return_value="0"):
            result = player.select_play(None)
            assert result == [c(3)]

    def test_follow_single(self, player: HumanPlayer) -> None:
        # 테이블에 ♣5, effective_rank=5.0 → ♣7(idx=2)로 이김
        with patch("builtins.input", return_value="2"):
            result = player.select_play([c(5)], 5.0)
            assert result == [c(7)]

    def test_pass_on_follow(self, player: HumanPlayer) -> None:
        with patch("builtins.input", return_value=""):
            result = player.select_play([c(5)], 5.0)
            assert result is None

    def test_lead_cannot_pass(self, player: HumanPlayer) -> None:
        """선 플레이어는 Enter로 패스할 수 없다."""
        with patch("builtins.input", side_effect=["", "0"]):
            result = player.select_play(None)
            assert result == [c(3)]

    def test_invalid_combo_then_valid(self, player: HumanPlayer) -> None:
        # ♣3 + ♣7은 유효하지 않은 조합 → 다시 입력 → ♣3 싱글
        with patch("builtins.input", side_effect=["0 2", "0"]):
            result = player.select_play(None)
            assert result == [c(3)]

    def test_cant_beat_table_then_pass(self, player: HumanPlayer) -> None:
        # 테이블에 ♣9(eff=9.0), ♣3 선택 → 못 이김 → 패스
        with patch("builtins.input", side_effect=["0", ""]):
            result = player.select_play([c(9)], 9.0)
            assert result is None

    def test_lead_pair(self) -> None:
        p = HumanPlayer(name="Test", team=0)
        p.receive_cards([c(5, Suit.JADE), c(5, Suit.SWORD), c(9)])
        with patch("builtins.input", return_value="0 1"):
            result = p.select_play(None)
            assert len(result) == 2
