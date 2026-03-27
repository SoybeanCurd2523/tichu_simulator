"""게임 로직 모듈.

티츄 4인 게임을 시뮬레이션한다.
팀 구성: 0,2번(팀0) vs 1,3번(팀1) — 마주보는 자리가 파트너.
목표 점수(기본 1000점)에 먼저 도달하는 팀이 승리.

라운드 흐름:
1. 56장 셔플 → 8장씩 분배 → Grand Tichu 선언
2. 나머지 6장 분배 → 카드 패싱 (왼/오른/맞은편 각 1장)
3. Mahjong 보유자부터 트릭 플레이
4. 3명 완료 시(또는 1-2 피니시) 라운드 종료 → 점수 계산
"""

from __future__ import annotations

from game.card import Card, SpecialCard
from game.deck import Deck
from game.hand import HandType, HandValidator
from game.player import GameContext, Player
from game.scoring import ScoreCalculator


class Game:
    """티츄 게임 관리자."""

    TARGET_SCORE = 1000

    def __init__(self, player_names: list[str] | None = None) -> None:
        if player_names is None:
            player_names = ["P0", "P1", "P2", "P3"]
        if len(player_names) != 4:
            raise ValueError("플레이어는 정확히 4명이어야 합니다.")
        self.players = [
            Player(name=player_names[i], team=i % 2)
            for i in range(4)
        ]
        self.team_scores: dict[int, int] = {0: 0, 1: 0}
        self.round_number: int = 0

    # ── 좌석 인덱스 헬퍼 ───────────────────────────────

    @staticmethod
    def _partner_idx(idx: int) -> int:
        """맞은편(파트너) 인덱스."""
        return (idx + 2) % 4

    @staticmethod
    def _left_idx(idx: int) -> int:
        """왼쪽 플레이어 인덱스."""
        return (idx + 1) % 4

    @staticmethod
    def _right_idx(idx: int) -> int:
        """오른쪽 플레이어 인덱스."""
        return (idx + 3) % 4

    def _next_active_idx(self, idx: int) -> int:
        """idx 다음의 활성(미완료) 플레이어 인덱스."""
        for offset in range(1, 5):
            candidate = (idx + offset) % 4
            if not self.players[candidate].finished:
                return candidate
        return idx

    # ── 딜링 ────────────────────────────────────────────

    def _deal_cards(self) -> tuple[list[list[Card]], list[list[Card]]]:
        """56장을 셔플 후 [8장, 6장] × 4명으로 분배."""
        deck = Deck()
        deck.shuffle()
        all_cards = deck.cards
        first: list[list[Card]] = []
        remaining: list[list[Card]] = []
        for i in range(4):
            first.append(all_cards[i * 8:(i + 1) * 8])
            remaining.append(all_cards[32 + i * 6:32 + (i + 1) * 6])
        return first, remaining

    # ── 카드 패싱 ────────────────────────────────────────

    def _pass_cards(self) -> None:
        """각 플레이어가 왼쪽/오른쪽/맞은편에 1장씩 동시에 전달."""
        selections: list[list[Card]] = []
        for player in self.players:
            selected = player.select_pass_cards()
            selections.append(selected)

        # 동시에 제거
        for i, player in enumerate(self.players):
            player.remove_cards(selections[i])

        # 동시에 전달
        for i in range(4):
            to_left, to_right, to_opposite = selections[i]
            self.players[self._left_idx(i)].receive_cards([to_left])
            self.players[self._right_idx(i)].receive_cards([to_right])
            self.players[self._partner_idx(i)].receive_cards([to_opposite])

    # ── 시작 플레이어 ────────────────────────────────────

    def _find_starting_player(self) -> int:
        """Mahjong을 가진 플레이어 인덱스."""
        for i, player in enumerate(self.players):
            if player.has_mahjong():
                return i
        raise RuntimeError("Mahjong 카드를 가진 플레이어가 없습니다.")

    # ── Dragon 트릭 수령자 ───────────────────────────────

    def _choose_dragon_recipient(
        self,
        winner_idx: int,
        trick_play_log: list[tuple[int, list[Card]]] | None = None,
    ) -> int:
        """Dragon 트릭의 수령자(상대팀) 선택.

        활성 상대팀 플레이어 목록을 구성한 뒤,
        승자 플레이어의 choose_dragon_recipient 메서드에 위임한다.
        """
        winner_team = self.players[winner_idx].team

        active_opponents: list[tuple[int, str, int]] = []
        for i, p in enumerate(self.players):
            if p.team != winner_team and not p.finished:
                active_opponents.append((i, p.name, len(p.cards)))

        if not active_opponents:
            # 모든 상대가 완료 시 아무 상대에게
            for i, p in enumerate(self.players):
                if p.team != winner_team:
                    return i
            return (winner_idx + 1) % 4

        if len(active_opponents) == 1:
            return active_opponents[0][0]

        return self.players[winner_idx].choose_dragon_recipient(
            active_opponents, trick_play_log or [],
        )

    # ── 이벤트 훅 (서브클래스에서 오버라이드) ──────────────

    def _on_player_play(
        self, player_idx: int, cards: list[Card], remaining: int,
    ) -> None:
        """플레이어가 카드를 낼 때 호출."""

    def _on_player_pass(self, player_idx: int) -> None:
        """플레이어가 패스할 때 호출."""

    def _on_trick_won(self, winner_idx: int, dragon_given: bool) -> None:
        """트릭 승리 시 호출."""

    def _on_player_finish(
        self, player_idx: int, finish_order: int,
    ) -> None:
        """플레이어가 모든 카드를 냈을 때 호출."""

    # ── 테이블 비교 ──────────────────────────────────────

    def _can_beat_table(
        self,
        table_cards: list[Card],
        table_effective_rank: float | None,
        play: list[Card],
    ) -> bool:
        """play가 테이블의 패를 이길 수 있는지 판별.

        싱글의 경우 Phoenix effective rank를 반영한다.
        """
        play_type = HandValidator.classify(play)
        table_type = HandValidator.classify(table_cards)
        if play_type is None or table_type is None:
            return False

        BOMBS = {HandType.FOUR_OF_A_KIND, HandType.STRAIGHT_FLUSH}

        # 폭탄은 모든 비-폭탄을 이김
        if play_type in BOMBS and table_type not in BOMBS:
            return True

        # 싱글 대 싱글: effective rank 기반 비교
        if (table_type == HandType.SINGLE and play_type == HandType.SINGLE
                and len(table_cards) == 1 and len(play) == 1
                and table_effective_rank is not None):
            played_card = play[0]

            # Dragon은 싱글 최강
            if played_card.special == SpecialCard.DRAGON:
                return table_effective_rank < 25.0

            # Phoenix: 항상 비-Dragon을 이김 (실효 rank = current + 0.5)
            if played_card.special == SpecialCard.PHOENIX:
                return table_effective_rank < 25.0

            # 일반 카드: rank > effective rank
            return played_card.rank > table_effective_rank

        # 기타: HandValidator에 위임
        return HandValidator.can_beat(table_cards, play)

    # ── 트릭 플레이 루프 ─────────────────────────────────

    def _play_tricks(
        self, start_idx: int
    ) -> tuple[dict[str, list[list[Card]]], list[str]]:
        """트릭 플레이 루프.

        현재 플레이어들의 카드로 게임을 진행한다.
        Dog → 팀원에게 턴 넘기기, Dragon 트릭 → 상대팀에게,
        Phoenix 싱글 → effective rank +0.5 자동 적용.

        Args:
            start_idx: 시작 플레이어 인덱스 (Mahjong 보유자).

        Returns:
            (tricks_won, finish_order) 튜플.
        """
        tricks_won: dict[str, list[list[Card]]] = {
            p.name: [] for p in self.players
        }
        finish_order: list[str] = []

        current_idx = start_idx
        table_cards: list[Card] | None = None
        table_all_cards: list[Card] = []
        table_effective_rank: float | None = None
        last_winner_idx = start_idx
        won_with_dragon = False
        trick_play_log: list[tuple[int, list[Card]]] = []

        max_iter = 2000
        iteration = 0

        while len(finish_order) < 3 and iteration < max_iter:
            iteration += 1
            player = self.players[current_idx]

            # ── 트릭 종료: 한 바퀴 돌아 마지막 승자에게 복귀 ──
            if table_cards is not None and current_idx == last_winner_idx:
                self._award_trick(
                    last_winner_idx, table_all_cards,
                    tricks_won, won_with_dragon, trick_play_log,
                )
                table_cards = None
                table_all_cards = []
                table_effective_rank = None
                won_with_dragon = False
                trick_play_log = []

                # 승자가 완료 상태면 다음 활성 플레이어가 리드
                if self.players[last_winner_idx].finished:
                    current_idx = self._next_active_idx(last_winner_idx)
                    last_winner_idx = current_idx
                continue

            # ── 완료된 플레이어 건너뛰기 ──
            if player.finished:
                current_idx = (current_idx + 1) % 4
                continue

            # ── GameContext 설정 ──
            ctx = GameContext(
                my_idx=current_idx,
                trick_winner_idx=(
                    last_winner_idx if table_cards is not None else None
                ),
                players_team=[p.team for p in self.players],
                players_tichu=[p.tichu_called for p in self.players],
                players_grand_tichu=[
                    p.grand_tichu_called for p in self.players
                ],
                players_finished=[p.finished for p in self.players],
                players_card_count=[len(p.cards) for p in self.players],
            )
            player.set_game_context(ctx)

            play = player.select_play(table_cards, table_effective_rank)

            # ── 패스 ──
            if play is None:
                self._on_player_pass(current_idx)
                current_idx = (current_idx + 1) % 4
                continue

            # ── 유효성 검사 ──
            if HandValidator.classify(play) is None:
                current_idx = (current_idx + 1) % 4
                continue

            # ── Small Tichu 선언 (첫 플레이 직전) ──
            if not player._has_played_first_card:
                if (not player.grand_tichu_called
                        and not player.tichu_called):
                    if player.decide_tichu():
                        player.call_tichu()
                player._has_played_first_card = True

            # ── Dog 처리: 선공으로만 가능, 팀원에게 턴 넘기기 ──
            if len(play) == 1 and play[0].special == SpecialCard.DOG:
                if table_cards is not None:
                    current_idx = (current_idx + 1) % 4
                    continue

                player.remove_cards(play)
                self._on_player_play(current_idx, play, len(player.cards))
                if self._check_finish(player, finish_order):
                    self._on_player_finish(
                        current_idx, player.finish_order,
                    )

                teammate_idx = self._partner_idx(current_idx)
                if self.players[teammate_idx].finished:
                    current_idx = self._next_active_idx(teammate_idx)
                else:
                    current_idx = teammate_idx
                last_winner_idx = current_idx
                # table 은 None으로 유지 → 팀원이 새 트릭 리드
                continue

            # ── 후공 시 비교 ──
            if table_cards is not None:
                if not self._can_beat_table(
                    table_cards, table_effective_rank, play
                ):
                    current_idx = (current_idx + 1) % 4
                    continue

            # ── 카드 제출 ──
            player.remove_cards(play)
            self._on_player_play(current_idx, play, len(player.cards))
            table_cards = play
            table_all_cards.extend(play)
            trick_play_log.append((current_idx, list(play)))
            last_winner_idx = current_idx

            # ── effective rank 갱신 (싱글) ──
            if len(play) == 1:
                card = play[0]
                if card.special == SpecialCard.PHOENIX:
                    if table_effective_rank is not None:
                        table_effective_rank = table_effective_rank + 0.5
                    else:
                        table_effective_rank = card.rank  # 1.5 (리드)
                else:
                    table_effective_rank = card.rank
                won_with_dragon = card.special == SpecialCard.DRAGON
            else:
                table_effective_rank = None
                won_with_dragon = False

            # ── 완료 체크 ──
            if self._check_finish(player, finish_order):
                self._on_player_finish(
                    current_idx, player.finish_order,
                )
                # 1-2 피니시 검사
                if len(finish_order) >= 2:
                    t1 = self._team_of(finish_order[0])
                    t2 = self._team_of(finish_order[1])
                    if t1 == t2:
                        break

            current_idx = (current_idx + 1) % 4

        # ── 미완료 트릭 처리 ──
        if table_all_cards:
            self._award_trick(
                last_winner_idx, table_all_cards,
                tricks_won, won_with_dragon, trick_play_log,
            )

        # ── 나머지 플레이어 순위 등록 ──
        for player in self.players:
            if player.name not in finish_order:
                finish_order.append(player.name)
                player.finished = True
                player.finish_order = len(finish_order)

        return tricks_won, finish_order

    def _award_trick(
        self,
        winner_idx: int,
        trick_cards: list[Card],
        tricks_won: dict[str, list[list[Card]]],
        dragon_trick: bool,
        trick_play_log: list[tuple[int, list[Card]]] | None = None,
    ) -> None:
        """트릭을 승자에게 부여. Dragon 트릭은 상대팀에게."""
        self._on_trick_won(winner_idx, dragon_trick)
        if dragon_trick:
            recipient = self._choose_dragon_recipient(
                winner_idx, trick_play_log,
            )
            tricks_won[self.players[recipient].name].append(
                list(trick_cards)
            )
        else:
            tricks_won[self.players[winner_idx].name].append(
                list(trick_cards)
            )

    def _check_finish(
        self, player: Player, finish_order: list[str]
    ) -> bool:
        """플레이어 완료 여부 체크. 완료 시 등록."""
        if player.hand_empty() and not player.finished:
            player.finished = True
            finish_order.append(player.name)
            player.finish_order = len(finish_order)
            return True
        return False

    def _team_of(self, player_name: str) -> int:
        """플레이어 이름으로 팀 번호를 찾는다."""
        for p in self.players:
            if p.name == player_name:
                return p.team
        raise ValueError(f"플레이어를 찾을 수 없습니다: {player_name}")

    # ── 라운드 진행 ──────────────────────────────────────

    def play_round(self) -> dict[int, int]:
        """한 라운드를 진행한다.

        Returns:
            이번 라운드의 팀별 점수.
        """
        self.round_number += 1
        first_hands, remaining_hands = self._deal_cards()
        return self._play_round_with_cards(first_hands, remaining_hands)

    def _play_round_with_cards(
        self,
        first_hands: list[list[Card]],
        remaining_hands: list[list[Card]],
    ) -> dict[int, int]:
        """주어진 카드 분배로 라운드를 진행한다.

        Args:
            first_hands: 각 플레이어의 첫 8장.
            remaining_hands: 각 플레이어의 나머지 6장.

        Returns:
            이번 라운드의 팀별 점수.
        """
        # 1. 초기화
        for p in self.players:
            p.reset()

        # 2. 첫 8장 분배 + Grand Tichu 선언
        for i, player in enumerate(self.players):
            player.receive_cards(first_hands[i])
        for player in self.players:
            if player.decide_grand_tichu():
                player.call_grand_tichu()

        # 3. 나머지 6장 분배
        for i, player in enumerate(self.players):
            player.receive_cards(remaining_hands[i])

        # 4. 카드 패싱
        self._pass_cards()

        # 5. 트릭 플레이 (Small Tichu는 각 플레이어의 첫 플레이 직전에 선언)
        start_idx = self._find_starting_player()
        tricks_won, finish_order = self._play_tricks(start_idx)

        # 6. 점수 계산
        round_scores = ScoreCalculator.calculate_round_score(
            self.players, tricks_won, finish_order
        )
        for team, score in round_scores.items():
            self.team_scores[team] += score

        return round_scores

    # ── 게임 제어 ────────────────────────────────────────

    def is_game_over(self) -> bool:
        """게임 종료 여부."""
        return any(s >= self.TARGET_SCORE for s in self.team_scores.values())

    def get_winner(self) -> int | None:
        """승리 팀 번호. 미종료 시 None."""
        if not self.is_game_over():
            return None
        return max(self.team_scores, key=self.team_scores.get)  # type: ignore

    def run(self) -> int:
        """게임을 끝까지 진행하고 승리 팀을 반환한다."""
        while not self.is_game_over():
            self.play_round()
        return self.get_winner()  # type: ignore
