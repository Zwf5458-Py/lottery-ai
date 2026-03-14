import sqlite3
from datetime import datetime

from modules.auth import USERS_DB_PATH


def _get_conn():
    return sqlite3.connect(USERS_DB_PATH)


def get_user_points(user_id: int) -> int:
    try:
        conn = _get_conn()
        row = conn.execute("SELECT points FROM users WHERE id=?", (user_id,)).fetchone()
        conn.close()
        return int(row[0]) if row and row[0] is not None else 0
    except Exception:
        return 0


def add_points(user_id: int, amount: int, reason: str, meta: str = '') -> dict:
    if amount <= 0:
        return {'success': False, 'error': '积分变动必须为正数'}
    try:
        conn = _get_conn()
        conn.execute("UPDATE users SET points = COALESCE(points, 0) + ? WHERE id=?", (amount, user_id))
        row = conn.execute("SELECT points FROM users WHERE id=?", (user_id,)).fetchone()
        balance = int(row[0]) if row and row[0] is not None else 0
        conn.execute(
            "INSERT INTO user_points_ledger (user_id, change_amount, balance, reason, meta) VALUES (?, ?, ?, ?, ?)",
            (user_id, amount, balance, reason, meta)
        )
        conn.commit()
        conn.close()
        return {'success': True, 'balance': balance}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def deduct_points(user_id: int, amount: int, reason: str, meta: str = '') -> dict:
    if amount <= 0:
        return {'success': False, 'error': '扣减积分必须为正数'}
    try:
        conn = _get_conn()
        # 原子扣减积分
        cursor = conn.execute(
            "UPDATE users SET points = points - ? WHERE id = ? AND points >= ?",
            (amount, user_id, amount)
        )
        
        if cursor.rowcount == 0:
            # 判断是用户不存在还是积分不足
            row = conn.execute("SELECT points FROM users WHERE id=?", (user_id,)).fetchone()
            conn.close()
            if not row:
                return {'success': False, 'error': '用户不存在'}
            return {'success': False, 'error': '积分不足', 'balance': int(row[0])}
            
        # 扣减成功，获取最新余额用于记录
        row = conn.execute("SELECT points FROM users WHERE id=?", (user_id,)).fetchone()
        new_balance = int(row[0]) if row else 0
        
        conn.execute(
            "INSERT INTO user_points_ledger (user_id, change_amount, balance, reason, meta) VALUES (?, ?, ?, ?, ?)",
            (user_id, -amount, new_balance, reason, meta)
        )
        conn.commit()
        conn.close()
        return {'success': True, 'balance': new_balance}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def record_recharge(user_id: int, amount: float, points_per_yuan: int = 10) -> dict:
    try:
        amount = float(amount)
        if amount <= 0:
            return {'success': False, 'error': '充值金额必须大于 0'}
        points = int(round(amount * points_per_yuan))
        conn = _get_conn()
        conn.execute(
            "INSERT INTO user_recharges (user_id, amount, points) VALUES (?, ?, ?)",
            (user_id, amount, points)
        )
        total_row = conn.execute("SELECT COUNT(1) FROM user_recharges WHERE user_id=?", (user_id,)).fetchone()
        recharge_count = int(total_row[0]) if total_row else 0
        conn.commit()
        conn.close()
        add_points(user_id, points, 'recharge', f'amount={amount}')
        return {'success': True, 'points': points, 'recharge_count': recharge_count}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def get_referrer_id(user_id: int):
    try:
        conn = _get_conn()
        row = conn.execute("SELECT referrer_id FROM users WHERE id=?", (user_id,)).fetchone()
        conn.close()
        return row[0] if row else None
    except Exception:
        return None


def mark_referral_reward(user_id: int, reward_type: str) -> bool:
    try:
        conn = _get_conn()
        if reward_type == 'recharge':
            conn.execute("UPDATE users SET reward_recharge_given=1 WHERE id=?", (user_id,))
        elif reward_type == 'vip':
            conn.execute("UPDATE users SET reward_vip_given=1 WHERE id=?", (user_id,))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def is_reward_given(user_id: int, reward_type: str) -> bool:
    try:
        conn = _get_conn()
        if reward_type == 'recharge':
            row = conn.execute("SELECT reward_recharge_given FROM users WHERE id=?", (user_id,)).fetchone()
        else:
            row = conn.execute("SELECT reward_vip_given FROM users WHERE id=?", (user_id,)).fetchone()
        conn.close()
        return bool(row[0]) if row else False
    except Exception:
        return False


def apply_referral_recharge_reward(user_id: int, amount: float, recharge_min: float, reward_points: int) -> dict:
    """被推荐用户首充达标后，给推荐人发放一次奖励"""
    try:
        amount = float(amount)
    except Exception:
        return {'success': False, 'reward_given': False, 'reason': 'amount_invalid'}

    if amount < recharge_min:
        return {'success': True, 'reward_given': False, 'reason': 'amount_below_min'}

    try:
        conn = _get_conn()
        total_row = conn.execute("SELECT COUNT(1) FROM user_recharges WHERE user_id=?", (user_id,)).fetchone()
        recharge_count = int(total_row[0]) if total_row else 0
        conn.close()
    except Exception:
        recharge_count = 0

    if recharge_count != 1:
        return {'success': True, 'reward_given': False, 'reason': 'not_first_recharge'}

    ref_id = get_referrer_id(user_id)
    if not ref_id:
        return {'success': True, 'reward_given': False, 'reason': 'no_referrer'}
    if is_reward_given(user_id, 'recharge'):
        return {'success': True, 'reward_given': False, 'reason': 'already_given'}

    add_res = add_points(ref_id, int(reward_points), 'share_reward_recharge', f'referred_user={user_id},amount={amount}')
    if not add_res.get('success'):
        return {'success': False, 'reward_given': False, 'reason': 'add_points_failed', 'error': add_res.get('error')}

    marked = mark_referral_reward(user_id, 'recharge')
    if not marked:
        return {'success': False, 'reward_given': False, 'reason': 'mark_failed'}

    return {
        'success': True,
        'reward_given': True,
        'reason': 'ok',
        'referrer_id': ref_id,
        'reward_points': int(reward_points),
        'referrer_balance': add_res.get('balance')
    }


def apply_referral_vip_reward(user_id: int, reward_points: int) -> dict:
    """被推荐用户开通 VIP 后，给推荐人发放一次奖励"""
    ref_id = get_referrer_id(user_id)
    if not ref_id:
        return {'success': True, 'reward_given': False, 'reason': 'no_referrer'}
    if is_reward_given(user_id, 'vip'):
        return {'success': True, 'reward_given': False, 'reason': 'already_given'}

    add_res = add_points(ref_id, int(reward_points), 'share_reward_vip', f'referred_user={user_id}')
    if not add_res.get('success'):
        return {'success': False, 'reward_given': False, 'reason': 'add_points_failed', 'error': add_res.get('error')}

    marked = mark_referral_reward(user_id, 'vip')
    if not marked:
        return {'success': False, 'reward_given': False, 'reason': 'mark_failed'}

    return {
        'success': True,
        'reward_given': True,
        'reason': 'ok',
        'referrer_id': ref_id,
        'reward_points': int(reward_points),
        'referrer_balance': add_res.get('balance')
    }


def calc_referral_reward_points(base_points: int, ratio: float, fallback_points: int) -> int:
    """按比例计算奖励积分，失败时回退到固定奖励积分。"""
    try:
        base = int(base_points)
        ratio_val = float(ratio)
        fixed = int(fallback_points)
    except Exception:
        return max(0, int(fallback_points or 0))

    if base <= 0:
        return max(0, fixed)
    if ratio_val <= 0:
        return max(0, fixed)

    computed = int(round(base * ratio_val))
    if computed <= 0:
        computed = 1
    return computed


def get_points_ledger(user_id: int, page: int = 1, page_size: int = 20) -> dict:
    try:
        page = max(1, int(page))
        page_size = max(1, min(100, int(page_size)))
        offset = (page - 1) * page_size

        conn = _get_conn()
        total_row = conn.execute(
            "SELECT COUNT(1) FROM user_points_ledger WHERE user_id=?",
            (user_id,)
        ).fetchone()
        total = int(total_row[0]) if total_row else 0

        rows = conn.execute(
            """
            SELECT id, change_amount, balance, reason, meta, created_at
            FROM user_points_ledger
            WHERE user_id=?
            ORDER BY id DESC
            LIMIT ? OFFSET ?
            """,
            (user_id, page_size, offset)
        ).fetchall()
        conn.close()

        items = []
        for r in rows:
            items.append({
                'id': int(r[0]),
                'change_amount': int(r[1]),
                'balance': int(r[2]),
                'reason': r[3] or '',
                'meta': r[4] or '',
                'created_at': r[5] or ''
            })

        return {
            'success': True,
            'items': items,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total': total,
                'total_pages': (total + page_size - 1) // page_size if total else 0
            }
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}


def get_recharge_history(user_id: int, page: int = 1, page_size: int = 20) -> dict:
    try:
        page = max(1, int(page))
        page_size = max(1, min(100, int(page_size)))
        offset = (page - 1) * page_size

        conn = _get_conn()
        total_row = conn.execute(
            "SELECT COUNT(1) FROM user_recharges WHERE user_id=?",
            (user_id,)
        ).fetchone()
        total = int(total_row[0]) if total_row else 0

        rows = conn.execute(
            """
            SELECT id, amount, points, created_at
            FROM user_recharges
            WHERE user_id=?
            ORDER BY id DESC
            LIMIT ? OFFSET ?
            """,
            (user_id, page_size, offset)
        ).fetchall()
        conn.close()

        items = []
        for r in rows:
            items.append({
                'id': int(r[0]),
                'amount': float(r[1]),
                'points': int(r[2]),
                'created_at': r[3] or ''
            })

        return {
            'success': True,
            'items': items,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total': total,
                'total_pages': (total + page_size - 1) // page_size if total else 0
            }
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}
