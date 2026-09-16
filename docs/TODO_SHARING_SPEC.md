# Technical Specification: Todo Sharing (Chia Sẻ Danh Sách Công Việc)

> **Tác giả**: Pham Duc Anh  
> **Ngày tạo**: 2026-09-16  
> **Trạng thái**: Draft / In Review  
> **Tài liệu tham khảo**: `templates/SPEC_TEMPLATE.md`

---

## 1. Overview & Objective (Tổng Quan & Mục Tiêu)

### 1.1 Feature Summary
Tính năng **Todo Sharing** cho phép người dùng (Owner) chia sẻ danh sách công việc hoặc từng đầu việc của mình cho người dùng khác trong hệ thống theo email, với hai mức phân quyền linh hoạt:
- **Viewer (Chỉ xem)**: Người được chia sẻ chỉ có thể xem nội dung, không thể chỉnh sửa hay thay đổi trạng thái.
- **Editor (Chỉnh sửa)**: Người được chia sẻ có thể xem, đánh dấu hoàn thành/chưa hoàn thành và cập nhật nội dung công việc.

Owner có toàn quyền quản lý danh sách người được chia sẻ và có thể thu hồi quyền (Revoke) bất cứ lúc nào.

### 1.2 Problem Statement
Hiện tại ứng dụng Todo là dạng đơn người dùng (single-tenant per user data). Người dùng khi làm việc nhóm, phân công việc nhà hoặc phối hợp dự án nhỏ không có cách nào chia sẻ đầu việc cho nhau mà không phải chia sẻ thông tin đăng nhập tài khoản. Việc bổ sung tính năng chia sẻ có phân quyền sẽ giải quyết nhu cầu cộng tác cơ bản mà vẫn đảm bảo tính bảo mật và toàn vẹn dữ liệu.

### 1.3 Target Audience & Roles
1. **Owner (Chủ sở hữu)**: Người tạo ra Todo, có toàn quyền (Read, Update, Delete, Share, Revoke, Transfer ownership).
2. **Editor (Người cộng tác có quyền sửa)**: Được Owner cấp quyền, có thể Read và Update Todo. Không có quyền xoá Todo và không được chia sẻ tiếp cho người khác.
3. **Viewer (Người xem)**: Được Owner cấp quyền, chỉ có quyền Read Todo. Không được sửa hay xoá.

---

## 2. User Stories & Acceptance Criteria (Kịch Bản Người Dùng)

### User Story 1: Owner chia sẻ Todo cho người dùng khác
- **As an** Owner của một Todo,
- **I want to** nhập email của người dùng khác và chọn quyền (`viewer` hoặc `editor`),
- **So that** họ có thể xem hoặc cùng tôi hoàn thành công việc.
- **Acceptance Criteria**:
  - [x] Hệ thống kiểm tra email có tồn tại trên hệ thống hay không. Nếu không, trả về lỗi `404 Not Found: User not found`.
  - [x] Không cho phép Owner tự chia sẻ Todo cho chính mình (trả về `400 Bad Request: Cannot share todo with yourself`).
  - [x] Nếu Todo đã từng được chia sẻ cho email đó trước đây, hệ thống cập nhật lại quyền mới (`permission`) thay vì báo lỗi trùng lặp.
  - [x] Sau khi chia sẻ thành công, người được chia sẻ sẽ thấy Todo này xuất hiện trong danh sách công việc được chia sẻ của họ.

### User Story 2: Collaborator xem danh sách công việc được chia sẻ với mình
- **As a** Collaborator (Viewer hoặc Editor),
- **I want to** truy cập tab hoặc danh sách "Shared with me",
- **So that** tôi có thể theo dõi các công việc người khác đã giao hoặc chia sẻ cho tôi.
- **Acceptance Criteria**:
  - [x] API trả về danh sách các Todo kèm theo thông tin quyền hạn của tôi (`viewer` hoặc `editor`) và email của người chia sẻ (Owner).
  - [x] Danh sách này được phân trang (`page`, `size`) tương tự như danh sách Todo cá nhân.
  - [x] Người dùng không thể thấy các Todo mà họ đã bị thu hồi quyền truy cập.

### User Story 3: Editor cập nhật trạng thái hoặc nội dung Todo
- **As an** Editor,
- **I want to** đánh dấu hoàn thành checkbox hoặc chỉnh sửa tiêu đề/mô tả của Todo được chia sẻ,
- **So that** công việc được cập nhật tiến độ kịp thời.
- **Acceptance Criteria**:
  - [x] Editor có thể gọi API `PUT /api/v1/todos/{id}` để cập nhật trạng thái `completed`, `title`, `description`.
  - [x] Nếu Viewer cố tình gửi request `PUT`, hệ thống chặn lại và trả về lỗi `403 Forbidden: You do not have permission to edit this todo`.
  - [x] Cả Owner và các Collaborators khác khi tải lại danh sách sẽ thấy ngay trạng thái mới nhất (cache bị xoá và cập nhật lại).
  - [x] Editor **không** được phép gọi API `DELETE /api/v1/todos/{id}` (chỉ Owner mới có quyền xoá Todo).

### User Story 4: Owner xem danh sách người được chia sẻ và thu hồi quyền
- **As an** Owner,
- **I want to** mở bảng quản lý chia sẻ của một Todo để xem ai đang có quyền và có nút "Revoke",
- **So that** tôi có thể ngừng chia sẻ khi công việc đã xong hoặc không còn phù hợp.
- **Acceptance Criteria**:
  - [x] Chỉ Owner mới có quyền gọi API lấy danh sách shares (`GET /api/v1/todos/{id}/shares`) và thu hồi (`DELETE /api/v1/todos/{id}/shares/{user_id}`).
  - [x] Khi thu hồi thành công, quyền của Collaborator bị xoá ngay lập tức khỏi database và cache Redis của Collaborator bị xóa.
  - [x] Nếu Collaborator đang mở trang và cố tình gửi request chỉnh sửa sau khi bị thu hồi, họ sẽ nhận mã lỗi `403 Forbidden` hoặc `404 Not Found`.

---

## 3. Scope (Phạm Vi Tính Năng)

### 3.1 In-Scope (Bắt buộc trong phiên bản này)
- Tạo bảng liên kết `todo_shares` lưu quan hệ giữa Todo và User được chia sẻ.
- Chia sẻ theo từng Todo cụ thể thông qua địa chỉ email.
- 2 mức phân quyền: `viewer` (chỉ đọc) và `editor` (đọc & sửa).
- Quản trị viên Todo (Owner) có quyền xem danh sách chia sẻ, đổi quyền và thu hồi quyền.
- Tự động xóa cache Redis liên quan khi quyền hạn hoặc dữ liệu Todo thay đổi.

### 3.2 Out-of-Scope (Để dành cho phiên bản tiếp theo)
- Chia sẻ cả folder/dự án lớn (hiện tại tập trung vào chia sẻ cấp Todo).
- Public Link Sharing (chia sẻ link ẩn danh xem không cần tài khoản).
- Phân quyền lồng (Resharing): Collaborator không được quyền mời thêm người khác.
- Lịch sử thay đổi chi tiết (Activity Log: ai sửa dòng nào vào mấy giờ).
- Thông báo thời gian thực (WebSockets / Push Notifications).

---

## 4. Database Design (Thiết Kế Cơ Sở Dữ Liệu)

### 4.1 Bảng mới: `todo_shares`

| Tên Cột | Kiểu Dữ Liệu | Ràng Buộc (Constraints) | Mô Tả |
|---|---|---|---|
| `id` | `UUID` | Primary Key, Default `gen_random_uuid()` | Định danh bản ghi chia sẻ |
| `todo_id` | `UUID` | Foreign Key `todos(id)` ON DELETE CASCADE, NOT NULL | Todo được chia sẻ |
| `shared_with_user_id` | `UUID` | Foreign Key `users(id)` ON DELETE CASCADE, NOT NULL | Người dùng được cấp quyền |
| `permission` | `VARCHAR(20)` | NOT NULL, Check in (`'viewer'`, `'editor'`) | Mức độ phân quyền |
| `created_at` | `TIMESTAMPTZ` | NOT NULL, Default `CURRENT_TIMESTAMP` | Thời gian cấp quyền |
| `updated_at` | `TIMESTAMPTZ` | NOT NULL, Default `CURRENT_TIMESTAMP` | Thời gian cập nhật quyền |

### 4.2 Constraints & Indexes

```sql
-- 1. Đảm bảo mỗi Todo chỉ chia sẻ cho 1 user tối đa 1 lần (tránh trùng lặp)
ALTER TABLE todo_shares 
ADD CONSTRAINT uq_todo_user_share UNIQUE (todo_id, shared_with_user_id);

-- 2. Đảm bảo giá trị permission chỉ hợp lệ là viewer hoặc editor
ALTER TABLE todo_shares 
ADD CONSTRAINT ck_todo_share_permission CHECK (permission IN ('viewer', 'editor'));

-- 3. Index phục vụ truy vấn: Lấy tất cả Todo được chia sẻ cho một User
CREATE INDEX ix_todo_shares_user_id ON todo_shares (shared_with_user_id);

-- 4. Index phục vụ truy vấn: Lấy tất cả người đang được chia sẻ Todo này
CREATE INDEX ix_todo_shares_todo_id ON todo_shares (todo_id);
```

### 4.3 Cascade Delete Behavior
- Khi **Todo bị xoá** (bởi Owner): Tất cả các bản ghi chia sẻ liên quan trong `todo_shares` sẽ tự động bị xoá nhờ `ON DELETE CASCADE`.
- Khi **Tài khoản người dùng bị xoá**: Các bản ghi chia sẻ liên quan đến user đó trong `todo_shares` cũng tự động bị dọn dẹp.

---

## 5. API Contracts & Endpoints (Đặc Tả API)

Tất cả các endpoint đều yêu cầu Authorization Header: `Bearer <access_token>`.

### 5.1 POST `/api/v1/todos/{todo_id}/shares` (Cấp quyền chia sẻ)
Chia sẻ Todo cho một người dùng qua email.

- **Request Body**:
  ```json
  {
    "email": "collab@example.com",
    "permission": "editor" // hoặc "viewer"
  }
  ```
- **Responses**:
  - `201 Created`: Cấp quyền thành công.
    ```json
    {
      "id": "c1f72a6b-9c3f-4e0d-b4f7-873d9d300123",
      "todo_id": "8a31e84f-e221-4f11-9a72-6bbbc9048a12",
      "shared_with_user_id": "52f9b177-3310-4822-83bb-92cc0b112233",
      "shared_with_email": "collab@example.com",
      "permission": "editor",
      "created_at": "2026-09-16T10:00:00Z"
    }
    ```
  - `400 Bad Request`: Tự chia sẻ cho bản thân (`"Cannot share todo with yourself"`).
  - `403 Forbidden`: Người gửi request không phải là Owner của Todo.
  - `404 Not Found`: Không tìm thấy Todo hoặc không tìm thấy người dùng có email này.

### 5.2 GET `/api/v1/todos/{todo_id}/shares` (Xem danh sách người được chia sẻ)
Chỉ Owner mới có thể gọi API này để xem ai đang có quyền vào Todo của mình.

- **Responses**:
  - `200 OK`:
    ```json
    {
      "items": [
        {
          "id": "c1f72a6b-9c3f-4e0d-b4f7-873d9d300123",
          "shared_with_user_id": "52f9b177-3310-4822-83bb-92cc0b112233",
          "email": "collab@example.com",
          "permission": "editor",
          "created_at": "2026-09-16T10:00:00Z"
        }
      ],
      "total": 1
    }
    ```
  - `403 Forbidden`: Người gọi không phải Owner.

### 5.3 DELETE `/api/v1/todos/{todo_id}/shares/{user_id}` (Thu hồi quyền chia sẻ)
Owner thu hồi quyền của một người dùng.

- **Responses**:
  - `204 No Content`: Thu hồi thành công.
  - `403 Forbidden`: Người gọi không phải Owner.
  - `404 Not Found`: Bản ghi chia sẻ không tồn tại.

### 5.4 GET `/api/v1/todos/shared` (Danh sách Todo người khác chia sẻ cho tôi)
Lấy danh sách các Todo mà tài khoản hiện tại được mời làm Viewer hoặc Editor.

- **Query Parameters**: `page=1`, `size=20`.
- **Responses**:
  - `200 OK`:
    ```json
    {
      "items": [
        {
          "id": "8a31e84f-e221-4f11-9a72-6bbbc9048a12",
          "title": "Kế hoạch tuần",
          "description": "Chi tiết công việc chung",
          "completed": false,
          "owner_email": "owner@example.com",
          "my_permission": "editor",
          "created_at": "2026-09-16T09:00:00Z",
          "updated_at": "2026-09-16T09:30:00Z"
        }
      ],
      "total": 1,
      "page": 1,
      "size": 20
    }
    ```

---

## 6. Business Logic & Security Considerations (Quy Tắc Nghiệp Vụ & Bảo Mật)

### 6.1 Ma Trận Phân Quyền (Permission Matrix)

| Thao Tác | Owner | Editor | Viewer | Người dùng khác (Unshared) |
|---|:---:|:---:|:---:|:---:|
| Xem nội dung Todo |  Cho phép |  Cho phép |  Cho phép | ❌ Chặn (404/403) |
| Đổi trạng thái (`completed`) |  Cho phép |  Cho phép | ❌ Chặn (403) | ❌ Chặn (404/403) |
| Cập nhật Title / Description |  Cho phép |  Cho phép | ❌ Chặn (403) | ❌ Chặn (404/403) |
| Xoá Todo |  Cho phép | ❌ Chặn (403) | ❌ Chặn (403) | ❌ Chặn (404/403) |
| Mời người khác / Đổi quyền |  Cho phép | ❌ Chặn (403) | ❌ Chặn (403) | ❌ Chặn (404/403) |
| Thu hồi quyền (Revoke) |  Cho phép | ❌ Chặn (403) | ❌ Chặn (403) | ❌ Chặn (404/403) |

### 6.2 Các Trường Hợp Biên & Ngoại Lệ (Edge Cases)
1. **Tự chia sẻ cho chính mình**:
   - *Tình huống*: User nhập chính email của mình để chia sẻ.
   - *Xử lý*: Kiểm tra `if target_user.id == current_user.id:` $\rightarrow$ Ném lỗi `HTTP 400: Cannot share with yourself`.
2. **Mời trùng lặp hoặc cập nhật quyền (Duplicate Invites)**:
   - *Tình huống*: Owner đã chia sẻ Todo A cho User B là `viewer`, sau đó lại gửi request chia sẻ tiếp thành `editor`.
   - *Xử lý*: Dùng câu lệnh `UPSERT` (hoặc `INSERT ... ON CONFLICT (todo_id, shared_with_user_id) DO UPDATE SET permission = EXCLUDED.permission`). Thao tác này sẽ cập nhật quyền hạn mới mà không sinh bản ghi thừa và không ném lỗi 500.
3. **Cập nhật đồng thời (Concurrent Updates)**:
   - *Tình huống*: Cả Owner và Editor cùng gửi request cập nhật Todo vào cùng một mili-giây.
   - *Xử lý*: Sử dụng transaction database và cập nhật theo `updated_at`. Phiên bản update sau cùng sẽ được ghi nhận; kết hợp gọi xóa cache lập tức để người còn lại nhận thông tin mới khi refresh.
4. **Thu hồi quyền khi Collaborator đang thao tác**:
   - *Tình huống*: Owner thu hồi quyền trong khi Editor đang mở form sửa Todo trên trình duyệt.
   - *Xử lý*: Khi Editor bấm Lưu, backend kiểm tra lại quyền trong database tại thời điểm đó. Nếu không còn quyền, ngay lập tức trả về `403 Forbidden: Permission revoked` và frontend sẽ điều hướng người dùng ra màn hình chính kèm thông báo lỗi.

---

## 7. Caching & Invalidation Strategy (Chiến Lược Cache Redis)

### 7.1 Cấu Trúc Cache Key
- Danh sách todo cá nhân của user: `todos:list:{user_id}`
- Danh sách todo được chia sẻ với user: `todos:shared:{user_id}`
- Chi tiết todo: `todos:detail:{todo_id}`

### 7.2 Quy Tắc Xoá Cache (Invalidation Rules)
1. **Khi Owner chia sẻ Todo**:
   - Xoá cache `todos:shared:{collaborator_id}` để collaborator thấy Todo mới ngay trong danh sách được chia sẻ.
2. **Khi Owner thu hồi quyền**:
   - Xoá cache `todos:shared:{collaborator_id}` để todo lập tức biến mất khỏi danh sách của người bị thu hồi.
3. **Khi Owner hoặc Editor cập nhật Todo**:
   - Xoá cache `todos:detail:{todo_id}`.
   - Xoá cache danh sách của Owner (`todos:list:{owner_id}`).
   - Truy vấn danh sách các collaborators của Todo đó và xoá cache `todos:shared:{collab_id}` của từng người.
4. **Khi Owner xoá Todo**:
   - Xoá cache danh sách của Owner và toàn bộ cache danh sách của các collaborators liên quan.

---

## 8. Kế Hoạch Triển Khai Trong Tương Lai (Next Steps)
1. Tạo Alembic Migration cho bảng `todo_shares`.
2. Viết Pydantic schemas cho request/response của tính năng chia sẻ.
3. Viết helper kiểm tra quyền truy cập (`check_todo_access(user_id, todo_id, required_permission)`).
4. Thêm các route endpoints mới vào router FastAPI.
5. Viết unit test và tích hợp giao diện frontend.
