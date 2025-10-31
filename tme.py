period_map = {
    'day': timedelta(days=1),
    'week': timedelta(weeks=1),
    'month': timedelta(days=30),
    '6month': timedelta(days=180),
    'year': timedelta(days=365)
}
time_filter = f" AND time >= ?" if period in period_map else ""
params.append((datetime.now() - period_map.get(period, timedelta(days=7))).isoformat())
# 返回 logs 帶 time (ISO) 供前端排序