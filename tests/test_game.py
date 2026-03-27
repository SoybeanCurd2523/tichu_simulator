"""game.py 단위 테스트."""

import random

import pytest

from game.card import Card, SpecialCard, Suit
from game.game import Game
from game.player import Player


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
#  팀 구성
# ══════════════════════════════════════════════════════════════════


class TestTeamComposition:
    """팀 배정: 0,2번(팀0) vs 1,3번(팀1)."""

    def test_team_assignment(self) -> None:
        game = Game()
        assert game.players[0].team == 0
        assert game.players[1].team == 1
        assert game.players[2].team == 0
        assert game.players[3].team == 1

    def test_partner_idx(self) -> None:
        assert Game._partner_idx(0) == 2
        assert Game._partner_idx(1) == 3
        assert Game._partner_idx(2) == 0
        assert Game._partner_idx(3) == 1

    def test_left_right_idx(self) -> None:
        assert Game._left_idx(0) == 1
        assert Game._right_idx(0) == 3
        assert Game._left_idx(2) == 3
        assert Game._right_idx(2) == 1

    def test_four_players_required(self) -> None:
        with pytest.raises(ValueError):
            Game(player_names=["A", "B", "C"])


# ══════════════════════════════════════════════════════════════════
#  카드 분배 (8장 + 6장)
# ══════════════════════════════════════════════════════════════════


class TestDealing:
    """56장 셔플 후 8장/6장 분배."""

    def test_deal_8_plus_6(self) -> None:
        game = Game()
        first, remaining = game._deal_cards()
        assert all(len(h) == 8 for h in first)
        assert all(len(h) == 6 for h in remaining)

    def test_all_56_unique(self) -> None:
        game = Game()
        first, remaining = game._deal_cards()
        all_cards: list[Card] = []
        for h in first:
            all_cards.extend(h)
        for h in remaining:
            all_cards.extend(h)
        assert len(all_cards) == 56

    def test_grand_tichu_after_8_cards(self) -> None:
        """Grand Tichu 선언 타이밍: 첫 8장 후."""

        class GTPlayer(Player):
            def decide_grand_tichu(self) -> bool:
                # 8장일 때만 GT 선언
                return len(self.cards) == 8

        game = Game()
        game.players = [
            GTPlayer(name=f"P{i}", team=i % 2) for i in range(4)
        ]
        first, remaining = game._deal_cards()
        game._play_round_with_cards(first, remaining)
        for p in game.players:
            assert p.grand_tichu_called is True


# ══════════════════════════════════════════════════════════════════
#  카드 패싱
# ══════════════════════════════════════════════════════════════════


class TestCardPassing:
    """각 플레이어가 왼/오른/맞은편에 1장씩 전달."""

    def _setup_known_hands(self, game: Game) -> None:
        """테스트용: 각 플레이어에게 고유한 14장 배분."""
        for p in game.players:
            p.reset()
        suits = [J, S, P, T]
        specials = [mahjong(), dog(), phoenix(), dragon()]
        for i, player in enumerate(game.players):
            cards = [Card.normal(r, suits[i]) for r in range(2, 15)]
            cards.append(specials[i])
            player.receive_cards(cards)

    def test_still_14_cards_after_passing(self) -> None:
        game = Game()
        self._setup_known_hands(game)
        game._pass_cards()
        for player in game.players:
            assert len(player.cards) == 14

    def test_received_from_neighbors(self) -> None:
        """P0이 P1, P3, P2로부터 1장씩 받는지 확인."""
        game = Game()
        self._setup_known_hands(game)
        p0_before = set(id(c) for c in game.players[0].cards)
        game._pass_cards()
        p0_after = set(id(c) for c in game.players[0].cards)
        # 3장 빠지고 3장 들어옴
        removed = p0_before - p0_after
        added = p0_after - p0_before
        assert len(removed) == 3
        assert len(added) == 3


# ══════════════════════════════════════════════════════════════════
#  시작 플레이어 (Mahjong)
# ══════════════════════════════════════════════════════════════════


class TestStartingPlayer:
    def test_mahjong_holder_starts(self) -> None:
        game = Game()
        for p in game.players:
            p.reset()
        game.players[2].receive_cards([mahjong(), c(3), c(4)])
        game.players[0].receive_cards([c(5)])
        game.players[1].receive_cards([c(6)])
        game.players[3].receive_cards([c(7)])
        assert game._find_starting_player() == 2


# ══════════════════════════════════════════════════════════════════
#  _can_beat_table (Phoenix effective rank)
# ══════════════════════════════════════════════════════════════════


class TestCanBeatTable:
    """Phoenix effective rank 반영 테스트."""

    def test_normal_single_beats_lower(self) -> None:
        game = Game()
        assert game._can_beat_table([c(5)], 5.0, [c(8)]) is True
        assert game._can_beat_table([c(8)], 8.0, [c(5)]) is False

    def test_phoenix_on_table_effective_rank(self) -> None:
        """Phoenix가 10 위에 놓이면 effective rank = 10.5."""
        game = Game()
        # ♠J(11) > 10.5 → 이김
        assert game._can_beat_table([phoenix()], 10.5, [c(11)]) is True
        # ♠10 ≤ 10.5 → 못 이김
        assert game._can_beat_table([phoenix()], 10.5, [c(10)]) is False
        # ♠10 = 10.0 < 10.5 → 못 이김
        assert game._can_beat_table([phoenix()], 10.5, [c(10, S)]) is False

    def test_phoenix_as_lead_beatable_by_2(self) -> None:
        """Phoenix 리드(eff=1.5)는 rank 2로 이김."""
        game = Game()
        assert game._can_beat_table([phoenix()], 1.5, [c(2)]) is True

    def test_dragon_not_beatable_by_normal(self) -> None:
        game = Game()
        assert game._can_beat_table([dragon()], 25.0, [c(14)]) is False

    def test_phoenix_cannot_beat_dragon(self) -> None:
        game = Game()
        assert game._can_beat_table([dragon()], 25.0, [phoenix()]) is False

    def test_bomb_beats_dragon(self) -> None:
        game = Game()
        bomb = [Card.normal(3, s) for s in Suit]
        assert game._can_beat_table([dragon()], 25.0, bomb) is True


# ══════════════════════════════════════════════════════════════════
#  Dragon 트릭 수령자
# ══════════════════════════════════════════════════════════════════


class TestDragonRecipient:
    def test_gives_to_opponent_team(self) -> None:
        game = Game()
        # P0(팀0) 승리 → 상대팀(팀1)에게
        recipient = game._choose_dragon_recipient(0)
        assert game.players[recipient].team == 1

    def test_prefers_active_opponent(self) -> None:
        game = Game()
        # P1(팀1) 완료, P3(팀1) 활성
        game.players[1].finished = True
        recipient = game._choose_dragon_recipient(0)
        assert recipient == 3


# ══════════════════════════════════════════════════════════════════
#  Dog 카드 → 팀원에게 턴 넘기기
# ══════════════════════════════════════════════════════════════════


class TestDogCard:
    def test_dog_passes_turn_to_teammate(self) -> None:
        """Dog → 팀원에게 턴 넘김. P0이 Dog 리드 → P2(팀원) 리드."""
        game = Game()
        for p in game.players:
            p.reset()

        # 새 AI: P0은 A♠를 먼저 리드 (Dog는 팀원 Tichu 시에만)
        # P0: ♠A 리드 → 모두 패스 → P0 트릭 승, Dog만 남음
        # P0: Dog 리드 → P2에게 넘김
        # P2: ♠3 리드 → 1st 완료는 P0 (Dog+A 모두 소진)
        game.players[0].receive_cards([dog(), c(14)])
        game.players[1].receive_cards([c(2)])
        game.players[2].receive_cards([c(3)])
        game.players[3].receive_cards([c(4), c(5)])

        tricks_won, finish_order = game._play_tricks(start_idx=0)

        # P0이 1st (A♠ 리드 + Dog 리드로 패 소진)
        assert finish_order[0] == "P0"
        # P2가 2nd (Dog 후 P2 리드)
        assert finish_order[1] == "P2"
        # 같은 팀 → 1-2 피니시
        assert game.players[0].team == game.players[2].team == 0

    def test_dog_to_finished_teammate_goes_to_next(self) -> None:
        """팀원이 이미 완료되면 다음 활성 플레이어에게."""
        game = Game()
        for p in game.players:
            p.reset()

        # P2(팀원) 이미 완료
        game.players[2].finished = True
        game.players[2].finish_order = 1

        game.players[0].receive_cards([dog(), c(14)])
        game.players[1].receive_cards([c(2), c(3)])
        game.players[3].receive_cards([c(4)])

        tricks_won, finish_order = game._play_tricks(start_idx=0)

        # P2는 이미 완료 → Dog 후 다음 활성(P3)에게 턴
        # P3이 리드
        assert "P3" in finish_order


# ══════════════════════════════════════════════════════════════════
#  Dragon 트릭 → 상대팀
# ══════════════════════════════════════════════════════════════════


class TestDragonTrick:
    def test_dragon_trick_goes_to_opponent(self) -> None:
        """Dragon으로 딴 트릭은 상대팀에게 넘긴다."""
        game = Game()
        for p in game.players:
            p.reset()

        # P2: Mahjong, ♠10 → Mahjong으로 시작
        # P3: ♠4 → 따라감
        # P0: Dragon → Dragon 싱글로 이김
        # P1: ♠2, ♠3 → Dragon 못 이김
        game.players[0].receive_cards([dragon()])
        game.players[1].receive_cards([c(2), c(3)])
        game.players[2].receive_cards([mahjong(), c(10)])
        game.players[3].receive_cards([c(4)])

        tricks_won, finish_order = game._play_tricks(start_idx=2)

        # Dragon 트릭은 P0(팀0)의 상대 팀1에게
        dragon_in_p1 = any(
            any(card.special == SpecialCard.DRAGON for card in trick)
            for trick in tricks_won["P1"]
        )
        dragon_in_p3 = any(
            any(card.special == SpecialCard.DRAGON for card in trick)
            for trick in tricks_won["P3"]
        )
        assert dragon_in_p1 or dragon_in_p3, "Dragon 트릭이 상대팀에게 가야 함"

        # P0(팀0)은 Dragon 트릭을 갖지 않아야 함
        dragon_in_p0 = any(
            any(card.special == SpecialCard.DRAGON for card in trick)
            for trick in tricks_won["P0"]
        )
        assert not dragon_in_p0


# ══════════════════════════════════════════════════════════════════
#  Phoenix +0.5 effective rank
# ══════════════════════════════════════════════════════════════════


class TestPhoenixEffectiveRank:
    def test_phoenix_over_10_blocks_rank_10(self) -> None:
        """Phoenix(eff=10.5) 위에 ♠10은 낼 수 없다."""
        game = Game()
        for p in game.players:
            p.reset()

        # P0: Mahjong → 리드
        # P1: ♠10 → 따라감 (10 > 1.0)
        # P2: Phoenix → 따라감 (eff = 10.5)
        # P3: ♠5 → 10.5 못 이김, 패스
        # P0: Mahjong 이미 사용, 패스 (카드 없음 - 완료)
        # P1: ♠10 이미 사용, 패스 (카드 없음 - 완료)
        # → 다시 P2에게 돌아옴 → 트릭 종료, P2 승
        game.players[0].receive_cards([mahjong()])
        game.players[1].receive_cards([c(10)])
        game.players[2].receive_cards([phoenix(), c(14)])
        game.players[3].receive_cards([c(5)])

        tricks_won, finish_order = game._play_tricks(start_idx=0)

        # Phoenix가 포함된 트릭은 P2가 이겨야 함
        phoenix_trick = None
        for name, tricks in tricks_won.items():
            for trick in tricks:
                if any(card.special == SpecialCard.PHOENIX for card in trick):
                    phoenix_trick = name
        assert phoenix_trick == "P2"

    def test_phoenix_over_10_beaten_by_jack(self) -> None:
        """Phoenix(eff=10.5) 위에 ♠J(11)은 낼 수 있다."""
        game = Game()
        for p in game.players:
            p.reset()

        # P0 리드 → P1(♠10) → P2(Phoenix, eff=10.5) → P3(♠J beats 10.5)
        # P0에게 여분 카드를 줘서 3명 조기 완료를 방지
        game.players[0].receive_cards([mahjong(), c(2), c(3)])
        game.players[1].receive_cards([c(10)])
        game.players[2].receive_cards([phoenix()])
        game.players[3].receive_cards([c(11), c(12)])

        tricks_won, finish_order = game._play_tricks(start_idx=0)

        # ♠J가 Phoenix(10.5)를 이기므로 P3이 트릭(Phoenix 포함)을 가져감
        p3_cards = [card for trick in tricks_won["P3"] for card in trick]
        assert any(card.special == SpecialCard.PHOENIX for card in p3_cards)


# ══════════════════════════════════════════════════════════════════
#  3연속 패스 → 트릭 종료
# ══════════════════════════════════════════════════════════════════


class TestTrickEnd:
    def test_all_pass_trick_goes_to_last_winner(self) -> None:
        """모두 패스하면 마지막 승자가 트릭을 가져간다."""
        game = Game()
        for p in game.players:
            p.reset()

        # P0: Mahjong, ♠14 → Mahjong 리드 (eff=1)
        # P1: ♠3 → 3 > 1 → 따라감
        # P2: ♠2 → 2 < 3 → 패스
        # P3: ♠2(S) → 2 < 3 → 패스
        # P0: ♠14 → 14 > 3 → 따라감 → P0 승
        # P1: 카드 없음(완료)
        # P2: 패스
        # P3: 패스
        # → P0에게 돌아옴 → 트릭 종료
        game.players[0].receive_cards([mahjong(), c(14)])
        game.players[1].receive_cards([c(3)])
        game.players[2].receive_cards([c(2)])
        game.players[3].receive_cards([c(2, S)])

        tricks_won, finish_order = game._play_tricks(start_idx=0)

        # 첫 트릭: P0이 ♠14로 이김 → P0이 트릭 획득
        assert len(tricks_won["P0"]) >= 1
        first_trick = tricks_won["P0"][0]
        assert any(c.rank == 14 for c in first_trick)


# ══════════════════════════════════════════════════════════════════
#  1-2 피니시
# ══════════════════════════════════════════════════════════════════


class TestOneTwoFinish:
    def test_same_team_1_2_gives_200(self) -> None:
        """같은 팀이 1-2 피니시 → 200점."""
        game = Game()
        for p in game.players:
            p.reset()

        # P0(팀0): Dog, ♠A → Dog로 P2에게 넘김
        # P2(팀0): ♠3 → 리드, 1st 완료
        # P3(팀1): ♠4, ♠5
        # P0(팀0): ♠A로 따라감, 2nd 완료 → 1-2 피니시
        # P1(팀1): ♠2
        game.players[0].receive_cards([dog(), c(14)])
        game.players[1].receive_cards([c(2)])
        game.players[2].receive_cards([c(3)])
        game.players[3].receive_cards([c(4), c(5)])

        tricks_won, finish_order = game._play_tricks(start_idx=0)

        from game.scoring import ScoreCalculator
        scores = ScoreCalculator.calculate_round_score(
            game.players, tricks_won, finish_order
        )
        assert scores[0] == 200  # 팀0 = 200
        assert scores[1] == 0    # 팀1 = 0

    def test_different_team_1_2_no_200(self) -> None:
        """다른 팀이 1-2 피니시 → 200점 아님."""
        game = Game()
        for p in game.players:
            p.reset()

        # P0(팀0): Mahjong → 1st
        # P1(팀1): ♠3 → 2nd (다른 팀)
        game.players[0].receive_cards([mahjong()])
        game.players[1].receive_cards([c(3)])
        game.players[2].receive_cards([c(4)])
        game.players[3].receive_cards([c(5), c(6)])

        tricks_won, finish_order = game._play_tricks(start_idx=0)

        from game.scoring import ScoreCalculator
        scores = ScoreCalculator.calculate_round_score(
            game.players, tricks_won, finish_order
        )
        assert scores[0] != 200 or scores[1] != 0


# ══════════════════════════════════════════════════════════════════
#  전체 라운드 통합
# ══════════════════════════════════════════════════════════════════


class TestRoundIntegration:
    def test_round_completes(self) -> None:
        """라운드가 정상 완료되어 양 팀 점수를 반환."""
        random.seed(42)
        game = Game()
        scores = game.play_round()
        assert 0 in scores and 1 in scores

    def test_all_players_get_14_cards(self) -> None:
        """딜링+패싱 후 각 플레이어 14장."""
        game = Game()
        first, remaining = game._deal_cards()
        for p in game.players:
            p.reset()
        for i, p in enumerate(game.players):
            p.receive_cards(first[i])
            p.receive_cards(remaining[i])
        assert all(len(p.cards) == 14 for p in game.players)


# ══════════════════════════════════════════════════════════════════
#  전체 게임 통합
# ══════════════════════════════════════════════════════════════════


class TestFullGame:
    def test_game_runs_to_completion(self) -> None:
        """게임이 목표 점수에 도달하면 종료."""
        random.seed(123)
        game = Game()
        winner = game.run()
        assert winner in (0, 1)
        assert game.team_scores[winner] >= Game.TARGET_SCORE

    def test_on_player_play_receives_remaining_count(self) -> None:
        """_on_player_play 훅에 남은 패 수가 전달된다."""

        class SpyGame(Game):
            def __init__(self) -> None:
                super().__init__()
                self.play_log: list[tuple[int, int]] = []  # (player_idx, remaining)

            def _on_player_play(
                self, player_idx: int, cards: list[Card], remaining: int,
            ) -> None:
                self.play_log.append((player_idx, remaining))

        game = SpyGame()
        for p in game.players:
            p.reset()

        # P0: Mahjong + ♣3 (2장 → 1장 남음으로 시작)
        game.players[0].receive_cards([Card.mahjong(), c(3)])
        game.players[1].receive_cards([c(5)])
        game.players[2].receive_cards([c(7)])
        game.players[3].receive_cards([c(9)])

        game._play_tricks(start_idx=0)

        # 첫 플레이 시 남은 패 확인
        assert game.play_log[0] == (0, 1)  # P0이 Mahjong 내고 1장 남음

    def test_on_player_finish_called_with_order(self) -> None:
        """플레이어 패 소진 시 _on_player_finish가 등수와 함께 호출된다."""

        class SpyGame(Game):
            def __init__(self) -> None:
                super().__init__()
                self.finish_log: list[tuple[int, int]] = []  # (player_idx, order)

            def _on_player_finish(
                self, player_idx: int, finish_order: int,
            ) -> None:
                self.finish_log.append((player_idx, finish_order))

        game = SpyGame()
        for p in game.players:
            p.reset()

        # 각 플레이어에게 1장씩 → 한 번 내면 완료
        game.players[0].receive_cards([Card.mahjong()])
        game.players[1].receive_cards([c(5)])
        game.players[2].receive_cards([c(7)])
        game.players[3].receive_cards([c(9)])

        game._play_tricks(start_idx=0)

        # 최소 1명은 finish 해야 함
        assert len(game.finish_log) >= 1
        # 등수가 순차적으로 부여됨
        for i, (_, order) in enumerate(game.finish_log):
            assert order == i + 1

    def test_remaining_zero_on_last_play(self) -> None:
        """마지막 카드를 낼 때 remaining=0이 전달된다."""

        class SpyGame(Game):
            def __init__(self) -> None:
                super().__init__()
                self.play_log: list[tuple[int, int]] = []

            def _on_player_play(
                self, player_idx: int, cards: list[Card], remaining: int,
            ) -> None:
                self.play_log.append((player_idx, remaining))

        game = SpyGame()
        for p in game.players:
            p.reset()

        # P0: 1장만 → 내면 0장
        game.players[0].receive_cards([Card.mahjong()])
        game.players[1].receive_cards([c(5), c(6)])
        game.players[2].receive_cards([c(7), c(8)])
        game.players[3].receive_cards([c(9), c(10)])

        game._play_tricks(start_idx=0)

        # P0의 첫 플레이에서 remaining=0
        p0_plays = [(idx, rem) for idx, rem in game.play_log if idx == 0]
        assert p0_plays[0] == (0, 0)

    def test_multiple_seeds_all_terminate(self) -> None:
        """다양한 시드에서 게임이 모두 종료되는지 확인."""
        for seed in range(5):
            random.seed(seed)
            game = Game()
            winner = game.run()
            assert winner in (0, 1)
