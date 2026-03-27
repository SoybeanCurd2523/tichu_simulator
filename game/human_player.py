"""사람 플레이어 클래스.

CLI를 통해 사람이 직접 카드를 선택한다.
"""

from __future__ import annotations

from game.card import Card, SpecialCard, Suit
from game.hand import HandType, HandValidator
from game.player import Player


_SUIT_SYMBOLS = {
    Suit.JADE: "♣",
    Suit.SWORD: "♠",
    Suit.PAGODA: "♦",
    Suit.STAR: "♥",
}

_RANK_NAMES = {11: "J", 12: "Q", 13: "K", 14: "A"}

_SPECIAL_NAMES = {
    SpecialCard.MAHJONG: "Mahjong",
    SpecialCard.DOG: "Dog",
    SpecialCard.PHOENIX: "Phoenix",
    SpecialCard.DRAGON: "Dragon",
}


def format_card(card: Card) -> str:
    """카드를 [ ♠ A ] 형식으로 포맷한다."""
    if card.special:
        return f"[ {_SPECIAL_NAMES[card.special]} ]"
    rank_str = _RANK_NAMES.get(int(card.rank), str(int(card.rank)))
    return f"[ {_SUIT_SYMBOLS[card.suit]} {rank_str} ]"


def format_cards(cards: list[Card]) -> str:
    """카드 리스트를 [ ♠ A ] [ ♥ K ] 형식으로 포맷한다."""
    return "  ".join(format_card(c) for c in cards)


class HumanPlayer(Player):
    """CLI 입력을 받는 사람 플레이어."""

    CARDS_PER_ROW = 4

    def _display_hand(self) -> None:
        """현재 손패를 번호와 함께 박스 형태로 출력한다."""
        print(f"\n  [손패] {len(self.cards)}장")
        for row_start in range(0, len(self.cards), self.CARDS_PER_ROW):
            row_end = min(row_start + self.CARDS_PER_ROW, len(self.cards))
            entries: list[str] = []
            for i in range(row_start, row_end):
                card = self.cards[i]
                pts = f" {card.points}점" if card.points != 0 else ""
                entry = f"{i:>2}: {format_card(card)}{pts}"
                entries.append(f"{entry:<20}")
            print(f"    {''.join(entries)}")

    def _input_yes_no(self, prompt: str) -> bool:
        """y/n 입력을 받는다."""
        while True:
            answer = input(prompt).strip().lower()
            if answer in ("y", "n"):
                return answer == "y"
            print("  → y 또는 n을 입력하세요.")

    def _input_card_indices(
        self, prompt: str, count: int | None = None, allow_empty: bool = False
    ) -> list[int]:
        """카드 번호를 입력받는다.

        Args:
            prompt: 입력 안내 메시지.
            count: 정확히 선택해야 할 장수. None이면 자유.
            allow_empty: 빈 입력(패스) 허용 여부.
        """
        while True:
            raw = input(prompt).strip()
            if allow_empty and raw == "":
                return []
            try:
                indices = [int(x) for x in raw.replace(",", " ").split()]
            except ValueError:
                print("  → 숫자를 입력하세요. (예: 0 2 4)")
                continue

            if any(i < 0 or i >= len(self.cards) for i in indices):
                print(f"  → 0~{len(self.cards) - 1} 범위의 번호를 입력하세요.")
                continue
            if len(indices) != len(set(indices)):
                print("  → 중복된 번호가 있습니다.")
                continue
            if count is not None and len(indices) != count:
                print(f"  → 정확히 {count}장을 선택하세요.")
                continue
            if not allow_empty and len(indices) == 0:
                print("  → 최소 1장을 선택하세요.")
                continue
            return sorted(indices)

    # ── Dragon 트릭 수령자 오버라이드 ──────────────────

    def choose_dragon_recipient(
        self,
        opponents: list[tuple[int, str, int]],
        trick_play_log: list[tuple[int, list[Card]]],
    ) -> int:
        """사람: Dragon 트릭 수령자를 직접 선택한다."""
        print("\n  Dragon으로 트릭을 가져갔습니다! 누구에게 줄까요?")
        min_cards = min(cc for _, _, cc in opponents)
        has_diff = len(set(cc for _, _, cc in opponents)) > 1
        for i, (idx, name, cc) in enumerate(opponents):
            hint = " ← 손패 적음" if has_diff and cc == min_cards else ""
            print(f"  {i + 1}. {name} (남은 패: {cc}장){hint}")

        while True:
            raw = input(f"  선택 (1 or {len(opponents)}): ").strip()
            try:
                choice = int(raw)
                if 1 <= choice <= len(opponents):
                    return opponents[choice - 1][0]
            except ValueError:
                pass
            print("  → 올바른 번호를 입력하세요.")

    # ── AI 메서드 오버라이드 ──────────────────────────

    def decide_grand_tichu(self) -> bool:
        """첫 8장을 보고 그랜드 티츄를 선언할지 결정."""
        self._display_hand()
        return self._input_yes_no("  그랜드 티츄를 선언하시겠습니까? (y/n): ")

    def decide_tichu(self) -> bool:
        """14장을 보고 스몰 티츄를 선언할지 결정."""
        self._display_hand()
        return self._input_yes_no("  스몰 티츄를 선언하시겠습니까? (y/n): ")

    def select_pass_cards(self) -> list[Card]:
        """패싱할 3장을 선택한다. [왼쪽, 오른쪽, 맞은편]."""
        print("\n  카드 패싱: 왼쪽 / 오른쪽 / 맞은편에 1장씩 전달합니다.")
        self._display_hand()

        targets = ["왼쪽", "오른쪽", "맞은편"]
        selected: list[Card] = []
        used_indices: set[int] = set()

        for target in targets:
            while True:
                indices = self._input_card_indices(
                    f"  {target}에게 줄 카드 번호: ", count=1
                )
                idx = indices[0]
                if idx in used_indices:
                    print("  → 이미 선택한 카드입니다.")
                    continue
                used_indices.add(idx)
                selected.append(self.cards[idx])
                break

        return selected

    def select_play(
        self,
        table_cards: list[Card] | None,
        table_effective_rank: float | None = None,
    ) -> list[Card] | None:
        """낼 카드를 선택한다."""
        if table_cards is None:
            print("\n  ── 선공입니다 ──")
        else:
            hand_type = HandValidator.classify(table_cards)
            type_name = hand_type.name if hand_type else "?"
            print(f"\n  ── 테이블: {format_cards(table_cards)}"
                  f"  ({type_name}) ──")

        self._display_hand()

        is_lead = table_cards is None

        # ── 후공 시 낼 수 있는 카드 없음 체크 ──
        if not is_lead and table_cards is not None:
            table_info = HandValidator._classify_full(table_cards)
            if table_info is not None:
                has_normal_play = (
                    self._find_weakest_beat(table_info, table_effective_rank)
                    is not None
                )
                if not has_normal_play:
                    has_bomb = (
                        self._find_weakest_bomb_beating(table_info)
                        is not None
                    )
                    if not has_bomb:
                        print("\n  낼 수 있는 카드가 없습니다. 자동 패스합니다.")
                        return None
                    print("\n  낼 수 있는 카드가 없지만 폭탄을 보유 중입니다.")
                    if not self._input_yes_no(
                        "  폭탄 사용 여부를 선택하세요"
                        " (y: 폭탄 사용 / n: 패스): "
                    ):
                        return None

        while True:
            raw = input(
                "  낼 카드 번호를 선택하세요"
                + ("" if is_lead else " (패스: Enter)")
                + ": "
            ).strip()

            if raw == "":
                if is_lead:
                    print("  → 선 플레이어는 패스할 수 없습니다.")
                else:
                    return None
                continue

            try:
                indices = sorted(set(
                    int(x) for x in raw.replace(",", " ").split()
                ))
            except ValueError:
                print("  → 숫자를 입력하세요. (예: 0 2 4)")
                continue

            if any(i < 0 or i >= len(self.cards) for i in indices):
                print(f"  → 0~{len(self.cards) - 1} 범위의 번호를 입력하세요.")
                continue

            play = [self.cards[i] for i in indices]

            # 유효한 패인지 확인
            classified = HandValidator.classify(play)
            if classified is None:
                print("  → 유효하지 않은 카드 조합입니다.")
                continue

            # 후공 시 이길 수 있는지 확인
            if table_cards is not None:
                if not self._can_beat_preview(
                    table_cards, table_effective_rank, play
                ):
                    print("  → 테이블의 패를 이길 수 없습니다.")
                    continue

            return play

    def _can_beat_preview(
        self,
        table_cards: list[Card],
        table_effective_rank: float | None,
        play: list[Card],
    ) -> bool:
        """간이 비교: 사용자에게 피드백을 주기 위한 사전 검증."""
        play_type = HandValidator.classify(play)
        table_type = HandValidator.classify(table_cards)
        if play_type is None or table_type is None:
            return False

        BOMBS = {HandType.FOUR_OF_A_KIND, HandType.STRAIGHT_FLUSH}
        if play_type in BOMBS and table_type not in BOMBS:
            return True

        # 싱글 대 싱글: effective rank 기반 비교
        if (table_type == HandType.SINGLE and play_type == HandType.SINGLE
                and len(table_cards) == 1 and len(play) == 1
                and table_effective_rank is not None):
            played_card = play[0]
            if played_card.special == SpecialCard.DRAGON:
                return table_effective_rank < 25.0
            if played_card.special == SpecialCard.PHOENIX:
                return table_effective_rank < 25.0
            return played_card.rank > table_effective_rank

        return HandValidator.can_beat(table_cards, play)
