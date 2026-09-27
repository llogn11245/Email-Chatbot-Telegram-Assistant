# Thiết kế mở rộng RAG (dự kiến)

Tài liệu này mô tả các "seam" đã chừa sẵn trong code để thêm pipeline RAG ở phiên bản sau mà **không phải đổi kiến trúc**.

## Seam đã có trong code

| Thành phần | Vị trí | Vai trò |
|---|---|---|
| `Retriever` protocol + `NullRetriever` | `backend/agent/retriever.py` | Trả về `list[Document]`; hiện là no-op. |
| `get_retriever(settings)` | `backend/agent/retriever.py` | Chọn retriever theo feature flag `rag_enabled`. |
| `get_embeddings(settings)` | `backend/agent/embeddings.py` | Seam embeddings (chưa hiện thực). |
| Pipeline state | `backend/agent/pipeline/state.py` | `AgentState` có `context_docs`, `trace_id`. |
| `build_agent` / `build_context_messages` | `backend/agent/pipeline/builder.py` | Ráp agent + chèn ngữ cảnh retrieval trước câu hỏi user. |
| Tool registry | `backend/agent/tools.py` (`get_tools`) | Thêm tool mới (vd `search_knowledge_base`) tại đây. |
| `settings.features` (JSON) | `backend/storage.py` | Cờ bật/tắt + cấu hình RAG. |
| Observability | `backend/observability/` | Log retrieval/tool để debug. |

Bật RAG sẽ chỉ cần: đặt `features.rag_enabled = true`, hiện thực `VectorRetriever`, và (nếu muốn) thêm tool search.

## Nguồn dữ liệu

- **Email của user** (các tài khoản Gmail đã kết nối) — nguồn chính.
- **Tài liệu upload** (PDF/txt/md) — mở rộng sau.

## Schema DB dự kiến (thêm khi làm RAG)

> Chưa tạo bảng ở phiên bản hiện tại (tránh schema chết). Sẽ thêm kèm migration.

### `documents`
| Cột | Kiểu | Ghi chú |
|---|---|---|
| `id` | INTEGER PK | |
| `scope` | TEXT | vd `account:<id>` hoặc `global` |
| `source_type` | TEXT | `email` / `file` |
| `source_ref` | TEXT | message_id / đường dẫn |
| `title` | TEXT | |
| `content` | TEXT | nội dung đã trích |
| `metadata` | TEXT (JSON) | |
| `created_at` | DATETIME | |

### `chunks`
| Cột | Kiểu | Ghi chú |
|---|---|---|
| `id` | INTEGER PK | |
| `document_id` | INTEGER | FK → documents |
| `chunk_text` | TEXT | |
| `embedding` | BLOB | vector (float32) |
| `dim` | INTEGER | số chiều |

### `task_runs` (theo dõi ingestion)
| Cột | Kiểu |
|---|---|
| `id` | INTEGER PK |
| `task` | TEXT |
| `status` | TEXT |
| `started_at` / `finished_at` | DATETIME |
| `detail` | TEXT (JSON) |

## Vector store

Chưa chốt. Các lựa chọn:
- `sqlite-vec` (nhúng vào SQLite — gọn, hợp desktop).
- Brute-force numpy (đơn giản, đủ cho quy mô nhỏ).
- External (Chroma/FAISS) — mạnh hơn nhưng thêm dependency/đóng gói phức tạp.

`VectorRetriever` sẽ là điểm cắm duy nhất; các phần còn lại không đổi.

## Embeddings

Chưa chốt: API-based (nhẹ bundle, cần mạng) hay local (offline, nặng bundle). Hiện thực ở `backend/agent/embeddings.py`.

## Luồng khi RAG bật

```
user_text
  → get_retriever(settings).retrieve(user_text, top_k)   # VectorRetriever
  → build_context_messages() chèn system message ngữ cảnh
  → create_react_agent (tools hiện có + có thể thêm search_knowledge_base)
  → trả lời
```

## Ingestion (email → index) — gợi ý

- Job định kỳ/ theo yêu cầu: đồng bộ email mới của từng tài khoản → chunk → embeddings → lưu `documents`/`chunks`.
- Ghi `task_runs` để theo dõi; log qua `observability`.
- Chạy nền trong cùng event loop của desktop (hoặc thread riêng), có thể dùng `features` để bật/tắt.
