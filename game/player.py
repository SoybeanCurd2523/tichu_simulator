"""플레이어 클래스 정의.

AI 로직은 이 모듈에 격리한다.
"""

from __future__ import annotations

from dataclasses import dataclass

from game.card import Card, SpecialCard, Suit
from game.hand import ClassifiedHand, HandType, HandValidator


# ── 카드 강도 · 특수 카드 7개 ────────────────────────
# Dragon, Phoenix, Mahjong, A♠, A♥, A♦, A♣
ACE_RANK = 14


def _card_strength(card: Card) -> float:
    """카드 강도: Dog(0) < 2 < … < A(14) < Phoenix(15) < Dragon(25)."""
    if card.special == SpecialCard.DOG:
        return 0.0
    if card.special == SpecialCard.PHOENIX:
        return 15.0
    if card.special == SpecialCard.DRAGON:
        return 25.0
    return float(card.rank)


def _is_special_seven(card: Card) -> bool:
    """특수 카드 7개 중 하나인지 판별."""
    if card.special in (SpecialCard.DRAGON, SpecialCard.PHOENIX, SpecialCard.MAHJONG):
        return True
    return card.rank == ACE_RANK and card.special is None


def _count_special_seven(cards: list[Card]) -> int:
    """특수 카드 7개 중 보유 수."""
    return sum(1 for c in cards if _is_special_seven(c))


@dataclass
class GameContext:
    """AI 판단에 필요한 게임 상태."""

    my_idx: int
    trick_winner_idx: int | None  # None이면 선공
    players_team: list[int]
    players_tichu: list[bool]
    players_grand_tichu: list[bool]
    players_finished: list[bool]
    players_card_count: list[int]


class Player:
    """티츄 플레이어.

    Attributes:
        name: 플레이어 이름.
        team: 팀 번호 (0 또는 1).
    """

    def __init__(self, name: str, team: int) -> None:
        self.name = name
        self.team = team
        self.cards: list[Card] = []
        self.tichu_called: bool = False
        self.grand_tichu_called: bool = False
        self.finished: bool = False
        self.finish_order: int = 0
        self._has_played_first_card: bool = False
        self._game_context: GameContext | None = None

    def reset(self) -> None:
        """라운드 시작 시 상태를 초기화한다."""
        self.cards = []
        self.finished = False
        self.finish_order = 0
        self.tichu_called = False
        self.grand_tichu_called = False
        self._has_played_first_card = False
        self._game_context = None

    def receive_cards(self, cards: list[Card]) -> None:
        """카드를 받는다."""
        self.cards.extend(cards)
        self.cards.sort(key=lambda c: c.rank)

    def has_mahjong(self) -> bool:
        """Mahjong 카드 보유 여부."""
        return any(c.special == SpecialCard.MAHJONG for c in self.cards)

    def remove_cards(self, cards: list[Card]) -> None:
        """낸 카드를 패에서 제거한다."""
        for card in cards:
            self.cards.remove(card)

    def hand_empty(self) -> bool:
        """패가 비었는지 확인."""
        return len(self.cards) == 0

    def call_tichu(self) -> None:
        """스몰 티츄를 선언한다."""
        self.tichu_called = True

    def call_grand_tichu(self) -> None:
        """그랜드 티츄를 선언한다."""
        self.grand_tichu_called = True

    def set_game_context(self, ctx: GameContext) -> None:
        """게임 상태를 AI에 전달한다."""
        self._game_context = ctx

    # ── Dragon 트릭 수령자 ─────────────────────────────

    def choose_dragon_recipient(
        self,
        opponents: list[tuple[int, str, int]],
        trick_play_log: list[tuple[int, list[Card]]],
    ) -> int:
        """Dragon 트릭 수령자를 선택한다.

        Args:
            opponents: 활성 상대 목록 [(idx, name, card_count), ...].
            trick_play_log: 현재 트릭의 플레이 기록 [(player_idx, cards), ...].

        Returns:
            선택된 상대의 플레이어 인덱스.

        AI 우선순위:
            (1) 손패가 가장 적은 활성 상대 → 4등 가능성 높음
            (2) 손패 수가 같다면 트릭에서 강한 카드를 낸 상대
            (3) 그 외 첫 번째 활성 상대
        """
        sorted_opps = sorted(opponents, key=lambda x: x[2])
        min_cards = sorted_opps[0][2]
        tied = [opp for opp in sorted_opps if opp[2] == min_cards]

        if len(tied) == 1:
            return tied[0][0]

        # 동률: 트릭에서 가장 강한 카드를 낸 상대
        if trick_play_log:
            tied_indices = {opp[0] for opp in tied}
            best_idx: int | None = None
            best_strength = -1.0
            for play_idx, play_cards in trick_play_log:
                if play_idx in tied_indices:
                    strength = max(_card_strength(c) for c in play_cards)
                    if strength > best_strength:
                        best_strength = strength
                        best_idx = play_idx
            if best_idx is not None:
                return best_idx

        return tied[0][0]

    # ── AI 메서드 ──────────────────────────────────────

    def decide_grand_tichu(self) -> bool:
        """AI: 첫 8장 중 특수 카드 7개 중 4개 이상이면 선언."""
        return _count_special_seven(self.cards) >= 4

    def decide_tichu(self) -> bool:
        """AI: 특수 카드 7개 중 3개 이상이면 스몰 티츄 선언.

        첫 카드를 내기 직전에 호출된다.
        """
        if self.grand_tichu_called:
            return False
        return _count_special_seven(self.cards) >= 3

    def select_pass_cards(self) -> list[Card]:
        """AI: 패싱할 3장 선택. [왼쪽, 오른쪽, 맞은편]"""
        return self._smart_pass_cards()

    def select_play(
        self,
        table_cards: list[Card] | None,
        table_effective_rank: float | None = None,
    ) -> list[Card] | None:
        """AI: 낼 카드를 선택한다."""
        if table_cards is None:
            return self._select_lead()
        return self._select_follow(table_cards, table_effective_rank)

    # ── 카드 헬퍼 ─────────────────────────────────────

    def _get_special(self, special: SpecialCard) -> Card | None:
        """특정 특수 카드를 찾는다."""
        for c in self.cards:
            if c.special == special:
                return c
        return None

    def _group_by_int_rank(self) -> dict[int, list[Card]]:
        """일반 카드 + Mahjong을 정수 rank로 그룹화 (Dog·Dragon·Phoenix 제외)."""
        groups: dict[int, list[Card]] = {}
        for c in self.cards:
            if c.special in (
                SpecialCard.DOG, SpecialCard.DRAGON, SpecialCard.PHOENIX,
            ):
                continue
            groups.setdefault(int(c.rank), []).append(c)
        return groups

    # ── 패싱 전략 ─────────────────────────────────────

    def _smart_pass_cards(self) -> list[Card]:
        """전략적 패 교환.

        Dog → 오른쪽 상대, Mahjong 절대 전달 안 함.
        Case A/B (GT 선언 or 특수≥3): 상대에게 약한, 팀원에게 3번째 약한.
        Case C (특수<3): 팀원에게 가장 강한, 상대에게 약한.
        """
        dog = self._get_special(SpecialCard.DOG)
        special_count = _count_special_seven(self.cards)

        pool = sorted(
            (c for c in self.cards
             if c.special != SpecialCard.DOG
             and c.special != SpecialCard.MAHJONG),
            key=_card_strength,
        )

        strong_hand = self.grand_tichu_called or special_count >= 3

        if dog:
            to_right: Card = dog
            if strong_hand:
                to_left = pool[0]
                to_opposite = pool[1]
            else:
                to_left = pool[0]
                to_opposite = pool[-1]
        else:
            if strong_hand:
                to_left = pool[0]
                to_right = pool[1]
                to_opposite = pool[2]
            else:
                to_left = pool[0]
                to_right = pool[1]
                to_opposite = pool[-1]

        return [to_left, to_right, to_opposite]

    # ── 팀 · Tichu 전략 ──────────────────────────────

    def _should_pass(self) -> bool:
        """팀원 배려 / Tichu 대응 전략으로 패스해야 하는지 판단."""
        ctx = self._game_context
        if ctx is None or ctx.trick_winner_idx is None:
            return False

        my_team = ctx.players_team[ctx.my_idx]

        # 내가 Tichu → 절대 패스 안 함
        if ctx.players_tichu[ctx.my_idx] or ctx.players_grand_tichu[ctx.my_idx]:
            return False

        # 팀원이 Tichu → 무조건 패스
        partner_idx = (ctx.my_idx + 2) % 4
        if ctx.players_tichu[partner_idx] or ctx.players_grand_tichu[partner_idx]:
            return True

        winner_idx = ctx.trick_winner_idx
        winner_team = ctx.players_team[winner_idx]

        # 상대 Tichu 확인
        opponent_tichu_idx = None
        for i in range(4):
            if ctx.players_team[i] != my_team and (
                ctx.players_tichu[i] or ctx.players_grand_tichu[i]
            ):
                opponent_tichu_idx = i
                break

        if opponent_tichu_idx is not None:
            if winner_idx == opponent_tichu_idx:
                return False   # Tichu 선언자가 이김 → 막아야 함
            if winner_team != my_team:
                return True    # 다른 상대가 이김 → 놔둠 (Tichu 방해)
            return True        # 팀원이 이김 → 패스

        # 아무도 Tichu 안 함: 팀원이 이기고 있으면 패스
        return winner_team == my_team

    def _should_use_bomb(self) -> bool:
        """폭탄 사용이 정당한 상황인지."""
        ctx = self._game_context
        if ctx is None:
            return False
        my_team = ctx.players_team[ctx.my_idx]

        if ctx.players_tichu[ctx.my_idx] or ctx.players_grand_tichu[ctx.my_idx]:
            return True

        if ctx.trick_winner_idx is not None:
            winner_team = ctx.players_team[ctx.trick_winner_idx]
            if winner_team != my_team:
                for i in range(4):
                    if ctx.players_team[i] != my_team and (
                        ctx.players_tichu[i] or ctx.players_grand_tichu[i]
                    ):
                        return True
        return False

    # ── 리드 ──────────────────────────────────────────

    def _select_lead(self) -> list[Card]:
        """AI: 선공 카드 선택.

        Mahjong 보유 시 스트레이트에 포함해서 리드 시도.
        팀원 Tichu → Dog로 턴 넘기기.
        조합 우선순위: straight > pair_seq > full_house > triple > pair > single.
        강한 카드(A, Phoenix, Dragon) 미포함 조합 우선.
        """
        ctx = self._game_context

        mahjong = self._get_special(SpecialCard.MAHJONG)
        if mahjong:
            straight = self._find_mahjong_straight()
            if straight:
                return straight
            return [mahjong]

        # 팀원이 Tichu → Dog로 턴 넘기기
        if ctx is not None:
            partner = (ctx.my_idx + 2) % 4
            if (ctx.players_tichu[partner] or ctx.players_grand_tichu[partner]):
                if not ctx.players_finished[partner]:
                    dog = self._get_special(SpecialCard.DOG)
                    if dog:
                        return [dog]

        # 조합 리드 (우선순위별)
        combo = self._find_lead_combo()
        if combo:
            return combo

        # 가장 약한 일반 카드
        for card in sorted(self.cards, key=_card_strength):
            if card.special in (
                SpecialCard.DOG, SpecialCard.PHOENIX, SpecialCard.DRAGON,
            ):
                continue
            return [card]

        # 특수 카드만 남은 경우
        return [self.cards[0]]

    # ── 리드 조합 탐색 ────────────────────────────────

    def _find_mahjong_straight(self) -> list[Card] | None:
        """Mahjong(1)을 포함하는 가장 짧은 스트레이트."""
        by = self._group_by_int_rank()
        phoenix = self._get_special(SpecialCard.PHOENIX)

        for top in range(5, 15):
            needed = list(range(1, top + 1))
            missing = [r for r in needed if r not in by]
            if not missing:
                return [by[r][0] for r in needed]
            if len(missing) == 1 and phoenix:
                cards = [by[r][0] for r in needed if r in by]
                cards.append(phoenix)
                return cards
            if missing:
                break
        return None

    def _find_lead_combo(self) -> list[Card] | None:
        """리드용 조합. 우선순위: straight > pair_seq > full_house > triple > pair.

        Pass 1: 강한 카드(A, Phoenix, Dragon) 없는 조합 먼저.
        Pass 2: 강한 카드 포함 조합 허용.
        """
        finders = [
            self._lead_straight,
            self._lead_pair_seq,
            self._lead_full_house,
            self._lead_triple,
            self._lead_pair,
        ]
        for strong_ok in (False, True):
            for finder in finders:
                combo = finder(strong_ok)
                if combo:
                    return combo
        return None

    def _lead_straight(self, strong_ok: bool) -> list[Card] | None:
        by = self._group_by_int_rank()
        phoenix = self._get_special(SpecialCard.PHOENIX) if strong_ok else None
        max_rank = 14 if strong_ok else 13

        for top in range(5, max_rank + 1):
            start = top - 4
            if start < 1:
                continue
            needed = list(range(start, top + 1))
            missing = [r for r in needed if r not in by]

            if not missing:
                return [by[r][0] for r in needed]
            if len(missing) == 1 and phoenix:
                cards = [by[r][0] for r in needed if r in by]
                cards.append(phoenix)
                return cards
        return None

    def _lead_pair_seq(self, strong_ok: bool) -> list[Card] | None:
        by = self._group_by_int_rank()
        phoenix = self._get_special(SpecialCard.PHOENIX) if strong_ok else None
        max_rank = 14 if strong_ok else 13

        for top in range(3, max_rank + 1):
            start = top - 1
            if start < 2:
                continue
            needed = list(range(start, top + 1))
            short = [
                r for r in needed
                if r not in by or len(by[r]) < 2
            ]
            if not short:
                cards: list[Card] = []
                for r in needed:
                    cards.extend(by[r][:2])
                return cards
            if len(short) == 1 and phoenix:
                r_s = short[0]
                if r_s in by and len(by[r_s]) >= 1:
                    cards = []
                    for r in needed:
                        if r == r_s:
                            cards.extend([phoenix, by[r][0]])
                        else:
                            cards.extend(by[r][:2])
                    return cards
        return None

    def _lead_full_house(self, strong_ok: bool) -> list[Card] | None:
        by = self._group_by_int_rank()
        phoenix = self._get_special(SpecialCard.PHOENIX) if strong_ok else None
        max_rank = 14 if strong_ok else 13

        candidates: list[tuple[int, list[Card], bool]] = []
        for rank in sorted(by):
            if rank > max_rank:
                continue
            if len(by[rank]) >= 3:
                candidates.append((rank, by[rank][:3], False))
        if phoenix:
            for rank in sorted(by):
                if rank > max_rank:
                    continue
                if len(by[rank]) >= 2:
                    candidates.append((rank, [phoenix] + by[rank][:2], True))
        candidates.sort(key=lambda x: x[0])

        for t_rank, t_cards, uses_ph in candidates:
            for pr in sorted(by):
                if pr == t_rank or pr > max_rank:
                    continue
                if len(by[pr]) >= 2:
                    return t_cards + by[pr][:2]
                if not uses_ph and phoenix and len(by[pr]) >= 1:
                    return t_cards + [phoenix, by[pr][0]]
        return None

    def _lead_triple(self, strong_ok: bool) -> list[Card] | None:
        by = self._group_by_int_rank()
        phoenix = self._get_special(SpecialCard.PHOENIX) if strong_ok else None
        max_rank = 14 if strong_ok else 13

        for rank in sorted(by):
            if rank > max_rank:
                continue
            if len(by[rank]) >= 3:
                return by[rank][:3]
        if phoenix:
            for rank in sorted(by):
                if rank > max_rank:
                    continue
                if len(by[rank]) >= 2:
                    return [phoenix] + by[rank][:2]
        return None

    def _lead_pair(self, strong_ok: bool) -> list[Card] | None:
        by = self._group_by_int_rank()
        phoenix = self._get_special(SpecialCard.PHOENIX) if strong_ok else None
        max_rank = 14 if strong_ok else 13

        for rank in sorted(by):
            if rank > max_rank:
                continue
            if len(by[rank]) >= 2:
                return by[rank][:2]
        if phoenix:
            for rank in sorted(by):
                if rank > max_rank:
                    continue
                return [phoenix, by[rank][0]]
        return None

    # ── 팔로우 ────────────────────────────────────────

    def _select_follow(
        self,
        table_cards: list[Card],
        table_effective_rank: float | None,
    ) -> list[Card] | None:
        """AI: 후공 카드 선택 — 테이블 타입에 맞는 가장 약한 조합."""
        if self._should_pass():
            return None

        table_info = HandValidator._classify_full(table_cards)
        if table_info is None:
            return None

        play = self._find_weakest_beat(table_info, table_effective_rank)
        if play:
            return play

        if self._should_use_bomb():
            bomb = self._find_weakest_bomb_beating(table_info)
            if bomb:
                return bomb

        return None

    # ── 조합 탐색 ─────────────────────────────────────

    def _find_weakest_beat(
        self, table_info: ClassifiedHand, table_eff: float | None,
    ) -> list[Card] | None:
        """테이블을 이기는 가장 약한 같은-타입 조합."""
        ht = table_info.hand_type
        s = table_info.strength
        n = table_info.length

        if ht == HandType.SINGLE:
            eff = table_eff if table_eff is not None else s
            return self._beat_single(eff)
        if ht == HandType.PAIR:
            return self._beat_pair(s)
        if ht == HandType.TRIPLE:
            return self._beat_triple(s)
        if ht == HandType.FULL_HOUSE:
            return self._beat_full_house(s)
        if ht == HandType.STRAIGHT:
            return self._beat_straight(s, n)
        if ht == HandType.PAIR_SEQUENCE:
            return self._beat_pair_sequence(s, n)
        if ht == HandType.FOUR_OF_A_KIND:
            return self._beat_four(s)
        if ht == HandType.STRAIGHT_FLUSH:
            return self._beat_sf(s, n)
        return None

    # ── 싱글 ──

    def _beat_single(self, eff: float) -> list[Card] | None:
        """가장 약한 싱글. Phoenix는 A(14)만 잡는다."""
        for c in sorted(self.cards, key=_card_strength):
            if c.special in (
                SpecialCard.DOG, SpecialCard.PHOENIX, SpecialCard.DRAGON,
            ):
                continue
            if c.rank > eff:
                return [c]

        phoenix = self._get_special(SpecialCard.PHOENIX)
        if phoenix and eff == ACE_RANK:
            return [phoenix]

        dragon = self._get_special(SpecialCard.DRAGON)
        if dragon and eff < 25.0:
            return [dragon]

        return None

    # ── 페어 ──

    def _beat_pair(self, min_rank: float) -> list[Card] | None:
        """가장 약한 페어 (자연 페어와 Phoenix 페어 중 약한 쪽)."""
        by = self._group_by_int_rank()
        phoenix = self._get_special(SpecialCard.PHOENIX)

        natural: tuple[int, list[Card]] | None = None
        for rank in sorted(by):
            if rank <= min_rank:
                continue
            if len(by[rank]) >= 2:
                natural = (rank, by[rank][:2])
                break

        phoenix_pair: tuple[int, list[Card]] | None = None
        if phoenix:
            for rank in sorted(by):
                if rank <= min_rank:
                    continue
                phoenix_pair = (rank, [phoenix, by[rank][0]])
                break

        if natural and phoenix_pair:
            return natural[1] if natural[0] <= phoenix_pair[0] else phoenix_pair[1]
        if natural:
            return natural[1]
        if phoenix_pair:
            return phoenix_pair[1]
        return None

    # ── 트리플 ──

    def _beat_triple(self, min_rank: float) -> list[Card] | None:
        """가장 약한 트리플."""
        by = self._group_by_int_rank()
        phoenix = self._get_special(SpecialCard.PHOENIX)

        natural: tuple[int, list[Card]] | None = None
        for rank in sorted(by):
            if rank <= min_rank:
                continue
            if len(by[rank]) >= 3:
                natural = (rank, by[rank][:3])
                break

        phoenix_triple: tuple[int, list[Card]] | None = None
        if phoenix:
            for rank in sorted(by):
                if rank <= min_rank:
                    continue
                if len(by[rank]) >= 2:
                    phoenix_triple = (rank, [phoenix] + by[rank][:2])
                    break

        if natural and phoenix_triple:
            return (natural[1] if natural[0] <= phoenix_triple[0]
                    else phoenix_triple[1])
        if natural:
            return natural[1]
        if phoenix_triple:
            return phoenix_triple[1]
        return None

    # ── 풀하우스 ──

    def _beat_full_house(self, min_triple: float) -> list[Card] | None:
        """가장 약한 풀하우스 (트리플 rank > min_triple)."""
        by = self._group_by_int_rank()
        phoenix = self._get_special(SpecialCard.PHOENIX)

        # 가능한 트리플 후보 (약한 순)
        candidates: list[tuple[int, list[Card], bool]] = []
        for rank in sorted(by):
            if rank <= min_triple:
                continue
            if len(by[rank]) >= 3:
                candidates.append((rank, by[rank][:3], False))

        if phoenix:
            for rank in sorted(by):
                if rank <= min_triple:
                    continue
                if len(by[rank]) >= 2:
                    candidates.append((rank, [phoenix] + by[rank][:2], True))

        candidates.sort(key=lambda x: x[0])

        for triple_rank, triple_cards, uses_ph in candidates:
            for pair_rank in sorted(by):
                if pair_rank == triple_rank:
                    continue
                if len(by[pair_rank]) >= 2:
                    return triple_cards + by[pair_rank][:2]
                if not uses_ph and phoenix and len(by[pair_rank]) >= 1:
                    return triple_cards + [phoenix, by[pair_rank][0]]
        return None

    # ── 스트레이트 ──

    def _beat_straight(self, min_top: float, length: int) -> list[Card] | None:
        """같은 길이, 더 높은 top rank의 가장 약한 스트레이트."""
        by = self._group_by_int_rank()
        phoenix = self._get_special(SpecialCard.PHOENIX)

        for top in range(int(min_top) + 1, 15):
            start = top - length + 1
            if start < 1:
                continue
            needed = list(range(start, top + 1))
            missing = [r for r in needed if r not in by]

            if not missing:
                return [by[r][0] for r in needed]
            if len(missing) == 1 and phoenix:
                cards = [by[r][0] for r in needed if r in by]
                cards.append(phoenix)
                return cards
        return None

    # ── 연속 페어 ──

    def _beat_pair_sequence(
        self, min_top: float, num_cards: int,
    ) -> list[Card] | None:
        """같은 길이, 더 높은 top rank의 가장 약한 연속 페어."""
        by = self._group_by_int_rank()
        phoenix = self._get_special(SpecialCard.PHOENIX)
        num_pairs = num_cards // 2

        for top in range(int(min_top) + 1, 15):
            start = top - num_pairs + 1
            if start < 2:
                continue
            needed = list(range(start, top + 1))
            short = [
                r for r in needed
                if r not in by or len(by[r]) < 2
            ]

            if not short:
                cards: list[Card] = []
                for r in needed:
                    cards.extend(by[r][:2])
                return cards
            if len(short) == 1 and phoenix:
                r_s = short[0]
                if r_s in by and len(by[r_s]) >= 1:
                    cards = []
                    for r in needed:
                        if r == r_s:
                            cards.extend([phoenix, by[r][0]])
                        else:
                            cards.extend(by[r][:2])
                    return cards
        return None

    # ── 포카드(폭탄) 대응 ──

    def _beat_four(self, min_rank: float) -> list[Card] | None:
        """더 높은 포카드 또는 SF."""
        by = self._group_by_int_rank()
        for rank in sorted(by):
            if rank <= min_rank:
                continue
            non_sp = [c for c in by[rank] if not c.is_special]
            if len(non_sp) >= 4:
                return non_sp[:4]
        sfs = self._find_all_straight_flushes()
        return sfs[0] if sfs else None

    # ── SF(폭탄) 대응 ──

    def _beat_sf(self, min_top: float, min_len: int) -> list[Card] | None:
        """더 긴 or 같은 길이에서 더 높은 SF."""
        for sf in self._find_all_straight_flushes():
            info = HandValidator._classify_full(sf)
            if info and (
                info.length > min_len
                or (info.length == min_len and info.strength > min_top)
            ):
                return sf
        return None

    # ── 폭탄 공통 ──

    def _find_weakest_bomb_beating(
        self, table_info: ClassifiedHand,
    ) -> list[Card] | None:
        """테이블을 이기는 가장 약한 폭탄."""
        BOMBS = {HandType.FOUR_OF_A_KIND, HandType.STRAIGHT_FLUSH}
        by = self._group_by_int_rank()

        if table_info.hand_type not in BOMBS:
            # 비-폭탄 → 아무 폭탄이면 됨
            for rank in sorted(by):
                non_sp = [c for c in by[rank] if not c.is_special]
                if len(non_sp) >= 4:
                    return non_sp[:4]
            sfs = self._find_all_straight_flushes()
            return sfs[0] if sfs else None

        if table_info.hand_type == HandType.FOUR_OF_A_KIND:
            return self._beat_four(table_info.strength)
        return self._beat_sf(table_info.strength, table_info.length)

    def _find_all_straight_flushes(self) -> list[list[Card]]:
        """모든 SF 폭탄을 찾아 약한 순으로 반환."""
        by_suit: dict[Suit, list[Card]] = {}
        for c in self.cards:
            if c.is_special:
                continue
            by_suit.setdefault(c.suit, []).append(c)

        results: list[list[Card]] = []
        for cards in by_suit.values():
            sc = sorted(cards, key=lambda c: c.rank)
            run: list[Card] = [sc[0]]
            for i in range(1, len(sc)):
                if sc[i].rank == run[-1].rank + 1:
                    run.append(sc[i])
                else:
                    self._extract_sf_runs(run, results)
                    run = [sc[i]]
            self._extract_sf_runs(run, results)

        results.sort(key=lambda sf: (len(sf), max(c.rank for c in sf)))
        return results

    @staticmethod
    def _extract_sf_runs(
        run: list[Card], out: list[list[Card]],
    ) -> None:
        """연속 런에서 길이 5 이상의 모든 SF 조합을 추출."""
        if len(run) < 5:
            return
        for sz in range(5, len(run) + 1):
            for st in range(len(run) - sz + 1):
                out.append(run[st : st + sz])

    def __str__(self) -> str:
        return f"Player({self.name}, team={self.team})"

    def __repr__(self) -> str:
        return str(self)
