"""패 유효성 검증 모듈.

모든 패 검증은 이 모듈에서만 처리한다.

티츄 패 종류 (8가지):
- Single: 카드 1장
- Pair: 같은 rank 2장 (Phoenix 와일드 가능)
- Triple: 같은 rank 3장 (Phoenix 와일드 가능)
- Full House: 트리플 + 페어, 5장 (Phoenix 와일드 가능)
- Straight: 5장 이상 연속, Ace는 최고값만 (Phoenix 와일드 가능)
- Pair Sequence: 인접 숫자 연속 페어 2쌍 이상, 4장 이상 (Phoenix 와일드 가능)
- Four of a Kind: 같은 rank 4장 — 폭탄 (Phoenix 사용 불가)
- Straight Flush: 같은 슈트 5장 이상 연속 — 폭탄 (Phoenix 사용 불가)

없는 조합:
- 플러쉬 (같은 슈트 비연속) ❌
- 투페어 (비인접 두 페어) ❌

특수 규칙:
- Phoenix: 와일드카드. 싱글/페어/트리플/풀하우스/스트레이트/연속페어에 사용 가능.
  폭탄(포카드/스트레이트 플러시)에는 사용 불가.
  싱글로 낼 때는 현재 최고 카드 +0.5로 동작.
- Dog: 싱글로만 낼 수 있다. 다른 조합에 포함 불가.
- Dragon: 싱글로만 낼 수 있다. 싱글 최강 카드.
- Mahjong(1): 싱글 또는 스트레이트에 포함 가능 (1로 취급, 맨 앞에만).

can_beat 규칙:
- 스티플 폭탄 > 포카드 폭탄 > 모든 비폭탄
- 같은 조합 타입 + 같은 길이일 때만 강도 비교 가능
- 다른 타입이거나 길이가 다르면 비교 불가 (낼 수 없음)
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import Enum, auto

from game.card import Card, SpecialCard, Suit


class HandType(Enum):
    """낼 수 있는 패 종류."""
    SINGLE = auto()
    PAIR = auto()
    TRIPLE = auto()
    FULL_HOUSE = auto()
    STRAIGHT = auto()
    PAIR_SEQUENCE = auto()
    FOUR_OF_A_KIND = auto()
    STRAIGHT_FLUSH = auto()


@dataclass(frozen=True)
class ClassifiedHand:
    """분류된 패 정보.

    Attributes:
        hand_type: 패 종류.
        strength: 패의 세기 (같은 종류 간 비교에 사용).
        length: 패의 카드 수 (스트레이트/연속페어 길이 비교용).
    """
    hand_type: HandType
    strength: float
    length: int


class HandValidator:
    """패 유효성 검증기."""

    @staticmethod
    def classify(cards: list[Card]) -> HandType | None:
        """카드 조합의 패 종류를 판별한다.

        Args:
            cards: 판별할 카드 리스트.

        Returns:
            HandType 또는 유효하지 않으면 None.
        """
        result = HandValidator._classify_full(cards)
        return result.hand_type if result else None

    @staticmethod
    def _classify_full(cards: list[Card]) -> ClassifiedHand | None:
        """패를 분류하고 세기 정보까지 반환한다."""
        if not cards:
            return None

        n = len(cards)
        has_phoenix = any(c.special == SpecialCard.PHOENIX for c in cards)
        has_dog = any(c.special == SpecialCard.DOG for c in cards)
        has_dragon = any(c.special == SpecialCard.DRAGON for c in cards)

        # Dog, Dragon은 싱글로만 낼 수 있다
        if has_dog:
            if n == 1:
                return ClassifiedHand(HandType.SINGLE, 0.0, 1)
            return None
        if has_dragon:
            if n == 1:
                return ClassifiedHand(HandType.SINGLE, 25.0, 1)
            return None

        # 일반 카드들의 rank (Phoenix 제외, Mahjong 포함)
        normal_ranks = sorted(
            c.rank for c in cards if c.special != SpecialCard.PHOENIX
        )

        # --- Single ---
        if n == 1:
            return ClassifiedHand(HandType.SINGLE, cards[0].rank, 1)

        # --- Pair ---
        if n == 2:
            if has_phoenix:
                # Phoenix + 일반카드 1장 = 페어
                return ClassifiedHand(HandType.PAIR, normal_ranks[0], 2)
            if normal_ranks[0] == normal_ranks[1]:
                return ClassifiedHand(HandType.PAIR, normal_ranks[0], 2)
            return None

        # --- Triple ---
        if n == 3:
            counts = Counter(normal_ranks)
            if has_phoenix:
                # Phoenix + 같은 rank 2장 = 트리플
                if len(counts) == 1 and len(normal_ranks) == 2:
                    return ClassifiedHand(HandType.TRIPLE, normal_ranks[0], 3)
                return None
            if len(counts) == 1:
                return ClassifiedHand(HandType.TRIPLE, normal_ranks[0], 3)
            return None

        # --- 4장: Four of a Kind 또는 연속 페어 ---
        if n == 4:
            # Four of a Kind (폭탄) — Phoenix 사용 불가
            non_special = [c for c in cards if not c.is_special]
            if len(non_special) == 4:
                non_special_ranks = [c.rank for c in non_special]
                if len(set(non_special_ranks)) == 1:
                    return ClassifiedHand(
                        HandType.FOUR_OF_A_KIND, non_special_ranks[0], 4
                    )

            # 연속 페어 (2쌍)
            ps = HandValidator._check_pair_sequence(cards, has_phoenix)
            if ps is not None:
                return ps

            return None

        # --- 5장: Full House, Straight Flush, Straight, 연속 페어 ---
        if n == 5:
            fh = HandValidator._check_full_house(cards, has_phoenix)
            if fh is not None:
                return fh

        # --- 5장 이상: Straight Flush (폭탄), Straight, 연속 페어 ---
        if n >= 5:
            sf = HandValidator._check_straight_flush(cards)
            if sf is not None:
                return sf

            st = HandValidator._check_straight(cards, has_phoenix)
            if st is not None:
                return st

        # --- 짝수장, 4장 이상: 연속 페어 ---
        if n >= 4 and n % 2 == 0:
            ps = HandValidator._check_pair_sequence(cards, has_phoenix)
            if ps is not None:
                return ps

        return None

    @staticmethod
    def _check_full_house(
        cards: list[Card], has_phoenix: bool
    ) -> ClassifiedHand | None:
        """풀하우스(트리플 + 페어) 여부를 검사한다.

        세기는 트리플 부분의 rank로 결정된다.
        """
        normal_ranks = [c.rank for c in cards if c.special != SpecialCard.PHOENIX]
        counts = Counter(normal_ranks)
        values = sorted(counts.values(), reverse=True)

        if has_phoenix:
            # Phoenix가 1장 → 일반 카드 4장
            # 가능한 조합: 2+2 (Phoenix가 하나를 3으로 만듦)
            if values == [2, 2]:
                # 세기: 더 높은 rank가 트리플이 됨
                triple_rank = max(counts.keys())
                return ClassifiedHand(HandType.FULL_HOUSE, triple_rank, 5)
            # 3+1 (Phoenix가 1을 페어로 만듦)
            if values == [3, 1]:
                triple_rank = [r for r, c in counts.items() if c == 3][0]
                return ClassifiedHand(HandType.FULL_HOUSE, triple_rank, 5)
            return None

        if values == [3, 2]:
            triple_rank = [r for r, c in counts.items() if c == 3][0]
            return ClassifiedHand(HandType.FULL_HOUSE, triple_rank, 5)
        return None

    @staticmethod
    def _check_straight(
        cards: list[Card], has_phoenix: bool
    ) -> ClassifiedHand | None:
        """스트레이트(5장 이상 연속) 여부를 검사한다.

        - Ace(14)는 최고값으로만 사용 (A-2-3-4-5 불가).
        - Mahjong(1)은 스트레이트에 포함 가능 (1-2-3-4-5).
        - Phoenix는 빈 자리 하나를 채울 수 있다.
        """
        normal_ranks = sorted(
            c.rank for c in cards if c.special != SpecialCard.PHOENIX
        )
        wilds = 1 if has_phoenix else 0
        n = len(cards)

        if len(normal_ranks) + wilds != n:
            return None

        # 중복 rank 불가
        if len(normal_ranks) != len(set(normal_ranks)):
            return None

        # 빈 자리 수 계산
        gaps = 0
        for i in range(1, len(normal_ranks)):
            diff = normal_ranks[i] - normal_ranks[i - 1]
            if diff < 1:
                return None
            gaps += diff - 1

        if gaps > wilds:
            return None

        # 세기: 스트레이트 최고 rank
        # Phoenix가 맨 위에 올 수도 있음
        top_rank = normal_ranks[-1]
        if wilds > 0 and gaps == 0:
            # 빈 자리가 없으면 Phoenix가 위나 아래에 붙음
            top_rank = normal_ranks[-1] + 1
        elif wilds > 0 and gaps > 0:
            # 빈 자리를 채운 경우 — 최고는 그대로
            top_rank = normal_ranks[-1]

        return ClassifiedHand(HandType.STRAIGHT, top_rank, n)

    @staticmethod
    def _check_straight_flush(cards: list[Card]) -> ClassifiedHand | None:
        """스트레이트 플러시(폭탄) 여부를 검사한다.

        폭탄이므로 Phoenix 사용 불가. 모두 일반 카드 + 같은 슈트.
        Mahjong(1)은 포함 가능 (1은 suit가 없으므로 제외).
        → 실제로 Mahjong은 special 카드이므로 스트레이트 플러시에 포함 불가.
        """
        # 특수 카드가 하나라도 있으면 불가
        if any(c.is_special for c in cards):
            return None

        suits = {c.suit for c in cards}
        if len(suits) != 1:
            return None

        ranks = sorted(c.rank for c in cards)
        for i in range(1, len(ranks)):
            if ranks[i] - ranks[i - 1] != 1:
                return None

        return ClassifiedHand(
            HandType.STRAIGHT_FLUSH, ranks[-1], len(cards)
        )

    @staticmethod
    def _check_pair_sequence(
        cards: list[Card], has_phoenix: bool
    ) -> ClassifiedHand | None:
        """연속 페어(2쌍 이상) 여부를 검사한다.

        세기는 연속 페어의 최고 rank로 결정된다.
        """
        n = len(cards)
        if n < 4 or n % 2 != 0:
            return None

        normal_ranks = [
            c.rank for c in cards if c.special != SpecialCard.PHOENIX
        ]
        counts = Counter(normal_ranks)

        num_pairs = n // 2  # 필요한 페어 수

        if has_phoenix:
            # Phoenix가 단일 카드 하나를 페어로 만듦
            singles = [r for r, c in counts.items() if c == 1]
            pairs = [r for r, c in counts.items() if c == 2]
            if len(singles) != 1 or len(pairs) != num_pairs - 1:
                return None
            all_pair_ranks = sorted(pairs + singles)
        else:
            if not all(v == 2 for v in counts.values()):
                return None
            if len(counts) != num_pairs:
                return None
            all_pair_ranks = sorted(counts.keys())

        # 연속인지 확인
        for i in range(1, len(all_pair_ranks)):
            if all_pair_ranks[i] - all_pair_ranks[i - 1] != 1:
                return None

        return ClassifiedHand(
            HandType.PAIR_SEQUENCE, all_pair_ranks[-1], n
        )

    @staticmethod
    def can_beat(current: list[Card], played: list[Card]) -> bool:
        """played가 current를 이길 수 있는지 판별한다.

        규칙:
        1. 폭탄(4장/SF)은 비-폭탄 패를 무조건 이긴다.
        2. SF 폭탄 > 4장 폭탄. SF끼리는 길이 → rank 순 비교.
        3. 4장 폭탄끼리는 rank 비교.
        4. 같은 HandType, 같은 길이일 때만 rank로 비교.
        5. Dragon 싱글은 Phoenix 싱글에 이긴다.
           Phoenix 싱글은 current_top + 0.5로 비교.

        Args:
            current: 현재 테이블 위의 패.
            played: 내려고 하는 패.

        Returns:
            이길 수 있으면 True.
        """
        cur = HandValidator._classify_full(current)
        ply = HandValidator._classify_full(played)

        if cur is None or ply is None:
            return False

        BOMBS = {HandType.FOUR_OF_A_KIND, HandType.STRAIGHT_FLUSH}

        cur_is_bomb = cur.hand_type in BOMBS
        ply_is_bomb = ply.hand_type in BOMBS

        # 폭탄 vs 비-폭탄
        if ply_is_bomb and not cur_is_bomb:
            return True
        if not ply_is_bomb and cur_is_bomb:
            return False

        # 폭탄 vs 폭탄
        if ply_is_bomb and cur_is_bomb:
            # SF > 4장
            if (ply.hand_type == HandType.STRAIGHT_FLUSH
                    and cur.hand_type == HandType.FOUR_OF_A_KIND):
                return True
            if (ply.hand_type == HandType.FOUR_OF_A_KIND
                    and cur.hand_type == HandType.STRAIGHT_FLUSH):
                return False
            # 같은 폭탄 종류끼리
            if ply.hand_type == HandType.STRAIGHT_FLUSH:
                # 길이가 긴 SF가 이김, 같으면 rank 비교
                if ply.length != cur.length:
                    return ply.length > cur.length
                return ply.strength > cur.strength
            # 4장 폭탄끼리: rank 비교
            return ply.strength > cur.strength

        # 일반 패끼리: 같은 종류, 같은 길이만 비교 가능
        if cur.hand_type != ply.hand_type:
            return False
        if cur.length != ply.length:
            return False

        # 싱글 Phoenix 특수 처리
        if cur.hand_type == HandType.SINGLE:
            played_card = played[0]
            current_card = current[0]

            # Dragon은 싱글 최강
            if played_card.special == SpecialCard.DRAGON:
                # Dragon은 Dog 위에 못 낸다 (Dog는 비교 대상 자체가 아님)
                return current_card.special != SpecialCard.DRAGON

            # Phoenix 싱글: current + 0.5
            if played_card.special == SpecialCard.PHOENIX:
                if current_card.special == SpecialCard.DRAGON:
                    return False
                effective = played_card.phoenix_rank(current_card.rank)
                return effective > current_card.rank

            # current가 Phoenix인 경우: Phoenix의 rank는 그 앞 카드 기준
            # 하지만 테이블 위의 Phoenix는 이미 +0.5가 적용된 상태
            # played의 일반 카드가 이기려면 current의 실효 rank보다 커야 함
            # → 여기서는 cur.strength가 Phoenix의 base_rank(1.5)이므로
            #   일반 카드는 rank 2부터 이김
            pass

        return ply.strength > cur.strength
