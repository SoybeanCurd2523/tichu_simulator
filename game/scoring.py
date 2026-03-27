"""점수 계산 모듈."""

from __future__ import annotations

from game.card import Card
from game.player import Player


class ScoreCalculator:
    """티츄 점수 계산기."""

    @staticmethod
    def count_card_points(cards: list[Card]) -> int:
        """카드 묶음의 점수 합계를 계산한다.

        5: 5점, 10/K: 10점, Dragon: 25점, Phoenix: -25점.
        전체 56장 합계는 항상 100점.
        """
        return sum(card.points for card in cards)

    @staticmethod
    def calculate_round_score(
        players: list[Player],
        tricks_won: dict[str, list[list[Card]]],
        finish_order: list[str],
    ) -> dict[int, int]:
        """라운드 점수를 계산한다.

        Args:
            players: 4명의 플레이어 리스트.
            tricks_won: 플레이어 이름 → 획득 트릭(카드 묶음) 리스트.
            finish_order: 카드를 다 낸 순서 (플레이어 이름).

        Returns:
            팀 번호 → 점수 딕셔너리.
        """
        team_scores: dict[int, int] = {0: 0, 1: 0}
        player_map = {p.name: p for p in players}

        # ── 1-2 피니시 검사 ──
        is_one_two = False
        if len(finish_order) >= 2:
            first = player_map[finish_order[0]]
            second = player_map[finish_order[1]]
            if first.team == second.team:
                team_scores[first.team] = 200
                is_one_two = True

        # ── 일반 점수 계산 (1-2 피니시가 아닐 때만) ──
        if not is_one_two:
            for player in players:
                cards_won: list[Card] = []
                for trick in tricks_won.get(player.name, []):
                    cards_won.extend(trick)
                points = ScoreCalculator.count_card_points(cards_won)
                team_scores[player.team] += points

            # 4등: 남은 카드 점수 → 1등 팀에게
            if len(finish_order) >= 4:
                last_player = player_map[finish_order[3]]
                remaining_pts = ScoreCalculator.count_card_points(
                    last_player.cards
                )
                first_player = player_map[finish_order[0]]
                team_scores[first_player.team] += remaining_pts

        # ── 티츄 보너스/벌점 (항상 적용) ──
        for player in players:
            if player.tichu_called:
                if finish_order[0] == player.name:
                    team_scores[player.team] += 100
                else:
                    team_scores[player.team] -= 100
            if player.grand_tichu_called:
                if finish_order[0] == player.name:
                    team_scores[player.team] += 200
                else:
                    team_scores[player.team] -= 200

        return team_scores
