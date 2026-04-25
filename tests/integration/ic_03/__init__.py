"""IC-03 stage_artifact_emitted 集成测试.

Dev-δ L1-02/L2-02 · 项目生命周期 stage 各产物 emit IC-03 事件.

3 类 stage artifact:
- 4 件套 (chart/charter/plan/team) · L2-03 FourPiecesProducer
- PMP 9 计划 (integration/scope/schedule/cost/quality/resource/communication/risk/procurement) · L2-04
- TOGAF ADM (preliminary/phase_a..h · 9 phase) · L2-05

每条产出 → emit `L1-02:stage_artifact_emitted` 经 IC-09 落盘.
payload 字段(IC-03 contract):
- artifact_kind   · 产物类型(four_set/pmp/togaf 子集)
- pid             · PM-14 分片
- event_id        · 唯一标识
- hash            · sha256 内容哈希
"""
