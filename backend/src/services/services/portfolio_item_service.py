from __future__ import annotations

import logging
import os
from typing import List, Dict, Any, Optional
from uuid import UUID

from supabase import Client, create_client

from api.models.portfolio_item_models import PortfolioItem, PortfolioItemCreate, PortfolioItemUpdate

logger = logging.getLogger(__name__)


class PortfolioItemServiceError(Exception):
    """Raised when portfolio item operations fail."""


class PortfolioItemService:
    """Service for managing portfolio items in Supabase."""

    def __init__(self, supabase_url: Optional[str] = None, supabase_key: Optional[str] = None) -> None:
        self.supabase_url = supabase_url or os.getenv("SUPABASE_URL")
        self.supabase_key = (
            supabase_key
            or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
            or os.getenv("SUPABASE_KEY")
            or os.getenv("SUPABASE_ANON_KEY")
        )

        if not self.supabase_url or not self.supabase_key:
            raise PortfolioItemServiceError("Supabase credentials not configured.")

        try:
            self.client: Client = create_client(self.supabase_url, self.supabase_key)
        except Exception as exc:
            raise PortfolioItemServiceError(f"Failed to initialize Supabase client: {exc}") from exc

    def _handle_response(self, response: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Handle Supabase response data."""
        if response is not None:
            return response
        logger.error("Supabase operation returned None")
        raise PortfolioItemServiceError("Supabase operation returned None")

    def get_all_portfolio_items(self, user_id: UUID) -> List[PortfolioItem]:
        try:
            response = self.client.from_('portfolio_items').select('*').eq('user_id', str(user_id)).execute()
            data = self._handle_response(response.data)
            return [PortfolioItem(**item) for item in data]
        except Exception as exc:
            raise PortfolioItemServiceError(f"Failed to retrieve portfolio items for user {user_id}: {exc}") from exc

    def get_portfolio_item(self, user_id: UUID, item_id: UUID) -> Optional[PortfolioItem]:
        try:
            response = self.client.from_('portfolio_items').select('*').eq('user_id', str(user_id)).eq('id', str(item_id)).execute()
            data = self._handle_response(response.data)
            if data:
                return PortfolioItem(**data[0])
            return None
        except Exception as exc:
            raise PortfolioItemServiceError(f"Failed to retrieve portfolio item {item_id} for user {user_id}: {exc}") from exc

    def create_portfolio_item(self, user_id: UUID, item: PortfolioItemCreate) -> PortfolioItem:
        try:
            new_item_data = item.model_dump()
            new_item_data['user_id'] = str(user_id)
            response = self.client.from_('portfolio_items').insert(new_item_data).execute()
            data = self._handle_response(response.data)
            return PortfolioItem(**data[0])
        except Exception as exc:
            raise PortfolioItemServiceError(f"Failed to create portfolio item for user {user_id}: {exc}") from exc

    def update_portfolio_item(self, user_id: UUID, item_id: UUID, item: PortfolioItemUpdate) -> Optional[PortfolioItem]:
        try:
            update_data = item.model_dump(exclude_unset=True)
            if not update_data:
                return self.get_portfolio_item(user_id, item_id) # No data to update, return current item

            response = self.client.from_('portfolio_items').update(update_data).eq('user_id', str(user_id)).eq('id', str(item_id)).execute()
            data = self._handle_response(response.data)
            if data:
                return PortfolioItem(**data[0])
            return None
        except Exception as exc:
            raise PortfolioItemServiceError(f"Failed to update portfolio item {item_id} for user {user_id}: {exc}") from exc

    def delete_portfolio_item(self, user_id: UUID, item_id: UUID) -> bool:
        try:
            response = self.client.from_('portfolio_items').delete().eq('user_id', str(user_id)).eq('id', str(item_id)).execute()
            data = self._handle_response(response.data)
            return bool(data)
        except Exception as exc:
            raise PortfolioItemServiceError(f"Failed to delete portfolio item {item_id} for user {user_id}: {exc}") from exc
