# Plan

1. Add a boundary regression test that rejects SQLite URLs in
   runtime/customer/workflow unit tests.
2. Capture the RED failure before changing the fixtures.
3. Replace the runtime-lab and runtime-policy unit SQLite engines with
   `mysql8_session` or `mysql8_unittest_database`.
4. Run the migrated focused unit tests and MySQL8 boundary gate with explicit
   disposable MySQL8 URLs.
5. Update tasks and evidence, then commit the focused hardening slice.
