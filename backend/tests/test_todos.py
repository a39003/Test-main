"""Todo tests."""

import pytest
from httpx import AsyncClient


async def get_auth_token(client: AsyncClient, email: str = "todo@example.com") -> str:
    """Helper to register and get auth token."""
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "password123"},
    )
    return response.json()["access_token"]


@pytest.mark.asyncio
async def test_create_todo(client: AsyncClient):
    """Test creating a new todo."""
    token = await get_auth_token(client, "create@example.com")

    response = await client.post(
        "/api/v1/todos",
        json={"title": "Test Todo", "description": "A test todo item"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Todo"
    assert data["description"] == "A test todo item"
    assert data["completed"] is False


@pytest.mark.asyncio
async def test_get_todos(client: AsyncClient):
    """Test getting todo list."""
    token = await get_auth_token(client, "list@example.com")

    # Create a todo first
    await client.post(
        "/api/v1/todos",
        json={"title": "List Todo"},
        headers={"Authorization": f"Bearer {token}"},
    )

    # Get todos
    response = await client.get(
        "/api/v1/todos",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert len(data["items"]) >= 1


@pytest.mark.asyncio
async def test_update_todo(client: AsyncClient):
    """Test updating a todo."""
    token = await get_auth_token(client, "update@example.com")

    # Create a todo
    create_response = await client.post(
        "/api/v1/todos",
        json={"title": "Update Me"},
        headers={"Authorization": f"Bearer {token}"},
    )
    todo_id = create_response.json()["id"]

    # Update it
    response = await client.put(
        f"/api/v1/todos/{todo_id}",
        json={"title": "Updated Title", "completed": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Title"


@pytest.mark.asyncio
async def test_delete_todo(client: AsyncClient):
    """Test deleting a todo."""
    token = await get_auth_token(client, "delete@example.com")

    # Create a todo
    create_response = await client.post(
        "/api/v1/todos",
        json={"title": "Delete Me"},
        headers={"Authorization": f"Bearer {token}"},
    )
    todo_id = create_response.json()["id"]

    # Delete it
    response = await client.delete(
        f"/api/v1/todos/{todo_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_get_single_todo(client: AsyncClient):
    """Test getting a single todo by ID."""
    token = await get_auth_token(client, "single@example.com")

    # Create a todo
    create_response = await client.post(
        "/api/v1/todos",
        json={"title": "Single Todo", "description": "Get me"},
        headers={"Authorization": f"Bearer {token}"},
    )
    todo_id = create_response.json()["id"]

    # Get it
    response = await client.get(
        f"/api/v1/todos/{todo_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Single Todo"


@pytest.mark.asyncio
@pytest.mark.parametrize("method", ["get", "put", "delete"])
async def test_user_cannot_access_another_users_todo(
    client: AsyncClient,
    method: str,
):
    """Read, update and delete must enforce the todo ownership boundary."""
    owner_token = await get_auth_token(client, f"owner-{method}@example.com")
    other_token = await get_auth_token(client, f"other-{method}@example.com")
    create_response = await client.post(
        "/api/v1/todos",
        json={"title": "Owner private todo", "description": "private"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    todo_id = create_response.json()["id"]
    headers = {"Authorization": f"Bearer {other_token}"}

    if method == "get":
        response = await client.get(f"/api/v1/todos/{todo_id}", headers=headers)
    elif method == "put":
        response = await client.put(
            f"/api/v1/todos/{todo_id}",
            json={"title": "Taken over"},
            headers=headers,
        )
    else:
        response = await client.delete(f"/api/v1/todos/{todo_id}", headers=headers)

    assert response.status_code in (403, 404)


@pytest.mark.asyncio
async def test_completed_can_be_toggled_from_true_to_false(client: AsyncClient):
    """False is a meaningful update value and must not be treated as absent."""
    token = await get_auth_token(client, "toggle@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    created = await client.post(
        "/api/v1/todos",
        json={"title": "Toggle me"},
        headers=headers,
    )
    todo_id = created.json()["id"]
    await client.put(
        f"/api/v1/todos/{todo_id}",
        json={"completed": True},
        headers=headers,
    )

    response = await client.put(
        f"/api/v1/todos/{todo_id}",
        json={"completed": False},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["completed"] is False


@pytest.mark.asyncio
async def test_title_only_update_preserves_description(client: AsyncClient):
    """Omitted fields must not be erased during a partial update."""
    token = await get_auth_token(client, "partial-update@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    created = await client.post(
        "/api/v1/todos",
        json={"title": "Old title", "description": "Keep this description"},
        headers=headers,
    )

    response = await client.put(
        f"/api/v1/todos/{created.json()['id']}",
        json={"title": "New title"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["description"] == "Keep this description"


@pytest.mark.asyncio
async def test_cached_todo_list_is_isolated_between_users(client: AsyncClient):
    """A cached list belonging to one user must never be returned to another."""
    owner_token = await get_auth_token(client, "cache-owner@example.com")
    other_token = await get_auth_token(client, "cache-other@example.com")
    await client.post(
        "/api/v1/todos",
        json={"title": "Secret cached todo"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    await client.get(
        "/api/v1/todos",
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    response = await client.get(
        "/api/v1/todos",
        headers={"Authorization": f"Bearer {other_token}"},
    )

    assert response.status_code == 200
    assert response.json()["items"] == []


@pytest.mark.asyncio
async def test_create_todo_invalidates_cached_list(
    client: AsyncClient,
    fake_redis,
):
    """Creating a todo must invalidate any cached list for that user."""
    token = await get_auth_token(client, "cache-create@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    await client.get("/api/v1/todos", headers=headers)
    fake_redis.deleted_keys.clear()

    response = await client.post(
        "/api/v1/todos",
        json={"title": "Invalidate the list"},
        headers=headers,
    )

    assert response.status_code == 201
    assert fake_redis.deleted_keys
