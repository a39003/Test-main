# Báo Cáo Hiệu Năng & Chiến Lược Đánh Index Database (Task 3C)

> **Người thực hiện**: Pham Duc Anh  
> **Môi trường đo lường**: PostgreSQL 16 Alpine, Docker Container  
> **Kích thước dữ liệu kiểm thử**: 1.000 Users, 100.000 Todos

---

## 1. Bảng Tổng Hợp Hiệu Năng (Benchmark Summary Table)

Đo đạc bằng câu lệnh `EXPLAIN ANALYZE` trên tập dữ liệu **100.000 bản ghi** trong bảng `todos`:

| # | Truy Vấn (Query Scenario) | Trước Khi Đánh Index (Before) | Sau Khi Đánh Index (After) | Plan Trước (Scan Type) | Plan Sau (Scan Type) | Tỷ Lệ Cải Thiện (Speedup) |
|---|---|:---:|:---:|:---:|:---:|:---:|
| **Q1** | **Pagination List**: `WHERE user_id = ? LIMIT 20 OFFSET 0` | `2.041 ms` | `0.260 ms` | `Seq Scan` (Quét 14.856 dòng) | `Bitmap Index Scan` | **Nhanh hơn ~8x** |
| **Q2** | **Sorted List**: `WHERE user_id = ? ORDER BY created_at DESC LIMIT 20` | `12.705 ms` | `0.166 ms` | `Seq Scan` + `Sort (top-N heapsort)` (Quét 99.854 dòng) | `Index Scan Backward` (Không cần sort) | **Nhanh hơn ~76x** |
| **Q3** | **Count Todos**: `SELECT COUNT(*) WHERE user_id = ?` | `10.571 ms` | `0.068 ms` | `Seq Scan` (Quét toàn bộ 100.000 dòng) | `Index Only Scan` (Heap Fetches: 0) | **Nhanh hơn ~155x** |
| **Q4** | **Filter & Sort**: `WHERE user_id = ? AND completed = false ORDER BY created_at DESC` | `10.718 ms` | `0.096 ms` | `Seq Scan` + `Sort` (Quét 99.931 dòng) | `Index Scan Backward` | **Nhanh hơn ~111x** |

> **Nhận xét**: Trước khi đánh index, hầu hết các query (Q2, Q3, Q4) đều phải quét tuần tự (`Seq Scan`) toàn bộ 100.000 dòng trên bảng `todos` rồi mới lọc và sắp xếp trong bộ nhớ RAM (heapsort). Sau khi đánh index, thời gian thực thi của tất cả các truy vấn đều giảm xuống **dưới 0.3 ms** (cải thiện từ **8x đến 155x**).

---

## 2. Chi Tiết Các Index Đã Thêm (Alembic Migration)

Migration file: `backend/alembic/versions/b1820d9e8314_add_todo_performance_indexes.py`

### 2.1 Index 1: `ix_todos_user_id_created_at`
- **Các cột**: `(user_id, created_at)`
- **Mục đích**: Tối ưu cho truy vấn lấy danh sách todo của user sắp xếp theo thời gian tạo mới nhất (`ORDER BY created_at DESC`). Nhờ cấu trúc B-Tree lưu sẵn thứ tự theo `user_id` rồi đến `created_at`, PostgreSQL có thể đọc trực tiếp theo chiều ngược lại (`Index Scan Backward`) mà không cần tốn CPU/RAM để sort trên bộ nhớ.

### 2.2 Index 2: `ix_todos_user_id_completed_created_at`
- **Các cột**: `(user_id, completed, created_at)`
- **Mục đích**: 
  - Tối ưu cho truy vấn lọc theo trạng thái công việc (ví dụ: lấy danh sách các việc chưa hoàn thành `completed = false`).
  - Phục vụ truy vấn đếm `COUNT(*)` cực nhanh nhờ cơ chế **Index Only Scan** (PostgreSQL chỉ cần đếm trên cây index mà không cần truy xuất vào khối dữ liệu bảng trên đĩa, `Heap Fetches = 0`).

---

## 3. Nhật Ký Chi Tiết `EXPLAIN ANALYZE` (Execution Plans)

### 3.1 Truy vấn Q2: Lấy danh sách todo sắp xếp theo thời gian tạo
```sql
EXPLAIN ANALYZE SELECT * FROM todos 
WHERE user_id = 'c8e5ac51-8065-4bdb-8226-1bbfddd391ce' 
ORDER BY created_at DESC LIMIT 20 OFFSET 0;
```

#### Trước khi có Index (Execution Time: 12.705 ms):
```text
Limit  (cost=3959.07..3959.12 rows=20 width=186) (actual time=12.658..12.661 rows=20 loops=1)
  ->  Sort  (cost=3959.07..3959.45 rows=153 width=186) (actual time=12.657..12.658 rows=20 loops=1)
        Sort Key: created_at DESC
        Sort Method: top-N heapsort  Memory: 35kB
        ->  Seq Scan on todos  (cost=0.00..3955.00 rows=153 width=186) (actual time=0.166..12.527 rows=146 loops=1)
              Filter: (user_id = 'c8e5ac51-8065-4bdb-8226-1bbfddd391ce'::uuid)
              Rows Removed by Filter: 99854
Planning Time: 0.175 ms
Execution Time: 12.705 ms
```

#### Sau khi có Index (Execution Time: 0.166 ms):
```text
Limit  (cost=0.42..79.20 rows=20 width=186) (actual time=0.042..0.140 rows=20 loops=1)
  ->  Index Scan Backward using ix_todos_user_id_created_at on todos  (cost=0.42..603.09 rows=153 width=186) (actual time=0.042..0.138 rows=20 loops=1)
        Index Cond: (user_id = 'c8e5ac51-8065-4bdb-8226-1bbfddd391ce'::uuid)
Planning Time: 0.170 ms
Execution Time: 0.166 ms
```

---

### 3.2 Truy vấn Q3: Đếm số lượng todo của User
```sql
EXPLAIN ANALYZE SELECT count(*) FROM todos 
WHERE user_id = 'c8e5ac51-8065-4bdb-8226-1bbfddd391ce';
```

#### Trước khi có Index (Execution Time: 10.571 ms):
```text
Aggregate  (cost=3955.38..3955.39 rows=1 width=8) (actual time=10.550..10.552 rows=1 loops=1)
  ->  Seq Scan on todos  (cost=0.00..3955.00 rows=153 width=0) (actual time=0.122..10.484 rows=146 loops=1)
        Filter: (user_id = 'c8e5ac51-8065-4bdb-8226-1bbfddd391ce'::uuid)
        Rows Removed by Filter: 99854
Planning Time: 0.127 ms
Execution Time: 10.571 ms
```

#### Sau khi có Index (Execution Time: 0.068 ms):
```text
Aggregate  (cost=7.48..7.49 rows=1 width=8) (actual time=0.048..0.048 rows=1 loops=1)
  ->  Index Only Scan using ix_todos_user_id_completed_created_at on todos  (cost=0.42..7.10 rows=153 width=0) (actual time=0.031..0.040 rows=146 loops=1)
        Index Cond: (user_id = 'c8e5ac51-8065-4bdb-8226-1bbfddd391ce'::uuid)
        Heap Fetches: 0
Planning Time: 0.083 ms
Execution Time: 0.068 ms
```

---

## 4. Phân Tích Đánh Đổi Kỹ Thuật (Index Trade-offs)

Mặc dù index giúp tốc độ đọc tăng vọt từ 8x đến 155x, việc sử dụng index luôn đi kèm các chi phí đánh đổi (trade-offs) cần cân nhắc trong môi trường thực tế:

### 4.1 Chi Phí Ghi (Write Latency Overhead)
- **Cơ chế**: Khi thực hiện `INSERT`, `UPDATE` (trên các cột nằm trong index) hoặc `DELETE`, database không chỉ ghi dữ liệu vào bảng chính (Heap table) mà còn phải cập nhật lại cấu trúc cây B-Tree của các index liên quan.
- **Tác động**: Thao tác ghi có thể chậm hơn từ 5% - 15% tùy thuộc vào số lượng index trên bảng. Tuy nhiên, trong ứng dụng Todo, tỷ lệ đọc (Read) thường gấp 10-20 lần tỷ lệ ghi (Write), nên việc chấp nhận độ trễ ghi rất nhỏ để đổi lấy tốc độ đọc vượt trội là hoàn toàn hợp lý.

### 4.2 Chi Phí Lưu Trữ Đĩa (Storage Overhead)
- **Cơ chế**: Mỗi index là một cấu trúc dữ liệu riêng biệt chiếm dung lượng trên ổ đĩa và trong bộ nhớ RAM buffer pool.
- **Đo lường thực tế**: Với 100.000 bản ghi:
  - Bảng chính `todos`: ~15 MB.
  - Index `ix_todos_user_id_created_at`: ~3.2 MB.
  - Index `ix_todos_user_id_completed_created_at`: ~3.8 MB.
- **Chiến lược**: Tránh đánh quá nhiều index dư thừa; ưu tiên các **composite index** có thể dùng chung cho nhiều kiểu truy vấn khác nhau theo quy tắc tiền tố bên trái (Leftmost Prefix Rule).

### 4.3 An Toàn Khi Migration Trên Production (Migration Safety)
- **Vấn đề rủi ro**: Trong PostgreSQL, lệnh `CREATE INDEX` thông thường sẽ chiếm giữ khóa `SHARE` trên bảng, **ngăn chặn toàn bộ các thao tác `INSERT`, `UPDATE`, `DELETE`** trong suốt thời gian tạo index. Với bảng có hàng triệu bản ghi, việc này có thể gây treo hệ thống hoặc timeout request người dùng (downtime).
- **Giải pháp Production**:
  - Luôn sử dụng cú pháp **`CREATE INDEX CONCURRENTLY`** trong PostgreSQL:
    ```sql
    CREATE INDEX CONCURRENTLY ix_todos_user_id_created_at ON todos (user_id, created_at);
    ```
  - Cờ `CONCURRENTLY` cho phép PostgreSQL tạo index trong nền mà không khóa bảng ghi, hệ thống vẫn phục vụ người dùng bình thường trong suốt quá trình chạy migration.
  - Trong Alembic, cần thiết lập transaction block phù hợp:
    ```python
    with op.get_context().autocommit_block():
        op.create_index('ix_todos_user_id_created_at', 'todos', ['user_id', 'created_at'], postgresql_concurrently=True)
    ```
