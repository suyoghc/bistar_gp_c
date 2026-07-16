"""M2cR milestone R2 infrastructure (hermetic; no scientific computation).

This subpackage implements the plan §8 R2 enumeration of
``docs/plan-post-d45-m2cr.md`` under the R1 contracts frozen by prereg
addendum v1.19 and ``docs/m2c_freeze/m2c_execution_record.schema_v1.json``.
Nothing here performs, authorizes, or schedules scientific computation: the
v2 gates are exercised only through synthetic and rigged oracles, the capture
driver only through fake payloads, and every future ``--execute`` requires
its own fresh explicit author authorization recorded in the committed
authorization ledger.

Frozen sources are imported, never modified: numerical constants come from
``bistar_gp.m2c_freeze`` and ``bistar_gp/profile_integration.py`` stays
byte-identical (ballot B13).
"""
