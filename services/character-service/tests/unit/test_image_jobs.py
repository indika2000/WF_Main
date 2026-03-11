"""Unit tests for image_jobs — job queue CRUD and lifecycle."""

import pytest

from app.models.creature import (
    Attributes,
    Classification,
    CreatureCard,
    CreatureImages,
    Identity,
    Presentation,
    Source,
)
from app.services.image_jobs import (
    claim_next_job,
    complete_job,
    ensure_image_jobs,
    fail_job,
    get_creature_image_status,
)


def _make_creature(**overrides) -> CreatureCard:
    defaults = {
        "identity": Identity(
            creature_id="WF-v1-RARE-FOREST-ELF-8A4C91B2",
            creature_signature="RARE|FOREST|ELF|GROVE_ELF|EARTH|MEDIUM|CAUTIOUS|MOSSBOUND",
        ),
        "source": Source(
            canonical_id="EAN_13|5012345678900|WILDERNESS_FRIENDS|v1",
            code_type="EAN_13",
            raw_value="5012345678900",
        ),
        "classification": Classification(
            rarity="RARE",
            biome="FOREST",
            family="NATURE_SPIRIT",
            species="ELF",
            sub_type="GROVE_ELF",
            element="EARTH",
            temperament="CAUTIOUS",
            size="MEDIUM",
            variant="MOSSBOUND",
        ),
        "presentation": Presentation(
            name="Frostborn Ice Dragon",
            title="The Warden of Hollow Pines",
            primary_color="Emerald",
            secondary_color="Amber",
            sigil="leaf",
            frame_style="natural",
        ),
        "attributes": Attributes(
            power=55, defense=40, agility=70,
            wisdom=65, ferocity=30, magic=75, luck=45,
        ),
    }
    defaults.update(overrides)
    return CreatureCard(**defaults)


@pytest.fixture
async def creature_in_db(test_db):
    """Insert a creature into the test DB and return it."""
    creature = _make_creature()
    await test_db.creatures.insert_one(creature.to_db_dict())
    return creature


class TestEnsureImageJobs:
    async def test_creates_three_jobs(self, test_db, creature_in_db):
        created = await ensure_image_jobs(test_db, creature_in_db, "user-1")
        assert created is True

        jobs = await test_db.image_generation_jobs.find(
            {"creature_id": creature_in_db.identity.creature_id}
        ).to_list(length=10)
        assert len(jobs) == 3

        image_types = {j["image_type"] for j in jobs}
        assert image_types == {"card", "headshot_color", "headshot_pencil"}

    async def test_card_has_priority_1(self, test_db, creature_in_db):
        await ensure_image_jobs(test_db, creature_in_db, "user-1")
        card_job = await test_db.image_generation_jobs.find_one(
            {"creature_id": creature_in_db.identity.creature_id, "image_type": "card"}
        )
        assert card_job["priority"] == 1

    async def test_headshots_have_no_reference_initially(self, test_db, creature_in_db):
        await ensure_image_jobs(test_db, creature_in_db, "user-1")
        headshot = await test_db.image_generation_jobs.find_one(
            {"creature_id": creature_in_db.identity.creature_id, "image_type": "headshot_color"}
        )
        assert headshot["reference_image_id"] is None

    async def test_no_duplicate_jobs(self, test_db, creature_in_db):
        await ensure_image_jobs(test_db, creature_in_db, "user-1")
        created_again = await ensure_image_jobs(test_db, creature_in_db, "user-1")
        assert created_again is False

        jobs = await test_db.image_generation_jobs.find(
            {"creature_id": creature_in_db.identity.creature_id}
        ).to_list(length=10)
        assert len(jobs) == 3

    async def test_sets_artist_id_on_creature(self, test_db, creature_in_db):
        await ensure_image_jobs(test_db, creature_in_db, "user-1")
        doc = await test_db.creatures.find_one(
            {"identity.creature_id": creature_in_db.identity.creature_id}
        )
        assert doc["images"]["artist_id"] is not None

    async def test_jobs_have_prompts(self, test_db, creature_in_db):
        await ensure_image_jobs(test_db, creature_in_db, "user-1")
        jobs = await test_db.image_generation_jobs.find(
            {"creature_id": creature_in_db.identity.creature_id}
        ).to_list(length=10)
        for job in jobs:
            assert len(job["prompt"]) > 50  # Prompts should be substantial


class TestClaimNextJob:
    async def test_claims_card_first(self, test_db, creature_in_db):
        await ensure_image_jobs(test_db, creature_in_db, "user-1")

        job = await claim_next_job(test_db)
        assert job is not None
        assert job["image_type"] == "card"
        assert job["status"] == "processing"
        assert job["attempts"] == 1

    async def test_headshots_not_claimed_without_reference(self, test_db, creature_in_db):
        await ensure_image_jobs(test_db, creature_in_db, "user-1")

        # Claim the card job
        card_job = await claim_next_job(test_db)
        assert card_job["image_type"] == "card"

        # Headshots should not be claimable yet (no reference_image_id)
        next_job = await claim_next_job(test_db)
        assert next_job is None

    async def test_returns_none_when_empty(self, test_db):
        job = await claim_next_job(test_db)
        assert job is None


class TestCompleteJob:
    async def test_marks_completed(self, test_db, creature_in_db):
        await ensure_image_jobs(test_db, creature_in_db, "user-1")
        card_job = await claim_next_job(test_db)

        await complete_job(test_db, card_job["job_id"], "img-001")

        updated = await test_db.image_generation_jobs.find_one({"job_id": card_job["job_id"]})
        assert updated["status"] == "completed"
        assert updated["result_image_id"] == "img-001"
        assert updated["completed_at"] is not None

    async def test_updates_creature_images(self, test_db, creature_in_db):
        await ensure_image_jobs(test_db, creature_in_db, "user-1")
        card_job = await claim_next_job(test_db)

        await complete_job(test_db, card_job["job_id"], "img-001")

        creature_doc = await test_db.creatures.find_one(
            {"identity.creature_id": creature_in_db.identity.creature_id}
        )
        assert creature_doc["images"]["card"] == "img-001"

    async def test_card_completion_unlocks_headshots(self, test_db, creature_in_db):
        await ensure_image_jobs(test_db, creature_in_db, "user-1")
        card_job = await claim_next_job(test_db)

        await complete_job(test_db, card_job["job_id"], "card-img-001")

        # Headshot jobs should now have reference_image_id set
        headshot_color = await test_db.image_generation_jobs.find_one(
            {"creature_id": creature_in_db.identity.creature_id, "image_type": "headshot_color"}
        )
        assert headshot_color["reference_image_id"] == "card-img-001"

        # Should now be claimable
        next_job = await claim_next_job(test_db)
        assert next_job is not None
        assert next_job["image_type"] in ("headshot_color", "headshot_pencil")


class TestFailJob:
    async def test_requeues_on_first_failure(self, test_db, creature_in_db):
        await ensure_image_jobs(test_db, creature_in_db, "user-1")
        card_job = await claim_next_job(test_db)

        await fail_job(test_db, card_job["job_id"], "API error")

        updated = await test_db.image_generation_jobs.find_one({"job_id": card_job["job_id"]})
        assert updated["status"] == "pending"
        assert updated["error"] == "API error"

    async def test_permanently_fails_after_max_attempts(self, test_db, creature_in_db):
        await ensure_image_jobs(test_db, creature_in_db, "user-1")

        # Claim and fail 3 times
        for _ in range(3):
            job = await claim_next_job(test_db)
            if job:
                await fail_job(test_db, job["job_id"], "API error")

        card_job = await test_db.image_generation_jobs.find_one(
            {"creature_id": creature_in_db.identity.creature_id, "image_type": "card"}
        )
        assert card_job["status"] == "failed"


class TestGetCreatureImageStatus:
    async def test_returns_all_jobs(self, test_db, creature_in_db):
        await ensure_image_jobs(test_db, creature_in_db, "user-1")

        status = await get_creature_image_status(
            test_db, creature_in_db.identity.creature_id
        )
        assert len(status) == 3
        assert all(j["status"] == "pending" for j in status)

    async def test_returns_empty_for_unknown_creature(self, test_db):
        status = await get_creature_image_status(test_db, "nonexistent")
        assert status == []
