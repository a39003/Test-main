# Bug Hunting Report

This report records the findings before production code is changed. Regression
tests that reproduce the issues are in `backend/tests/test_auth.py` and
`backend/tests/test_todos.py`.

| # | Location | Severity | Problem | Proposed fix |
|---|---|---|---|---|
| 1 | `backend/app/core/security.py:49-57` (`verify_token`) | Critical | JWT expiration verification is disabled, so expired tokens remain valid. | Enable the library's `exp` verification and reject expired tokens. |
| 2 | `backend/app/api/deps.py:16-51` (`get_current_user`) | Critical | The dependency does not require `type=access`; a refresh token can authenticate protected endpoints. | Require an access-token type in the authentication dependency. |
| 3 | `backend/app/api/v1/todos.py:88-102` (`get_todo`) | Critical | A user can read another user's todo by UUID because ownership is not checked. | Fetch by both todo ID and current user ID; return 404 when absent. |
| 4 | `backend/app/api/v1/todos.py:105-134` (`update_existing_todo`) | Critical | A user can modify another user's todo by UUID. | Enforce ownership in the database query before updating. |
| 5 | `backend/app/api/v1/todos.py:137-154` (`delete_existing_todo`) | Critical | A user can delete another user's todo by UUID. | Enforce ownership in the database query before deleting. |
| 6 | `backend/app/api/v1/todos.py:37` (`list_todos`) | Critical | All users and pagination variants share `todos:list`, allowing cross-user data leakage and incorrect pages. | Include user ID, page and size in the cache key. |
| 7 | `backend/app/api/v1/todos.py:77-154` (todo mutations) | High | Create, update and delete do not invalidate cached todo lists, so stale data can be served for five minutes. | Invalidate all affected list-cache keys after a successful mutation. |
| 8 | `backend/app/api/v1/todos.py:123-124` (`update_existing_todo`) | High | `if todo_data.completed` ignores `False`, preventing a completed todo from being made active. | Test `is not None`, or apply `model_dump(exclude_unset=True)`. |
| 9 | `backend/app/api/v1/todos.py:121-130` (`update_existing_todo`) | High | `model_dump()` includes omitted fields as `None`; changing only the title erases the description. | Use `model_dump(exclude_unset=True)` and update only supplied fields. |
| 10 | `frontend/src/features/auth/api/auth.ts:46-55` (`useLogout`) | High | Logout removes tokens but retains user-scoped React Query data, risking stale data across accounts. | Clear/remove user-scoped queries on logout and on forced 401 logout. |
| 11 | `frontend/src/features/todos/api/todos.ts:35-44` (`useTodos`) | Medium | The query key omits page and size, so different pages collide in the client cache. | Use a key such as `["todos", { page, size }]`. |
| 12 | `frontend/src/features/todos/api/todos.ts:76-100` (`useUpdateTodo`) | Medium | The optimistic update snapshots old data but does not restore it on failure. | Restore the snapshot from mutation context in `onError`. |

## Reproduction command

```bash
cd backend
pytest tests/test_auth.py tests/test_todos.py -v
```

The new regression tests are intentionally expected to fail against the
original implementation. They should pass only after the corresponding fixes
are applied.
