import asyncio
import logging
import time
from ticktick_api import TickTickAPI
from db import TickTickDB
from dotenv import load_dotenv
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TickTickDataManager:
    def __init__(self):
        load_dotenv()
        self.api = TickTickAPI()
        self.db = TickTickDB()
        self.max_retries = 3
        self.retry_delay = 60  # seconds
    
    async def sync_data(self):
        """Synchronize data from TickTick to MongoDB"""
        try:
            logger.info("Starting data synchronization...")
            
            # Sync projects
            logger.info("Fetching projects from TickTick API...")
            projects = await self._retry_with_backoff(self.api.get_projects)
            logger.info(f"Retrieved {len(projects)} projects from API")
            
            logger.info("Saving projects to database...")
            await self.db.save_projects(projects)
            logger.info(f"Successfully saved {len(projects)} projects to database")
            
            # Sync tasks
            logger.info("Fetching tasks from TickTick API...")
            tasks = await self._retry_with_backoff(self.api.get_tasks)
            logger.info(f"Retrieved {len(tasks)} tasks from API")
            
            logger.info("Saving tasks to database...")
            await self.db.save_tasks(tasks)
            logger.info(f"Successfully saved {len(tasks)} tasks to database")
            
            logger.info("Data synchronization completed successfully")
            
        except Exception as e:
            logger.error(f"Error during data synchronization: {str(e)}")
            raise
    
    async def _retry_with_backoff(self, func, *args, **kwargs):
        """Retry a function with exponential backoff"""
        for attempt in range(self.max_retries):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if "exceed_query_limit" in str(e):
                    if attempt < self.max_retries - 1:
                        wait_time = self.retry_delay * (2 ** attempt)
                        logger.warning(f"Rate limit exceeded. Waiting {wait_time} seconds before retry {attempt + 1}/{self.max_retries}")
                        await asyncio.sleep(wait_time)
                        continue
                raise

async def main():
    try:
        manager = TickTickDataManager()
        await manager.sync_data()
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        raise
    finally:
        logger.info("Database connection closed")
        await manager.db.close()

if __name__ == "__main__":
    logger.info("Starting TickTick data sync process...")
    asyncio.run(main()) 