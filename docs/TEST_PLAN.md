# Manual Test Plan: Authentication, Todo Management & Security Boundaries

## 1. Scope & Objective

- **Mục tiêu kiểm thử**: Xác thực chức năng toàn diện (Authentication, Todo CRUD, Authorization Boundary, Data Isolation, Caching Invalidation) và đảm bảo các lỗi bảo mật/logic đã được khắc phục hoàn toàn.
- **Phạm vi kiểm thử**:
  - Authentication & JWT Authorization (Access token expiration, tampered tokens, token type enforcement).
  - Todo Management CRUD & Data Integrity (Create, Read, Update partial/full, Delete, Toggle completion).
  - Cross-User Authorization & Multi-tenant Data Isolation.
  - Redis Caching & Cache Invalidation on Mutations.
  - UI State Synchronization & Logout Cache Cleanup.

## 2. Test Environment & Prerequisites

- **Base URL Backend**: `http://localhost:8000`
- **Base URL Frontend**: `http://localhost:3000`
- **Database**: PostgreSQL 16
- **Cache**: Redis 7
- **Pre-seeded Test Accounts**:
  - Account 1 (User A): `user_a@test.com` / `Password@123`
  - Account 2 (User B): `user_b@test.com` / `Password@123`

## 3. Test Cases Matrix

| TC ID | Module / Feature | Test Scenario | Preconditions | Test Steps | Expected Result | Priority / Severity | Status |
|---|---|---|---|---|---|---|---|
| **TC-01** | Auth | Đăng ký tài khoản thành công | Chưa có tài khoản | 1. Truy cập trang `/register`<br>2. Nhập email mới và password khớp với confirm password<br>3. Bấm "Create Account" | Tạo tài khoản thành công, trả về access/refresh token và chuyển hướng tới `/` | High / Blocker | Pass |
| **TC-02** | Auth | Đăng nhập thành công với thông tin hợp lệ | Tài khoản đã tồn tại | 1. Mở trang `/login`<br>2. Nhập email/password đúng<br>3. Bấm "Sign In" | Đăng nhập thành công, lưu token vào client và chuyển hướng tới Todo Dashboard | High / Blocker | Pass |
| **TC-03** | Auth | Đăng nhập thất bại với mật khẩu sai (Chống User Enumeration) | Tài khoản đã tồn tại | 1. Mở trang `/login`<br>2. Nhập email đúng, password sai<br>3. Bấm "Sign In" | Trả về 401 Unauthorized với thông báo lỗi chung, không làm lộ sự tồn tại của email | Medium / Security | Pass |
| **TC-04** | Auth - JWT Security | Từ chối Access Token đã hết hạn | Token đã hết thời gian khả dụng (`exp` trôi qua) | 1. Gửi request đến GET `/api/v1/auth/me` với Bearer token đã hết hạn | Server từ chối request với mã lỗi HTTP 401 Unauthorized | Critical / Security | Pass |
| **TC-05** | Auth - JWT Security | Từ chối Refresh Token dùng sai mục đích | Đã có refresh_token hợp lệ | 1. Sử dụng refresh_token làm Bearer Authorization header gọi GET `/api/v1/todos` | Backend kiểm tra `type=access` và trả về 401 Unauthorized | Critical / Security | Pass |
| **TC-06** | Auth - JWT Security | Từ chối Token bị thay đổi chữ ký (Tampered Token) | Đã có access_token | 1. Sửa đổi chuỗi signature của token<br>2. Gọi API protected | Server phát hiện signature invalid và từ chối 401 Unauthorized | Critical / Security | Pass |
| **TC-07** | Todo CRUD | Tạo Todo mới | User A đã đăng nhập | 1. Bấm nút "Add Todo"<br>2. Nhập Title & Description<br>3. Bấm "Create" | Todo mới hiển thị ở đầu danh sách UI với `completed = false` | High / Major | Pass |
| **TC-08** | Todo Logic | Đổi trạng thái completed từ true về false | Todo đang có `completed = true` | 1. Bấm bỏ chọn checkbox hoàn thành<br>2. F5 làm mới trang | Todo giữ nguyên trạng thái `completed = false` (không bị lỗi giữ nguyên true) | High / Major | Pass |
| **TC-09** | Todo Logic | Cập nhật một phần (Partial Update - chỉ sửa Title) | Todo có Title và Description | 1. Mở dialog edit todo<br>2. Chỉ thay đổi Title, giữ nguyên Description<br>3. Bấm Save | Title được cập nhật mới, Description cũ KHÔNG bị xoá/null | High / Major | Pass |
| **TC-10** | Authorization Boundary | User A không thể đọc/xem Todo của User B | User A & B đều đã đăng ký | 1. User B tạo Todo ID `X`<br>2. User A dùng API GET `/api/v1/todos/X` | Trả về HTTP 404 Not Found (hoặc 403 Forbidden), User A không thấy dữ liệu của User B | Critical / Security | Pass |
| **TC-11** | Authorization Boundary | User A không thể chỉnh sửa Todo của User B | User A & B đều đã đăng ký | 1. User B tạo Todo ID `X`<br>2. User A gửi request PUT `/api/v1/todos/X` | Server ngăn chặn update và trả về HTTP 404/403 | Critical / Security | Pass |
| **TC-12** | Authorization Boundary | User A không thể xoá Todo của User B | User A & B đều đã đăng ký | 1. User B tạo Todo ID `X`<br>2. User A gửi request DELETE `/api/v1/todos/X` | Server ngăn chặn delete và trả về HTTP 404/403 | Critical / Security | Pass |
| **TC-13** | Redis Cache | Phân lập Redis Cache giữa các User | User A & B đều có Todos | 1. User A gọi GET `/api/v1/todos` (cache được lưu)<br>2. User B gọi GET `/api/v1/todos` | User B nhận danh sách của riêng User B, không nhận nhầm cache của User A | Critical / Security | Pass |
| **TC-14** | Redis Cache | Xoá Cache (Invalidation) khi tạo Todo mới | Dữ liệu danh sách đã được cache trong Redis | 1. Gọi GET `/api/v1/todos`<br>2. Tạo Todo mới<br>3. Gọi lại GET `/api/v1/todos` | Trả về danh sách mới chứa Todo vừa tạo, cache cũ đã bị xóa | High / Major | Pass |
| **TC-15** | Redis Cache | Xoá Cache khi Cập nhật hoặc Xoá Todo | Dữ liệu danh sách đã được cache | 1. Cập nhật/Xoá một Todo<br>2. Gọi GET `/api/v1/todos` | Dữ liệu danh sách lập tức phản ánh thay đổi mới nhất | High / Major | Pass |
| **TC-16** | Frontend Security | Xoá toàn bộ Cache client khi Đăng xuất (Logout) | User A đang logged in | 1. User A xem danh sách Todos<br>2. Bấm "Logout"<br>3. User B đăng nhập trên cùng trình duyệt | React Query cache của User A đã được clear sạch, User B không thấy dữ liệu cũ | High / Major | Pass |

## 4. Defect Tracking & Known Limitations

- Tất cả 16 test cases trong ma trận kiểm thử đều đạt (**PASS**).
- Hệ thống backend đã triển khai kiểm tra quyền sở hữu (ownership authorization) tại mọi API endpoint mutation và query.
- Client frontend tự động thu hồi dữ liệu nhạy cảm khỏi bộ nhớ cache khi phiên làm việc kết thúc (Logout / Token expiry).
