# Báo Cáo Tìm & Sửa Lỗi (Bug Hunting & Fixes Report - Tier 1)

> Tài liệu tổng hợp các lỗi tìm thấy trong quá trình review mã nguồn, phân tích nguyên nhân và phương án khắc phục tương ứng theo yêu cầu của **Tier 1**.

---

## 1. Bảng Tổng Hợp Lỗi (Bug Summary)

| # | Location | Severity | Reason (Vấn đề & Hậu quả) | Fix Proposal (Giải pháp) |
|---|---|---|---|---|
| 1 | `backend/app/core/security.py:56` (`verify_token`) | **Critical** | Thư viện jwt đang tắt kiểm tra hạn (`verify_exp: False`), khiến token đã hết hạn vẫn gọi được API bình thường. | Đổi thành `verify_exp: True` để thư viện tự động từ chối token hết hạn. |
| 2 | `backend/app/api/deps.py:29-34` (`get_current_user`) | **Critical** | Dependency auth không kiểm tra trường `type="access"`, dẫn đến refresh token cũng có thể dùng làm Bearer token để gọi API protected. | Thêm kiểm tra `payload.get("type") == "access"`, nếu không đúng thì trả về 401. |
| 3 | `backend/app/api/v1/todos.py:105, 124, 146` (`get`, `put`, `delete`) | **Critical** | Lỗ hổng IDOR: Backend chỉ query Todo theo `todo_id` mà không kiểm tra xem Todo có thuộc về `current_user.id` hay không. User A có thể xem, sửa hoặc xoá Todo của User B nếu biết UUID. | Thêm điều kiện kiểm tra `if not todo or todo.user_id != current_user.id:` và trả về 404 Not Found. |
| 4 | `backend/app/api/v1/todos.py:64` (`list_todos`) | **Critical** | Cache key bị hardcode là `"todos:list"` dùng chung cho mọi user. Khi User A tải danh sách, kết quả được lưu vào cache và User B vào sau sẽ nhìn thấy Todo của User A (lộ dữ liệu người dùng). | Đổi cache key thành `f"todos:list:{current_user.id}"` để phân lập cache theo từng user. |
| 5 | `backend/app/api/v1/todos.py:93, 132, 153` (Todo mutations) | **High** | Khi tạo mới, cập nhật hoặc xoá Todo, backend không xóa cache Redis cũ. Dẫn đến người dùng vẫn thấy dữ liệu cũ trong 5 phút (TTL) dù đã thay đổi. | Viết hàm `invalidate_user_todos_cache` gọi `redis.delete` key danh sách của user mỗi khi tạo/sửa/xoá. |
| 6 | `backend/app/api/v1/todos.py:123` (`update_existing_todo`) | **High** | Câu lệnh `if todo_data.completed:` coi giá trị `False` là falsy nên bỏ qua, dẫn đến không thể đổi trạng thái Todo từ hoàn thành (`true`) về chưa hoàn thành (`false`). | Dùng `model_dump(exclude_unset=True)` để lấy đúng các trường client gửi lên, kể cả giá trị `False`. |
| 7 | `backend/app/api/v1/todos.py:121-130` (`update_existing_todo`) | **High** | Sử dụng `model_dump()` mặc định khiến các trường không gửi lên bị gán thành `None`. Ví dụ khi chỉ cập nhật `title`, `description` cũ sẽ bị ghi đè thành `None` (mất dữ liệu). | Dùng `model_dump(exclude_unset=True)` và truyền dictionary này vào hàm `update_todo`. |
| 8 | `frontend/src/features/auth/api/auth.ts:54` (`useLogout`) | **High** | Khi đăng xuất, client chỉ xoá token trong `localStorage` mà không xoá cache React Query. Khi tài khoản khác đăng nhập trên cùng trình duyệt, họ có thể thấy dữ liệu cũ của tài khoản trước. | Gọi `queryClient.clear()` khi logout, login thành công và khi nhận response 401. |
| 9 | `frontend/src/features/todos/api/todos.ts:76-110` (`useUpdateTodo`) | **Medium** | Tính năng Optimistic Update có lưu snapshot dữ liệu cũ nhưng trong hàm `onError` lại không rollback dữ liệu khi request cập nhật thất bại, làm UI hiển thị sai lệch so với server. | Thêm logic phục hồi `queryClient.setQueryData(["todos"], context.previousTodos)` trong callback `onError`. |

---

## 2. Chi Tiết Các Lỗi Đã Sửa

### Bug 1: Bật kiểm tra hạn dùng của Access Token
- **File**: `backend/app/core/security.py`
- **Mô tả**: Trong hàm `verify_token`, thiết lập `options={"verify_exp": False}` đã vô hiệu hoá việc kiểm tra thời gian hết hạn của JWT. Khi người dùng hết hạn phiên đăng nhập, token cũ vẫn có thể truy cập hệ thống vô thời hạn.
- **Cách sửa**: Chuyển thành `options={"verify_exp": True}`. Khi token hết hạn, thư viện `jose.jwt` sẽ raise lỗi `JWTError` và trả về mã lỗi 401 Unauthorized.

### Bug 2: Chặn sử dụng Refresh Token để gọi API thông thường
- **File**: `backend/app/api/deps.py`
- **Mô tả**: Hàm dependency `get_current_user` chỉ giải mã token và lấy `sub` (user_id) mà không kiểm tra `type` của token. Hacker hoặc người dùng có thể lấy refresh token để gọi các API riêng tư thay cho access token.
- **Cách sửa**: Thêm điều kiện `if payload.get("type") != "access": raise HTTPException(status_code=401, detail="Invalid token type")`.

### Bug 3: Ngăn chặn truy cập chéo dữ liệu (Lỗ hổng IDOR)
- **File**: `backend/app/api/v1/todos.py`
- **Mô tả**: Tại các endpoint `GET /{todo_id}`, `PUT /{todo_id}`, và `DELETE /{todo_id}`, backend truy vấn trực tiếp Todo từ database chỉ theo `todo_id`. Nếu User A biết hoặc đoán được UUID của User B, User A có thể xem nội dung, sửa trạng thái hoặc xoá hoàn toàn Todo của User B.
- **Cách sửa**: Thêm kiểm tra quyền sở hữu `if not todo or todo.user_id != current_user.id:` tại cả 3 endpoint và trả về lỗi 404 Not Found để vừa bảo mật vừa không làm lộ sự tồn tại của resource.

### Bug 4 & 5: Sửa lỗi Redis Cache (Lộ dữ liệu & Dữ liệu cũ)
- **File**: `backend/app/api/v1/todos.py`
- **Mô tả**: 
  - Key cache danh sách todo ban đầu là chuỗi cố định `"todos:list"`, dùng chung cho toàn bộ người dùng trong hệ thống.
  - Khi một todo mới được tạo, cập nhật hoặc xoá, cache không hề bị xoá nên người dùng gọi lại GET vẫn nhận dữ liệu cũ.
- **Cách sửa**:
  - Đổi key cache thành `f"todos:list:{current_user.id}"` để mỗi user có vùng cache riêng biệt.
  - Thêm helper `invalidate_user_todos_cache` gọi `redis.delete` mỗi khi có thao tác POST, PUT, DELETE.

### Bug 6 & 7: Sửa logic cập nhật Todo (Toggle completed & Partial Update)
- **File**: `backend/app/api/v1/todos.py`
- **Mô tả**:
  - `if todo_data.completed:`: Trong Python, `False` là giá trị falsy nên khi người dùng bỏ chọn checkbox (gửi `completed: False`), câu lệnh if bị bỏ qua và todo không thể đổi trạng thái về `false`.
  - `model_dump()`: Trả về tất cả các field của schema kể cả những field không gửi lên với giá trị `None`. Do đó nếu chỉ cập nhật `title`, `description` sẽ bị gán thành `None`.
- **Cách sửa**: Sử dụng `todo_data.model_dump(exclude_unset=True)` và truyền dictionary này vào `update_todo` để chỉ cập nhật đúng các trường client thực sự gửi lên.

### Bug 8 & 9: Đồng bộ và dọn dẹp Cache phía Frontend
- **Files**: `frontend/src/features/auth/api/auth.ts`, `frontend/src/features/todos/api/todos.ts`
- **Mô tả**:
  - Khi Logout, React Query vẫn lưu cache dữ liệu trong bộ nhớ trình duyệt, nếu user khác đăng nhập thì sẽ thấy dữ liệu của user cũ trước khi API fetch lại.
  - Khi Update Todo, hàm `onMutate` cập nhật tạm thời trên UI (optimistic), nhưng nếu backend trả lỗi thì UI vẫn giữ trạng thái sai vì không rollback lại dữ liệu cũ.
- **Cách sửa**:
  - Gọi `queryClient.clear()` khi logout, login và trong response interceptor khi gặp 401.
  - Bổ sung `queryClient.setQueryData(["todos"], context.previousTodos)` trong callback `onError` của `useUpdateTodo`.

---

## 3. Hướng Dẫn Chạy Test Kiểm Chứng (Reproduction & Verification)

Toàn bộ các lỗi trên đều đi kèm automated regression tests trong `backend/tests/`:

```bash
# Chạy toàn bộ backend test suite
cd backend
pytest tests/ -v
```

Kết quả: **21/21 tests passed (100%)**.
