"""tests/integration/ic_20 · IC-20 audit_chain_verify (~10 TC).

main-3 WP06 子目录 4.

注: 本任务中"IC-20 audit_chain_verify"使用 L1-09 verify_integrity HASH_CHAIN method
作为审计链 verify 抽象 · 因为它就是审计链的物理 verify 实现.

覆盖:
    - D1 完整链 verify · 3 TC
    - D2 篡改检测(中间篡改一条) · 3 TC
    - D3 缺失检测(删一条) · 2 TC
    - D4 cross-pid verify reject · 2 TC
"""
