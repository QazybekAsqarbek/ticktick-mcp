# make requests to ticktick api and save data to database
# use caching to avoid rate limiting
# use a flexible schema for the data

import asyncio
import logging
from typing import Dict, List, Any, Optional
from ticktick_api import TickTickAPI
from db import TickTickDB
from datetime import datetime, timedelta
import sys
import os
import time
from tenacity import retry, stop_after_attempt, wait_exponential
from settings import settings

# Create logs directory if it doesn't exist
os.makedirs('/app/logs', exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),  # Log to stdout
        logging.FileHandler('/app/logs/ticktick_sync.log')  # Log to file
    ]
)
logger = logging.getLogger(__name__)

class TickTickManager:
    def __init__(self, mongo_uri: str = None):
        """Initialize TickTick manager
        
        Args:
            mongo_uri: MongoDB connection URI, defaults to settings
        """
        self.db = TickTickDB(mongo_uri)
        self.api = TickTickAPI()
        self.logger = logging.getLogger(__name__)
        
        # Get debug projects from settings
        debug_projects = settings.DEBUG_PROJECTS.split(",")
        self.debug_projects = [p.strip() for p in debug_projects if p.strip()]
        if self.debug_projects:
            self.logger.info(f"Debug mode enabled. Working with projects: {', '.join(self.debug_projects)}")
    
    async def _validate_cache(self, items: List[Dict[str, Any]], item_type: str) -> bool:
        """Validate cached items
        
        Args:
            items: List of cached items
            item_type: Type of items (tasks, projects, notes)
        
        Returns:
            bool: True if cache is valid, False otherwise
        """
        if not items:
            self.logger.warning(f"No cached {item_type} found")
            return False
        
        # Check cache expiry
        current_time = datetime.utcnow()
        for item in items:
            if item.get("cache_expiry") and item["cache_expiry"] <= current_time:
                self.logger.info(f"Cache expired for {item_type} {item.get('id')}")
                return False
        
        # Validate required fields
        required_fields = {
            "tasks": ["id", "title", "projectId", "status"],
            "projects": ["id", "name"],
            "notes": ["id", "title", "content"]
        }
        
        for item in items:
            for field in required_fields[item_type]:
                if field not in item:
                    self.logger.warning(f"Missing required field {field} in {item_type} {item.get('id')}")
                    return False
        
        return True
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def sync_tasks(self, project_id: Optional[str] = None, cache_duration: int = 300) -> None:
        """Sync tasks from TickTick API
        
        Args:
            project_id: Optional project ID to sync tasks for
            cache_duration: Cache duration in seconds (default: 5 minutes)
        """
        try:
            # Check cache first
            cached_tasks = await self.db.get_tasks(project_id=project_id)
            if await self._validate_cache(cached_tasks, "tasks"):
                self.logger.info(f"Using cached tasks for project {project_id}")
                return
            
            # Fetch from API if cache invalid
            tasks = await self.api.get_tasks(project_id)
            if tasks:
                await self.db.save_tasks(tasks, cache_duration)
                self.logger.info(f"Synced {len(tasks)} tasks for project {project_id}")
            else:
                self.logger.warning(f"No tasks found for project {project_id}")
        except Exception as e:
            self.logger.error(f"Error syncing tasks: {str(e)}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def sync_projects(self, cache_duration: int = 3600) -> None:
        """Sync projects from TickTick API
        
        Args:
            cache_duration: Cache duration in seconds (default: 1 hour)
        """
        try:
            # Check cache first
            cached_projects = await self.db.get_projects()
            if await self._validate_cache(cached_projects, "projects"):
                self.logger.info("Using cached projects")
                return
            
            # Fetch from API if cache invalid
            projects = await self.api.get_projects()
            if projects:
                await self.db.save_projects(projects, cache_duration)
                self.logger.info(f"Synced {len(projects)} projects")
            else:
                self.logger.warning("No projects found")
        except Exception as e:
            self.logger.error(f"Error syncing projects: {str(e)}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def sync_notes(self, cache_duration: int = 300) -> None:
        """Sync notes from TickTick API
        
        Args:
            cache_duration: Cache duration in seconds (default: 5 minutes)
        """
        try:
            # Check cache first
            cached_notes = await self.db.get_notes()
            if await self._validate_cache(cached_notes, "notes"):
                self.logger.info("Using cached notes")
                return
            
            # Fetch from API if cache invalid
            notes = await self.api.get_notes()
            if notes:
                await self.db.save_notes(notes, cache_duration)
                self.logger.info(f"Synced {len(notes)} notes")
            else:
                self.logger.warning("No notes found")
        except Exception as e:
            self.logger.error(f"Error syncing notes: {str(e)}")
            raise
    
    async def sync_all(self, cache_duration: int = 300) -> None:
        """Sync all data from TickTick API
        
        Args:
            cache_duration: Cache duration in seconds (default: 5 minutes)
        """
        try:
            # Sync projects first
            await self.sync_projects(cache_duration)
            
            # Get all projects
            projects = await self.db.get_projects()
            
            if self.debug_projects:
                # Filter projects based on DEBUG_PROJECTS
                projects = [p for p in projects if p.get("name") in self.debug_projects]
                if not projects:
                    self.logger.error(f"No debug projects found. Looking for: {', '.join(self.debug_projects)}")
                    return
                self.logger.info(f"Found {len(projects)} debug projects to sync")
            
            # Sync tasks for each project
            for project in projects:
                await self.sync_tasks(project_id=project["id"], cache_duration=cache_duration)
            
            self.logger.info("Successfully synced all data")
        except Exception as e:
            self.logger.error(f"Error syncing all data: {str(e)}")
            raise
    
    def close(self):
        """Close database connection"""
        try:
            self.db.close()
            self.logger.info("Closed database connection")
        except Exception as e:
            self.logger.error(f"Error closing database connection: {str(e)}")
            raise

async def main():
    logger.info("Starting TickTick data sync process...")
    manager = TickTickManager()
    try:
        # First try a partial sync
        try:
            await manager.sync_all(cache_duration=300)
        except Exception as e:
            logger.warning(f"Partial sync failed, attempting full sync: {str(e)}")
            # If partial sync fails, try a full sync
            await manager.sync_all(cache_duration=300)
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())