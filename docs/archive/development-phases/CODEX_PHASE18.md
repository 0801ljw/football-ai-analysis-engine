Implement Phase 18 for /Users/ljw/projects/worldcup-ai-content-engine, using the existing failing tests as the contract.

Context:
- Current tests: `tests/test_multi_user_auth.py` has new RED tests for Phase 18.
- Current failures expected: missing token_preview/quota in user payloads, missing admin update/reset endpoints, missing admin user management panel.
- Keep this project local/self-hosted; no payment integration, no new dependencies, no git required.
- Keep token security: never expose token_hash; only expose one-time plaintext token on create/reset responses; list/get users show token_preview only.

Required implementation:
1. app/auth.py
   - Store token preview (`wc_...last4` or equivalent) in users table for future list output.
   - Migrate existing DB by adding token_preview column if missing.
   - `create_user()` should return user object with token_preview, no token_hash.
   - `list_users()`/`get_user()` should include token_preview and per-user quota status.
   - Add methods:
     - update_user(user_id, role=None, plan=None, run_quota=None, active=None) -> {user}
     - reset_token(user_id) -> {user, token}
   - Updating active=False should make authenticate fail.
   - Reset token invalidates old token.
   - `summary()` should include users with quota status and no secrets.

2. app/schemas.py
   - Add UserUpdateRequest with optional role/plan/run_quota/active.

3. app/main.py
   - Add `PATCH /api/admin/users/{user_id}` admin-only.
   - Add `POST /api/admin/users/{user_id}/reset-token` admin-only.
   - Existing `GET /api/admin/users` returns enhanced summary.
   - Existing `POST /api/admin/users` response should include token once and enhanced user object.

4. app/templates/index.html
   - Add “Admin 用户管理” panel in advanced tools with:
     - button id `admin-users-button`
     - form id `admin-user-create-form`
     - fields username/role/plan/run_quota
     - output container id `admin-users-output`
     - explanatory copy: token only shown once on create/reset.

5. app/static/app.js
   - Wire admin users button and create form:
     - GET /api/admin/users with authHeaders
     - POST /api/admin/users
     - Render users table/list with username role plan run_quota used remaining active token_preview
     - Include reset/disable/enable buttons if easy; at minimum list/create must work and compile.
   - Use no external libs.

6. Docs if quick:
   - Update README/PRODUCT_PLAN to mention Phase 18 user management, token reset/disable, per-user quota.

Verification to run before final:
`.venv/bin/python -m pytest tests/test_multi_user_auth.py -q`
Then if passes, run full checks if time.

Do not change unrelated files.