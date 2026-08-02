"""
market_intelligence/ipo_service.py

Purpose: Data-access and business logic for the `ipo_listings` table
(new in Phase 8). Follows the exact same BaseService pattern as every
`database/*_service.py` file (e.g. Phase 5's SearchHistoryService
living alongside its feature module rather than in `database/`).
Since no free, keyless IPO data API exists, `seed_sample_ipos()`
provides a realistic starting dataset editable by an admin; in a real
deployment this would be replaced by a scheduled scraper/API job
writing into the same table -- the schema and every downstream page
are already built to support that without changes.
"""

from datetime import datetime, timedelta
from typing import Any

from custom_exceptions import ValidationError
from database.base_service import BaseService
from database.models import IPOListing
from logging_config import logger

VALID_STATUSES = ("UPCOMING", "OPEN", "CLOSED", "LISTED")


class IPOService(BaseService[IPOListing]):
    """CRUD and business logic for the `ipo_listings` table."""

    model = IPOListing
    pk_column = "ipo_id"

    def create_ipo(
        self,
        company_name: str,
        exchange: str = "NSE",
        issue_price_min: float | None = None,
        issue_price_max: float | None = None,
        lot_size: int | None = None,
        open_date: datetime | None = None,
        close_date: datetime | None = None,
        listing_date: datetime | None = None,
    ) -> IPOListing:
        """Create a new IPO listing entry with an automatically-derived initial status."""
        if not company_name.strip():
            raise ValidationError("company_name is required.")

        entry = IPOListing(
            company_name=company_name.strip(),
            exchange=exchange,
            issue_price_min=issue_price_min,
            issue_price_max=issue_price_max,
            lot_size=lot_size,
            open_date=open_date,
            close_date=close_date,
            listing_date=listing_date,
            status=self._derive_status(open_date, close_date, listing_date),
        )
        created = self.create(entry)
        logger.info(f"IPO listing created: {company_name}")
        return created

    @staticmethod
    def _derive_status(open_date: datetime | None, close_date: datetime | None, listing_date: datetime | None) -> str:
        """Derive UPCOMING/OPEN/CLOSED/LISTED from today's date relative to the IPO's key dates."""
        now = datetime.utcnow()
        if listing_date and now >= listing_date:
            return "LISTED"
        if close_date and now > close_date:
            return "CLOSED"
        if open_date and now >= open_date:
            return "OPEN"
        return "UPCOMING"

    def refresh_all_statuses(self) -> int:
        """Recompute and update every IPO's status based on today's date. Returns the count updated."""
        all_ipos = self.list(page_size=500)["items"]
        updated_count = 0
        for ipo in all_ipos:
            correct_status = self._derive_status(ipo.open_date, ipo.close_date, ipo.listing_date)
            if correct_status != ipo.status:
                self.update(ipo.ipo_id, {"status": correct_status})
                updated_count += 1
        if updated_count:
            logger.info(f"Refreshed status for {updated_count} IPO listing(s).")
        return updated_count

    def get_by_status(self, status: str, page: int = 1, page_size: int = 25) -> dict[str, Any]:
        """List IPOs filtered by status, most recently opened first."""
        if status not in VALID_STATUSES:
            raise ValidationError(f"status must be one of: {', '.join(VALID_STATUSES)}")
        return self.list(filters={"status": status}, sort_by="open_date", sort_direction="desc", page=page, page_size=page_size)

    def update_subscription(self, ipo_id: int, subscription_times: float, gmp: float | None = None) -> IPOListing:
        """Update an IPO's live subscription multiple and (optionally) grey market premium."""
        updates: dict[str, Any] = {"subscription_times": subscription_times}
        if gmp is not None:
            updates["gmp"] = gmp
        return self.update(ipo_id, updates)

    def seed_sample_ipos(self) -> int:
        """
        Populate the table with a realistic sample IPO calendar if it's
        currently empty -- keeps the module fully demoable without a
        live data feed. No-op (returns 0) if any IPOs already exist.
        """
        if self.count() > 0:
            return 0

        today = datetime.utcnow()
        samples = [
            {
                "company_name": "Nova Fintech Solutions Ltd.",
                "issue_price_min": 210.0, "issue_price_max": 225.0, "lot_size": 65,
                "open_date": today + timedelta(days=5), "close_date": today + timedelta(days=8),
                "listing_date": today + timedelta(days=13), "gmp": 18.0,
            },
            {
                "company_name": "Bharat Green Energy Ltd.",
                "issue_price_min": 480.0, "issue_price_max": 505.0, "lot_size": 29,
                "open_date": today - timedelta(days=1), "close_date": today + timedelta(days=2),
                "listing_date": today + timedelta(days=7), "subscription_times": 12.4, "gmp": 65.0,
            },
            {
                "company_name": "Sundar Logistics & Warehousing Ltd.",
                "issue_price_min": 95.0, "issue_price_max": 102.0, "lot_size": 140,
                "open_date": today - timedelta(days=10), "close_date": today - timedelta(days=7),
                "listing_date": today - timedelta(days=2), "subscription_times": 34.8, "gmp": 22.0,
            },
            {
                "company_name": "Krishna Pharma Labs Ltd.",
                "issue_price_min": 610.0, "issue_price_max": 640.0, "lot_size": 23,
                "open_date": today + timedelta(days=20), "close_date": today + timedelta(days=23),
                "listing_date": today + timedelta(days=28),
            },
        ]

        for sample in samples:
            self.create_ipo(**sample)

        logger.info(f"Seeded {len(samples)} sample IPO listing(s).")
        return len(samples)


ipo_service = IPOService()
