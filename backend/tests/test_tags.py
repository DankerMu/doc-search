from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models import Document, Tag
from app.models.document import document_tags
from app.services.tag_service import TagService
from sqlalchemy import insert, select
from tests.conftest import test_db  # noqa: F401


@pytest.mark.asyncio
async def test_create_tag(test_db):
    async with test_db() as session:
        service = TagService(session)
        tag = await service.create_tag("Important", "#FF0000")

        assert tag.id is not None
        assert tag.name == "Important"
        assert tag.color == "#FF0000"


@pytest.mark.asyncio
async def test_create_tag_default_color(test_db):
    async with test_db() as session:
        service = TagService(session)
        tag = await service.create_tag("Default Color")

        assert tag.color == "#3B82F6"


@pytest.mark.asyncio
async def test_get_tag(test_db):
    async with test_db() as session:
        service = TagService(session)
        created = await service.create_tag("Lookup")

        tag = await service.get_tag(created.id)
        assert tag is not None
        assert tag.name == "Lookup"


@pytest.mark.asyncio
async def test_get_tag_not_found(test_db):
    async with test_db() as session:
        service = TagService(session)
        tag = await service.get_tag(99999)
        assert tag is None


@pytest.mark.asyncio
async def test_get_tag_by_name(test_db):
    async with test_db() as session:
        service = TagService(session)
        await service.create_tag("FindMe")

        tag = await service.get_tag_by_name("FindMe")
        assert tag is not None
        assert tag.name == "FindMe"


@pytest.mark.asyncio
async def test_get_tag_by_name_not_found(test_db):
    async with test_db() as session:
        service = TagService(session)
        tag = await service.get_tag_by_name("NonExistent")
        assert tag is None


@pytest.mark.asyncio
async def test_update_tag(test_db):
    async with test_db() as session:
        service = TagService(session)
        tag = await service.create_tag("Original", "#000000")

        updated = await service.update_tag(tag.id, name="Updated", color="#FFFFFF")
        assert updated is not None
        assert updated.name == "Updated"
        assert updated.color == "#FFFFFF"


@pytest.mark.asyncio
async def test_update_tag_partial(test_db):
    async with test_db() as session:
        service = TagService(session)
        tag = await service.create_tag("PartialUpdate", "#111111")

        # Update only name
        updated = await service.update_tag(tag.id, name="NewName")
        assert updated.name == "NewName"
        assert updated.color == "#111111"  # Unchanged

        # Update only color
        updated = await service.update_tag(tag.id, color="#222222")
        assert updated.name == "NewName"  # Unchanged
        assert updated.color == "#222222"


@pytest.mark.asyncio
async def test_update_tag_not_found(test_db):
    async with test_db() as session:
        service = TagService(session)
        result = await service.update_tag(99999, name="NewName")
        assert result is None


@pytest.mark.asyncio
async def test_delete_tag(test_db):
    async with test_db() as session:
        service = TagService(session)
        tag = await service.create_tag("ToDelete")

        success = await service.delete_tag(tag.id)
        assert success is True

        deleted = await service.get_tag(tag.id)
        assert deleted is None


@pytest.mark.asyncio
async def test_delete_tag_not_found(test_db):
    async with test_db() as session:
        service = TagService(session)
        success = await service.delete_tag(99999)
        assert success is False


@pytest.mark.asyncio
async def test_delete_tag_removes_from_documents(test_db):
    async with test_db() as session:
        service = TagService(session)
        tag = await service.create_tag("ToRemove")

        # Create a document
        doc = Document(
            filename="test.pdf",
            original_name="test.pdf",
            file_type="pdf",
            file_size=100,
        )
        session.add(doc)
        await session.commit()
        await session.refresh(doc)

        # Add tag to document
        await session.execute(
            insert(document_tags).values(document_id=doc.id, tag_id=tag.id)
        )
        await session.commit()

        # Delete tag
        success = await service.delete_tag(tag.id)
        assert success is True

        # Verify tag removed from association table
        result = await session.execute(
            select(document_tags).where(document_tags.c.tag_id == tag.id)
        )
        assert result.first() is None


@pytest.mark.asyncio
async def test_list_tags(test_db):
    async with test_db() as session:
        service = TagService(session)
        await service.create_tag("Alpha")
        await service.create_tag("Beta")
        await service.create_tag("Gamma")

        tags = await service.list_tags()
        assert len(tags) >= 3
        names = [t["name"] for t in tags]
        assert "Alpha" in names
        assert "Beta" in names
        assert "Gamma" in names


@pytest.mark.asyncio
async def test_list_tags_with_document_count(test_db):
    async with test_db() as session:
        service = TagService(session)
        tag = await service.create_tag("CountMe")

        # Create documents
        for i in range(3):
            doc = Document(
                filename=f"doc{i}.pdf",
                original_name=f"doc{i}.pdf",
                file_type="pdf",
                file_size=100,
            )
            session.add(doc)
            await session.commit()
            await session.refresh(doc)

            await session.execute(
                insert(document_tags).values(document_id=doc.id, tag_id=tag.id)
            )
        await session.commit()

        tags = await service.list_tags()
        count_me_tag = next((t for t in tags if t["name"] == "CountMe"), None)
        assert count_me_tag is not None
        assert count_me_tag["document_count"] == 3


@pytest.mark.asyncio
async def test_add_tag_to_document(test_db):
    async with test_db() as session:
        service = TagService(session)
        tag = await service.create_tag("AddToDoc")

        doc = Document(
            filename="test.pdf",
            original_name="test.pdf",
            file_type="pdf",
            file_size=100,
        )
        session.add(doc)
        await session.commit()
        await session.refresh(doc)

        added = await service.add_tag_to_document(doc.id, tag.id)
        assert added is True

        # Verify in association table
        result = await session.execute(
            select(document_tags).where(
                document_tags.c.document_id == doc.id,
                document_tags.c.tag_id == tag.id,
            )
        )
        assert result.first() is not None


@pytest.mark.asyncio
async def test_add_tag_to_document_already_tagged(test_db):
    async with test_db() as session:
        service = TagService(session)
        tag = await service.create_tag("AlreadyTagged")

        doc = Document(
            filename="test.pdf",
            original_name="test.pdf",
            file_type="pdf",
            file_size=100,
        )
        session.add(doc)
        await session.commit()
        await session.refresh(doc)

        await service.add_tag_to_document(doc.id, tag.id)
        added_again = await service.add_tag_to_document(doc.id, tag.id)
        assert added_again is False


@pytest.mark.asyncio
async def test_add_tag_to_document_not_found(test_db):
    async with test_db() as session:
        service = TagService(session)
        tag = await service.create_tag("DocNotFound")

        with pytest.raises(ValueError, match="Document not found"):
            await service.add_tag_to_document(99999, tag.id)


@pytest.mark.asyncio
async def test_add_tag_to_document_tag_not_found(test_db):
    async with test_db() as session:
        service = TagService(session)

        doc = Document(
            filename="test.pdf",
            original_name="test.pdf",
            file_type="pdf",
            file_size=100,
        )
        session.add(doc)
        await session.commit()
        await session.refresh(doc)

        with pytest.raises(ValueError, match="Tag not found"):
            await service.add_tag_to_document(doc.id, 99999)


@pytest.mark.asyncio
async def test_remove_tag_from_document(test_db):
    async with test_db() as session:
        service = TagService(session)
        tag = await service.create_tag("RemoveMe")

        doc = Document(
            filename="test.pdf",
            original_name="test.pdf",
            file_type="pdf",
            file_size=100,
        )
        session.add(doc)
        await session.commit()
        await session.refresh(doc)

        await service.add_tag_to_document(doc.id, tag.id)
        removed = await service.remove_tag_from_document(doc.id, tag.id)
        assert removed is True

        # Verify removed from association table
        result = await session.execute(
            select(document_tags).where(
                document_tags.c.document_id == doc.id,
                document_tags.c.tag_id == tag.id,
            )
        )
        assert result.first() is None


@pytest.mark.asyncio
async def test_remove_tag_from_document_not_tagged(test_db):
    async with test_db() as session:
        service = TagService(session)
        tag = await service.create_tag("NotTagged")

        doc = Document(
            filename="test.pdf",
            original_name="test.pdf",
            file_type="pdf",
            file_size=100,
        )
        session.add(doc)
        await session.commit()
        await session.refresh(doc)

        removed = await service.remove_tag_from_document(doc.id, tag.id)
        assert removed is False


@pytest.mark.asyncio
async def test_remove_tag_document_not_found(test_db):
    async with test_db() as session:
        service = TagService(session)
        tag = await service.create_tag("RemoveDocNotFound")

        with pytest.raises(ValueError, match="Document not found"):
            await service.remove_tag_from_document(99999, tag.id)


@pytest.mark.asyncio
async def test_batch_add_tags(test_db):
    async with test_db() as session:
        service = TagService(session)
        tag1 = await service.create_tag("Batch1")
        tag2 = await service.create_tag("Batch2")

        # Create documents
        doc_ids = []
        for i in range(3):
            doc = Document(
                filename=f"batch{i}.pdf",
                original_name=f"batch{i}.pdf",
                file_type="pdf",
                file_size=100,
            )
            session.add(doc)
            await session.commit()
            await session.refresh(doc)
            doc_ids.append(doc.id)

        result = await service.batch_add_tags(doc_ids, [tag1.id, tag2.id])
        assert result["added"] == 6  # 3 docs * 2 tags
        assert result["skipped"] == 0


@pytest.mark.asyncio
async def test_batch_add_tags_with_existing(test_db):
    async with test_db() as session:
        service = TagService(session)
        tag = await service.create_tag("BatchExisting")

        doc = Document(
            filename="batchexist.pdf",
            original_name="batchexist.pdf",
            file_type="pdf",
            file_size=100,
        )
        session.add(doc)
        await session.commit()
        await session.refresh(doc)

        # Add tag first time
        await service.add_tag_to_document(doc.id, tag.id)

        # Batch add same tag
        result = await service.batch_add_tags([doc.id], [tag.id])
        assert result["added"] == 0
        assert result["skipped"] == 1


@pytest.mark.asyncio
async def test_batch_add_tags_invalid_tag(test_db):
    async with test_db() as session:
        service = TagService(session)

        doc = Document(
            filename="batchinvalid.pdf",
            original_name="batchinvalid.pdf",
            file_type="pdf",
            file_size=100,
        )
        session.add(doc)
        await session.commit()
        await session.refresh(doc)

        with pytest.raises(ValueError, match="Tag 99999 not found"):
            await service.batch_add_tags([doc.id], [99999])


@pytest.mark.asyncio
async def test_batch_remove_tags(test_db):
    async with test_db() as session:
        service = TagService(session)
        tag1 = await service.create_tag("BatchRem1")
        tag2 = await service.create_tag("BatchRem2")

        # Create documents and add tags
        doc_ids = []
        for i in range(2):
            doc = Document(
                filename=f"batchrem{i}.pdf",
                original_name=f"batchrem{i}.pdf",
                file_type="pdf",
                file_size=100,
            )
            session.add(doc)
            await session.commit()
            await session.refresh(doc)
            doc_ids.append(doc.id)

        await service.batch_add_tags(doc_ids, [tag1.id, tag2.id])

        result = await service.batch_remove_tags(doc_ids, [tag1.id])
        assert result["removed"] == 2  # 2 docs * 1 tag


# API Tests
@pytest.mark.asyncio
async def test_create_tag_api(test_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/tags",
            json={"name": "APITag", "color": "#FF5733"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "APITag"
        assert data["color"] == "#FF5733"
        assert data["document_count"] == 0


@pytest.mark.asyncio
async def test_create_tag_api_default_color(test_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/tags",
            json={"name": "DefaultColorAPI"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["color"] == "#3B82F6"


@pytest.mark.asyncio
async def test_create_tag_api_duplicate(test_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/tags", json={"name": "Duplicate"})
        response = await client.post("/api/tags", json={"name": "Duplicate"})
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_tag_api_invalid_color(test_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/tags",
            json={"name": "InvalidColor", "color": "not-a-color"},
        )
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_tags_api(test_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/tags", json={"name": "ListTag1"})
        await client.post("/api/tags", json={"name": "ListTag2"})

        response = await client.get("/api/tags")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        names = [t["name"] for t in data]
        assert "ListTag1" in names
        assert "ListTag2" in names


@pytest.mark.asyncio
async def test_get_tag_api(test_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_resp = await client.post("/api/tags", json={"name": "GetTag"})
        tag_id = create_resp.json()["id"]

        response = await client.get(f"/api/tags/{tag_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "GetTag"


@pytest.mark.asyncio
async def test_get_tag_api_not_found(test_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/tags/99999")
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_tag_api(test_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_resp = await client.post(
            "/api/tags", json={"name": "UpdateTag", "color": "#000000"}
        )
        tag_id = create_resp.json()["id"]

        response = await client.put(
            f"/api/tags/{tag_id}",
            json={"name": "UpdatedTag", "color": "#FFFFFF"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "UpdatedTag"
        assert data["color"] == "#FFFFFF"


@pytest.mark.asyncio
async def test_update_tag_api_not_found(test_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.put(
            "/api/tags/99999",
            json={"name": "UpdateNonexistent"},
        )
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_tag_api_duplicate_name(test_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/tags", json={"name": "ExistingName"})
        create_resp = await client.post("/api/tags", json={"name": "ToRename"})
        tag_id = create_resp.json()["id"]

        response = await client.put(
            f"/api/tags/{tag_id}",
            json={"name": "ExistingName"},
        )
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]


@pytest.mark.asyncio
async def test_delete_tag_api(test_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        create_resp = await client.post("/api/tags", json={"name": "DeleteTag"})
        tag_id = create_resp.json()["id"]

        response = await client.delete(f"/api/tags/{tag_id}")
        assert response.status_code == 200
        assert response.json()["message"] == "Tag deleted"

        get_resp = await client.get(f"/api/tags/{tag_id}")
        assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_tag_api_not_found(test_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.delete("/api/tags/99999")
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_batch_add_tags_api(test_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create tag
        tag_resp = await client.post("/api/tags", json={"name": "BatchAddAPI"})
        tag_id = tag_resp.json()["id"]

        # Upload document
        files = {"file": ("test.md", b"# Test", "text/markdown")}
        doc_resp = await client.post("/api/documents/upload", files=files)
        doc_id = doc_resp.json()["id"]

        response = await client.post(
            "/api/tags/batch-add",
            json={"document_ids": [doc_id], "tag_ids": [tag_id]},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["added"] == 1
        assert data["skipped"] == 0


@pytest.mark.asyncio
async def test_batch_add_tags_api_invalid_tag(test_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Upload document
        files = {"file": ("test.md", b"# Test", "text/markdown")}
        doc_resp = await client.post("/api/documents/upload", files=files)
        doc_id = doc_resp.json()["id"]

        response = await client.post(
            "/api/tags/batch-add",
            json={"document_ids": [doc_id], "tag_ids": [99999]},
        )
        assert response.status_code == 400


@pytest.mark.asyncio
async def test_batch_remove_tags_api(test_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create tag
        tag_resp = await client.post("/api/tags", json={"name": "BatchRemAPI"})
        tag_id = tag_resp.json()["id"]

        # Upload document
        files = {"file": ("test.md", b"# Test", "text/markdown")}
        doc_resp = await client.post("/api/documents/upload", files=files)
        doc_id = doc_resp.json()["id"]

        # Add tag
        await client.post(
            "/api/tags/batch-add",
            json={"document_ids": [doc_id], "tag_ids": [tag_id]},
        )

        response = await client.post(
            "/api/tags/batch-remove",
            json={"document_ids": [doc_id], "tag_ids": [tag_id]},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["removed"] == 1


@pytest.mark.asyncio
async def test_add_tag_to_document_api(test_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create tag
        tag_resp = await client.post("/api/tags", json={"name": "AddToDocAPI"})
        tag_id = tag_resp.json()["id"]

        # Upload document
        files = {"file": ("test.md", b"# Test", "text/markdown")}
        doc_resp = await client.post("/api/documents/upload", files=files)
        doc_id = doc_resp.json()["id"]

        response = await client.post(
            f"/api/documents/{doc_id}/tags",
            json={"tag_id": tag_id},
        )
        assert response.status_code == 200
        assert "added" in response.json()["message"]


@pytest.mark.asyncio
async def test_add_tag_to_document_api_already_tagged(test_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create tag
        tag_resp = await client.post("/api/tags", json={"name": "AlreadyTaggedAPI"})
        tag_id = tag_resp.json()["id"]

        # Upload document
        files = {"file": ("test.md", b"# Test", "text/markdown")}
        doc_resp = await client.post("/api/documents/upload", files=files)
        doc_id = doc_resp.json()["id"]

        await client.post(f"/api/documents/{doc_id}/tags", json={"tag_id": tag_id})
        response = await client.post(
            f"/api/documents/{doc_id}/tags", json={"tag_id": tag_id}
        )
        assert response.status_code == 200
        assert "already has" in response.json()["message"]


@pytest.mark.asyncio
async def test_add_tag_to_document_api_invalid_doc(test_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create tag
        tag_resp = await client.post("/api/tags", json={"name": "InvalidDocAPI"})
        tag_id = tag_resp.json()["id"]

        response = await client.post(
            "/api/documents/99999/tags",
            json={"tag_id": tag_id},
        )
        assert response.status_code == 400


@pytest.mark.asyncio
async def test_add_tag_to_document_api_invalid_tag(test_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Upload document
        files = {"file": ("test.md", b"# Test", "text/markdown")}
        doc_resp = await client.post("/api/documents/upload", files=files)
        doc_id = doc_resp.json()["id"]

        response = await client.post(
            f"/api/documents/{doc_id}/tags",
            json={"tag_id": 99999},
        )
        assert response.status_code == 400


@pytest.mark.asyncio
async def test_remove_tag_from_document_api(test_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create tag
        tag_resp = await client.post("/api/tags", json={"name": "RemFromDocAPI"})
        tag_id = tag_resp.json()["id"]

        # Upload document
        files = {"file": ("test.md", b"# Test", "text/markdown")}
        doc_resp = await client.post("/api/documents/upload", files=files)
        doc_id = doc_resp.json()["id"]

        # Add tag
        await client.post(f"/api/documents/{doc_id}/tags", json={"tag_id": tag_id})

        response = await client.delete(f"/api/documents/{doc_id}/tags/{tag_id}")
        assert response.status_code == 200
        assert "removed" in response.json()["message"]


@pytest.mark.asyncio
async def test_remove_tag_from_document_api_not_tagged(test_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create tag
        tag_resp = await client.post("/api/tags", json={"name": "NotTaggedAPI"})
        tag_id = tag_resp.json()["id"]

        # Upload document
        files = {"file": ("test.md", b"# Test", "text/markdown")}
        doc_resp = await client.post("/api/documents/upload", files=files)
        doc_id = doc_resp.json()["id"]

        response = await client.delete(f"/api/documents/{doc_id}/tags/{tag_id}")
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_remove_tag_from_document_api_invalid_doc(test_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create tag
        tag_resp = await client.post("/api/tags", json={"name": "RemInvalidDocAPI"})
        tag_id = tag_resp.json()["id"]

        response = await client.delete(f"/api/documents/99999/tags/{tag_id}")
        assert response.status_code == 400
