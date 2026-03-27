"""티츄 시뮬레이터 CLI 인터페이스.

사람 1명(플레이어 0) vs AI 3명으로 플레이한다.
"""

from game.card import Card
from game.game import Game
from game.human_player import HumanPlayer, format_cards


class CLIGame(Game):
    """CLI 대화형 게임."""

    def __init__(self) -> None:
        super().__init__(player_names=["You", "AI_1", "AI_2", "AI_3"])
        # 플레이어 0을 HumanPlayer로 교체
        human = HumanPlayer(name="You", team=0)
        self.players[0] = human

    def _print_header(self, text: str) -> None:
        print(f"\n{'=' * 50}")
        print(f"  {text}")
        print(f"{'=' * 50}")

    def _print_scores(self) -> None:
        print(f"\n  [점수판] 팀0(You+AI_2): {self.team_scores[0]}점"
              f"  |  팀1(AI_1+AI_3): {self.team_scores[1]}점")

    # ── 이벤트 훅 오버라이드 ──────────────────────────

    def _on_player_play(
        self, player_idx: int, cards: list[Card], remaining: int,
    ) -> None:
        name = self.players[player_idx].name
        print(
            f"  ▶ {name}이(가) {format_cards(cards)} 을 냈습니다"
            f" (남은 패: {remaining}장)"
        )

    def _on_player_finish(self, player_idx: int, finish_order: int) -> None:
        name = self.players[player_idx].name
        ordinal = f"{finish_order}등"
        print(f"  🎉 {name}이(가) 모든 카드를 냈습니다! ({ordinal})")

    def _on_player_pass(self, player_idx: int) -> None:
        name = self.players[player_idx].name
        if player_idx != 0:  # 사람 플레이어 패스는 이미 표시됨
            print(f"  ─ {name} 패스")

    def _on_trick_won(self, winner_idx: int, dragon_given: bool) -> None:
        name = self.players[winner_idx].name
        if dragon_given:
            recipient = self._choose_dragon_recipient(winner_idx)
            rname = self.players[recipient].name
            print(f"  ★ {name} 트릭 승리! (Dragon → {rname}에게 전달)")
        else:
            print(f"  ★ {name} 트릭 승리!")

    # ── 라운드 진행 ──────────────────────────────────

    def play_round(self) -> dict[int, int]:
        """라운드를 진행하며 상태를 출력한다."""
        self.round_number += 1
        self._print_header(f"라운드 {self.round_number}")
        self._print_scores()

        first_hands, remaining_hands = self._deal_cards()
        round_scores = self._play_round_with_cards(first_hands, remaining_hands)

        # 라운드 결과 출력
        self._print_header(f"라운드 {self.round_number} 결과")
        print(f"  팀0: {round_scores[0]:+d}점  |  팀1: {round_scores[1]:+d}점")
        self._print_scores()

        return round_scores


def main() -> None:
    """CLI 게임을 실행한다."""
    print("╔══════════════════════════════════════════════════╗")
    print("║              티 츄  시 뮬 레 이 터              ║")
    print("║                                                  ║")
    print("║  팀0: You(0번) + AI_2(2번)                       ║")
    print("║  팀1: AI_1(1번) + AI_3(3번)                      ║")
    print("║  목표: 1000점 먼저 달성!                         ║")
    print("╚══════════════════════════════════════════════════╝")

    game = CLIGame()

    while not game.is_game_over():
        try:
            game.play_round()
        except KeyboardInterrupt:
            print("\n\n  게임을 중단합니다.")
            return
        except EOFError:
            print("\n\n  입력이 종료되었습니다.")
            return

    winner = game.get_winner()
    print(f"\n{'=' * 50}")
    if winner == 0:
        print("  🎉 축하합니다! 팀0(You+AI_2) 승리!")
    else:
        print("  팀1(AI_1+AI_3) 승리!")
    print(f"  최종 점수 — 팀0: {game.team_scores[0]}  |  팀1: {game.team_scores[1]}")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()
