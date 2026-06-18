from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.agent import AnswerResult
from app.api.deps import get_answerer, get_pipeline_runner
from app.db import get_session
from app.main import app
from app.pipeline.pipeline import run_pipeline

AUDIO = {"file": ("meeting.m4a", b"fake-audio-bytes", "audio/m4a")}


@pytest.fixture
async def api_client(db_session: AsyncSession, pipeline_fakes) -> AsyncIterator[AsyncClient]:
    async def override_session():
        yield db_session

    async def fake_runner(meeting_id, audio):
        await run_pipeline(db_session, meeting_id, audio, **pipeline_fakes)

    async def fake_answer(question, session, *, agent_session=None):
        return AnswerResult(answer=f"Answer about: {question}", sources=[])

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_pipeline_runner] = lambda: fake_runner
    app.dependency_overrides[get_answerer] = lambda: fake_answer

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


async def _upload(client: AsyncClient) -> str:
    resp = await client.post("/meetings", files=AUDIO)
    assert resp.status_code == 202
    return resp.json()["id"]


async def test_upload_processes_meeting_and_detail_is_complete(api_client: AsyncClient):
    mid = await _upload(api_client)  # fake runner processes inline
    resp = await api_client.get(f"/meetings/{mid}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "done"
    assert body["title"] == "Release planning"
    assert len(body["segments"]) == 2
    assert body["summary"]["key_decisions"] == ["Ship Friday"]
    assert len(body["action_items"]) == 1
    assert "auth" in body["topics"]
    assert body["talk_time"]


async def test_list_meetings(api_client: AsyncClient):
    await _upload(api_client)
    resp = await api_client.get("/meetings")
    assert resp.status_code == 200
    titles = [m["title"] for m in resp.json()]
    assert "Release planning" in titles


async def test_rename_speakers(api_client: AsyncClient):
    mid = await _upload(api_client)
    resp = await api_client.patch(
        f"/meetings/{mid}/speakers", json={"names": {"0": "Alice", "1": "Bob"}}
    )
    assert resp.status_code == 200
    names = {s["label"]: s["display_name"] for s in resp.json()["speakers"]}
    assert names == {0: "Alice", 1: "Bob"}


async def test_toggle_action_item(api_client: AsyncClient):
    mid = await _upload(api_client)
    detail = (await api_client.get(f"/meetings/{mid}")).json()
    item_id = detail["action_items"][0]["id"]
    resp = await api_client.patch(f"/action-items/{item_id}", json={"completed": True})
    assert resp.status_code == 200
    assert resp.json()["completed"] is True


async def test_ask_returns_answer(api_client: AsyncClient):
    resp = await api_client.post("/ask", json={"question": "What did we decide?"})
    assert resp.status_code == 200
    assert "What did we decide?" in resp.json()["answer"]


async def test_analytics_after_upload(api_client: AsyncClient):
    await _upload(api_client)
    resp = await api_client.get("/analytics")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_meetings"] >= 1
    assert body["action_items"]["total"] >= 1


async def test_missing_meeting_returns_404(api_client: AsyncClient):
    resp = await api_client.get("/meetings/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


async def test_empty_upload_rejected(api_client: AsyncClient):
    resp = await api_client.post("/meetings", files={"file": ("empty.m4a", b"", "audio/m4a")})
    assert resp.status_code == 400


async def test_non_audio_upload_rejected(api_client: AsyncClient):
    resp = await api_client.post(
        "/meetings", files={"file": ("notes.txt", b"hello world", "text/plain")}
    )
    assert resp.status_code == 415


async def test_ready_probe_checks_db(api_client: AsyncClient):
    resp = await api_client.get("/ready")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ready"


async def test_speaker_name_can_be_cleared(api_client: AsyncClient):
    mid = await _upload(api_client)
    await api_client.patch(f"/meetings/{mid}/speakers", json={"names": {"0": "Alice"}})
    resp = await api_client.patch(f"/meetings/{mid}/speakers", json={"names": {"0": ""}})
    assert resp.status_code == 200
    names = {s["label"]: s["display_name"] for s in resp.json()["speakers"]}
    assert names[0] is None


async def _ids(client: AsyncClient) -> set[str]:
    return {m["id"] for m in (await client.get("/meetings")).json()}


async def test_delete_archives_and_hides_meeting(api_client: AsyncClient):
    mid = await _upload(api_client)
    assert mid in await _ids(api_client)

    resp = await api_client.delete(f"/meetings/{mid}")
    assert resp.status_code == 204
    assert mid not in await _ids(api_client)
    assert (await api_client.get(f"/meetings/{mid}")).status_code == 404
    assert (await api_client.delete(f"/meetings/{mid}")).status_code == 404  # already gone


async def test_restore_brings_meeting_back(api_client: AsyncClient):
    mid = await _upload(api_client)
    await api_client.delete(f"/meetings/{mid}")
    resp = await api_client.post(f"/meetings/{mid}/restore")
    assert resp.status_code == 200
    assert mid in await _ids(api_client)


async def test_rename_meeting(api_client: AsyncClient):
    mid = await _upload(api_client)
    resp = await api_client.patch(f"/meetings/{mid}", json={"title": "Q3 Planning"})
    assert resp.status_code == 200
    assert resp.json()["title"] == "Q3 Planning"


async def test_add_and_delete_action_item(api_client: AsyncClient):
    mid = await _upload(api_client)
    created = await api_client.post(
        f"/meetings/{mid}/action-items", json={"task": "Book the venue", "owner": "Me"}
    )
    assert created.status_code == 201
    aid = created.json()["id"]
    items = (await api_client.get(f"/meetings/{mid}")).json()["action_items"]
    assert any(a["id"] == aid for a in items)

    deleted = await api_client.delete(f"/action-items/{aid}")
    assert deleted.status_code == 204
    items = (await api_client.get(f"/meetings/{mid}")).json()["action_items"]
    assert all(a["id"] != aid for a in items)


async def test_archived_meeting_excluded_from_analytics(api_client: AsyncClient):
    mid = await _upload(api_client)
    before = (await api_client.get("/analytics")).json()["total_meetings"]
    await api_client.delete(f"/meetings/{mid}")
    after = (await api_client.get("/analytics")).json()["total_meetings"]
    assert after == before - 1
