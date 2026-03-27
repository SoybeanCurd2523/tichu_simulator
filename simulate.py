#!/usr/bin/env python
"""4인 AI 자동 시뮬레이션.

사용법:
    python simulate.py --games 1000
    python simulate.py --games 500 --save-csv --verbose
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter, defaultdict

from game.card import Card, SpecialCard, Suit
from game.game import Game
from game.scoring import ScoreCalculator


# ── 상수 ───────────────────────────────────────────────

SPECIAL_FIELDS = [
    ("has_dragon", "Dragon"),
    ("has_phoenix", "Phoenix"),
    ("has_mahjong", "Mahjong"),
    ("has_ace_spade", "A♠"),
    ("has_ace_heart", "A♥"),
    ("has_ace_diamond", "A♦"),
    ("has_ace_club", "A♣"),
]

CSV_COLUMNS = [
    "game_id", "round_id", "player_id", "finish_order",
    "has_dragon", "has_phoenix", "has_mahjong",
    "has_ace_spade", "has_ace_heart", "has_ace_diamond", "has_ace_club",
    "special_count", "avg_rank", "max_rank", "has_bomb", "bomb_type",
    "gt_declared", "gt_success", "st_declared", "st_success",
    "round_score",
]


# ── 헬퍼 ──────────────────────────────────────────────

def detect_bomb(cards: list[Card]) -> tuple[bool, str]:
    """손패에서 폭탄 보유 여부와 종류를 판별한다.

    Returns:
        (has_bomb, bomb_type) — bomb_type은 "four_of_kind", "straight_flush", "none".
        스트레이트 플러시가 포카드보다 우선 표시된다.
    """
    # 스트레이트 플러시 체크
    by_suit: dict[Suit, list[float]] = {}
    for c in cards:
        if c.is_special:
            continue
        by_suit.setdefault(c.suit, []).append(c.rank)

    has_sf = False
    for ranks in by_suit.values():
        ranks_sorted = sorted(ranks)
        run = 1
        for i in range(1, len(ranks_sorted)):
            if ranks_sorted[i] == ranks_sorted[i - 1] + 1:
                run += 1
                if run >= 5:
                    has_sf = True
                    break
            else:
                run = 1
        if has_sf:
            break

    if has_sf:
        return True, "straight_flush"

    # 포카드 체크
    rank_counts = Counter(
        int(c.rank) for c in cards if not c.is_special
    )
    if any(v >= 4 for v in rank_counts.values()):
        return True, "four_of_kind"

    return False, "none"


def analyze_hand(cards: list[Card]) -> dict:
    """손패의 특성을 분석한다."""
    has_dragon = int(any(c.special == SpecialCard.DRAGON for c in cards))
    has_phoenix = int(any(c.special == SpecialCard.PHOENIX for c in cards))
    has_mahjong = int(any(c.special == SpecialCard.MAHJONG for c in cards))
    has_ace_spade = int(any(
        c.rank == 14 and c.suit == Suit.SWORD and not c.is_special
        for c in cards
    ))
    has_ace_heart = int(any(
        c.rank == 14 and c.suit == Suit.STAR and not c.is_special
        for c in cards
    ))
    has_ace_diamond = int(any(
        c.rank == 14 and c.suit == Suit.PAGODA and not c.is_special
        for c in cards
    ))
    has_ace_club = int(any(
        c.rank == 14 and c.suit == Suit.JADE and not c.is_special
        for c in cards
    ))

    special_count = (
        has_dragon + has_phoenix + has_mahjong
        + has_ace_spade + has_ace_heart + has_ace_diamond + has_ace_club
    )

    normal = [c for c in cards if not c.is_special]
    avg_rank = sum(c.rank for c in normal) / len(normal) if normal else 0.0
    max_rank = max((int(c.rank) for c in normal), default=0)

    has_bomb, bomb_type = detect_bomb(cards)

    return {
        "has_dragon": has_dragon,
        "has_phoenix": has_phoenix,
        "has_mahjong": has_mahjong,
        "has_ace_spade": has_ace_spade,
        "has_ace_heart": has_ace_heart,
        "has_ace_diamond": has_ace_diamond,
        "has_ace_club": has_ace_club,
        "special_count": special_count,
        "avg_rank": round(avg_rank, 2),
        "max_rank": max_rank,
        "has_bomb": int(has_bomb),
        "bomb_type": bomb_type,
    }


def get_combo_name(record: dict) -> str:
    """보유 특수 카드 조합 이름을 생성한다."""
    parts = []
    for field, name in SPECIAL_FIELDS:
        if record[field]:
            parts.append(name)
    return "+".join(parts) if parts else "(없음)"


# ── SimGame ────────────────────────────────────────────


class SimGame(Game):
    """데이터 수집용 Game 서브클래스.

    매 라운드마다 손패 특성과 결과를 기록한다.
    """

    def __init__(self, game_id: int = 0, verbose: bool = False) -> None:
        super().__init__()
        self.game_id = game_id
        self.verbose = verbose
        self.records: list[dict] = []
        self._round_id = 0

    def _play_round_with_cards(
        self,
        first_hands: list[list[Card]],
        remaining_hands: list[list[Card]],
    ) -> dict[int, int]:
        """라운드 진행 + 데이터 캡처."""
        self._round_id += 1

        # 1. 초기화
        for p in self.players:
            p.reset()

        # 2. 첫 8장 + Grand Tichu 선언
        for i, player in enumerate(self.players):
            player.receive_cards(first_hands[i])
        for player in self.players:
            if player.decide_grand_tichu():
                player.call_grand_tichu()

        # 3. 나머지 6장
        for i, player in enumerate(self.players):
            player.receive_cards(remaining_hands[i])

        # 4. 카드 패싱
        self._pass_cards()

        # ★ 손패 특성 캡처 (패싱 후, 트릭 전)
        hand_data = [analyze_hand(p.cards) for p in self.players]

        # 5. 트릭 플레이
        start_idx = self._find_starting_player()
        tricks_won, finish_order = self._play_tricks(start_idx)

        # 6. 점수 계산
        round_scores = ScoreCalculator.calculate_round_score(
            self.players, tricks_won, finish_order,
        )
        for team, score in round_scores.items():
            self.team_scores[team] += score

        # ★ 결과 캡처
        one_two = False
        if len(finish_order) >= 2:
            t1 = self._team_of(finish_order[0])
            t2 = self._team_of(finish_order[1])
            one_two = t1 == t2

        for i, p in enumerate(self.players):
            record = {
                "game_id": self.game_id,
                "round_id": self._round_id,
                "player_id": i,
                **hand_data[i],
                "finish_order": p.finish_order,
                "gt_declared": int(p.grand_tichu_called),
                "gt_success": int(
                    p.grand_tichu_called and p.finish_order == 1
                ),
                "st_declared": int(p.tichu_called),
                "st_success": int(
                    p.tichu_called and p.finish_order == 1
                ),
                "round_score": round_scores[p.team],
                "one_two_finish": int(one_two),
            }
            self.records.append(record)

        if self.verbose:
            gt_st = ""
            for p in self.players:
                if p.grand_tichu_called:
                    ok = "O" if p.finish_order == 1 else "X"
                    gt_st += f" GT:{p.name}({ok})"
                if p.tichu_called:
                    ok = "O" if p.finish_order == 1 else "X"
                    gt_st += f" ST:{p.name}({ok})"
            print(
                f"  R{self._round_id:>2}: "
                f"팀0={round_scores[0]:>+4d}  팀1={round_scores[1]:>+4d}  "
                f"순위={','.join(finish_order)}{gt_st}"
            )

        return round_scores


# ── 통계 출력 ──────────────────────────────────────────


def _avg(values: list[float | int]) -> float:
    return sum(values) / len(values) if values else 0.0


def _print_combo_stats(
    records: list[dict], success_field: str, top_n: int = 20,
) -> None:
    """특수 카드 조합별 성공률을 출력한다."""
    combos: dict[str, list[int]] = defaultdict(list)
    for r in records:
        key = get_combo_name(r)
        combos[key].append(r[success_field])

    sorted_combos = sorted(combos.items(), key=lambda x: -len(x[1]))
    for combo, vals in sorted_combos[:top_n]:
        rate = sum(vals) / len(vals) * 100
        print(
            f"  {combo:<40}  성공 {rate:5.1f}%"
            f"  ({sum(vals):>3d}/{len(vals):<3d})"
        )


def print_stats(records: list[dict]) -> None:
    """전체 통계를 출력한다."""
    total_rounds = len(records) // 4

    print("\n" + "=" * 60)
    print("  시뮬레이션 결과 통계")
    print("=" * 60)

    # ── 1. 특수 카드 수별 평균 등수 ─────────────────────
    print("\n[1] 특수 카드 수별 평균 등수")
    print("-" * 50)
    by_special: dict[int, list[int]] = defaultdict(list)
    for r in records:
        by_special[r["special_count"]].append(r["finish_order"])
    for cnt in sorted(by_special):
        vals = by_special[cnt]
        print(f"  특수 {cnt}개  →  평균 {_avg(vals):.2f}등  (n={len(vals):,})")

    # ── 2. 특수 카드 종류별 보유 시 평균 등수 ───────────
    print("\n[2] 특수 카드 종류별 보유 시 평균 등수")
    print("-" * 50)
    for field, name in SPECIAL_FIELDS:
        vals = [r["finish_order"] for r in records if r[field]]
        if vals:
            print(
                f"  {name:<10} 보유  →  평균 {_avg(vals):.2f}등"
                f"  (n={len(vals):,})"
            )

    # ── 3. Grand Tichu 특수 카드 수별 성공률 ────────────
    gt_records = [r for r in records if r["gt_declared"]]
    print(
        f"\n[3] Grand Tichu 선언 시 특수 카드 수별 성공률"
        f"  (총 {len(gt_records):,}건)"
    )
    print("-" * 50)
    if gt_records:
        by_cnt: dict[int, list[int]] = defaultdict(list)
        for r in gt_records:
            by_cnt[r["special_count"]].append(r["gt_success"])
        for cnt in sorted(by_cnt):
            vals = by_cnt[cnt]
            rate = sum(vals) / len(vals) * 100
            print(
                f"  특수 {cnt}개  →  성공 {rate:5.1f}%"
                f"  ({sum(vals):>3d}/{len(vals):<3d})"
            )
    else:
        print("  (선언 없음)")

    # ── 4. Grand Tichu 특수 카드 조합별 성공률 ──────────
    print("\n[4] Grand Tichu 선언 시 특수 카드 조합별 성공률")
    print("-" * 50)
    if gt_records:
        _print_combo_stats(gt_records, "gt_success")
    else:
        print("  (선언 없음)")

    # ── 5. Small Tichu 특수 카드 수별 성공률 ────────────
    st_records = [r for r in records if r["st_declared"]]
    print(
        f"\n[5] Small Tichu 선언 시 특수 카드 수별 성공률"
        f"  (총 {len(st_records):,}건)"
    )
    print("-" * 50)
    if st_records:
        by_cnt = defaultdict(list)
        for r in st_records:
            by_cnt[r["special_count"]].append(r["st_success"])
        for cnt in sorted(by_cnt):
            vals = by_cnt[cnt]
            rate = sum(vals) / len(vals) * 100
            print(
                f"  특수 {cnt}개  →  성공 {rate:5.1f}%"
                f"  ({sum(vals):>3d}/{len(vals):<3d})"
            )
    else:
        print("  (선언 없음)")

    # ── 6. Small Tichu 특수 카드 조합별 성공률 ──────────
    print("\n[6] Small Tichu 선언 시 특수 카드 조합별 성공률")
    print("-" * 50)
    if st_records:
        _print_combo_stats(st_records, "st_success")
    else:
        print("  (선언 없음)")

    # ── 7. 손패 평균 rank 구간별 평균 등수 ──────────────
    print("\n[7] 손패 평균 rank 구간별 평균 등수")
    print("-" * 50)
    buckets = [
        ("    ~5.0", lambda r: r["avg_rank"] <= 5.0),
        ("5.0 ~6.0", lambda r: 5.0 < r["avg_rank"] <= 6.0),
        ("6.0 ~7.0", lambda r: 6.0 < r["avg_rank"] <= 7.0),
        ("7.0 ~8.0", lambda r: 7.0 < r["avg_rank"] <= 8.0),
        ("8.0 ~9.0", lambda r: 8.0 < r["avg_rank"] <= 9.0),
        ("9.0~10.0", lambda r: 9.0 < r["avg_rank"] <= 10.0),
        ("10.0~   ", lambda r: r["avg_rank"] > 10.0),
    ]
    for label, pred in buckets:
        vals = [r["finish_order"] for r in records if pred(r)]
        if vals:
            print(
                f"  rank {label}  →  평균 {_avg(vals):.2f}등"
                f"  (n={len(vals):,})"
            )

    # ── 8. 1-2 피니시 발생률 ────────────────────────────
    print("\n[8] 1-2 피니시 발생률")
    print("-" * 50)
    one_two_count = sum(
        1 for r in records
        if r["player_id"] == 0 and r["one_two_finish"]
    )
    if total_rounds > 0:
        rate = one_two_count / total_rounds * 100
        print(f"  {one_two_count:,}/{total_rounds:,} 라운드  ({rate:.1f}%)")

    # ── 9. 폭탄 보유 시 vs 미보유 시 평균 등수 ─────────
    print("\n[9] 폭탄 보유 시 vs 미보유 시 평균 등수")
    print("-" * 50)
    no_bomb = [r["finish_order"] for r in records if not r["has_bomb"]]
    with_bomb = [r["finish_order"] for r in records if r["has_bomb"]]
    if no_bomb:
        print(
            f"  폭탄 미보유          →  평균 {_avg(no_bomb):.2f}등"
            f"  (n={len(no_bomb):,})"
        )
    if with_bomb:
        print(
            f"  폭탄 보유            →  평균 {_avg(with_bomb):.2f}등"
            f"  (n={len(with_bomb):,})"
        )
    for btype, label in [
        ("four_of_kind", "포카드"),
        ("straight_flush", "스트레이트 플러시"),
    ]:
        vals = [r["finish_order"] for r in records if r["bomb_type"] == btype]
        if vals:
            print(
                f"    └ {label:<18}  →  평균 {_avg(vals):.2f}등"
                f"  (n={len(vals):,})"
            )

    print("\n" + "=" * 60)


# ── CSV 저장 ───────────────────────────────────────────


def save_csv(records: list[dict], path: str = "results.csv") -> None:
    """레코드를 CSV로 저장한다."""
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)
    print(f"\nCSV 저장 완료: {path}  ({len(records):,} 행)")


# ── 메인 ───────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="티츄 4인 AI 자동 시뮬레이션",
    )
    parser.add_argument(
        "--games", type=int, default=1000,
        help="시뮬레이션할 게임 수 (기본: 1000)",
    )
    parser.add_argument(
        "--save-csv", action="store_true",
        help="raw 데이터를 results.csv로 저장",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="게임별 라운드 진행 출력 (기본: 억제)",
    )
    args = parser.parse_args()

    num_games = args.games
    all_records: list[dict] = []
    total_rounds = 0

    print(f"시뮬레이션 시작: {num_games:,}게임")
    print("-" * 40)

    for g in range(num_games):
        game = SimGame(game_id=g, verbose=args.verbose)

        if args.verbose:
            print(f"\n── Game {g + 1} ──")

        game.run()
        all_records.extend(game.records)
        total_rounds += game._round_id

        done = g + 1
        if done % 100 == 0 or done == num_games:
            pct = done / num_games * 100
            print(f"[{pct:5.1f}%] {done:,}/{num_games:,} 게임 완료")

    print(f"\n총 {total_rounds:,} 라운드, {len(all_records):,} 레코드 수집")
    print_stats(all_records)

    if args.save_csv:
        save_csv(all_records)


if __name__ == "__main__":
    main()
