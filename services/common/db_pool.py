"""
Database Connection Pool
Thread-safe PostgreSQL connection pooling with retry logic
"""

import psycopg2
from psycopg2 import pool, extras
from typing import Optional, Any, List, Tuple
import time
import logging
from contextlib import contextmanager

from .config import DatabaseConfig

logger = logging.getLogger(__name__)


class DatabasePool:
    """Thread-safe database connection pool"""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self._pool: Optional[pool.ThreadedConnectionPool] = None
        self._initialize_pool()
    
    def _initialize_pool(self):
        """Initialize connection pool"""
        try:
            self._pool = pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=self.config.pool_size,
                dsn=self.config.url
            )
            logger.info(f"Database pool initialized (size: {self.config.pool_size})")
        except Exception as e:
            logger.error(f"Failed to initialize database pool: {e}")
            raise
    
    @contextmanager
    def get_connection(self, retries: int = 3):
        """
        Get database connection from pool with retry logic
        
        Usage:
            with db_pool.get_connection() as conn:
                cur = conn.cursor()
                cur.execute("SELECT * FROM table")
        """
        conn = None
        attempt = 0
        
        while attempt < retries:
            try:
                conn = self._pool.getconn()
                yield conn
                conn.commit()
                return
            except psycopg2.OperationalError as e:
                attempt += 1
                logger.warning(f"Database connection error (attempt {attempt}/{retries}): {e}")
                
                if conn:
                    try:
                        conn.rollback()
                    except:
                        pass
                
                if attempt < retries:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise
            except Exception as e:
                if conn:
                    try:
                        conn.rollback()
                    except:
                        pass
                logger.error(f"Database error: {e}")
                raise
            finally:
                if conn:
                    self._pool.putconn(conn)
    
    @contextmanager
    def get_cursor(self, retries: int = 3):
        """
        Get database cursor with automatic connection management
        
        Usage:
            with db_pool.get_cursor() as cur:
                cur.execute("SELECT * FROM table")
                results = cur.fetchall()
        """
        with self.get_connection(retries=retries) as conn:
            cur = conn.cursor()
            try:
                yield cur
            finally:
                cur.close()
    
    def execute(self, query: str, params: Optional[tuple] = None, retries: int = 3) -> None:
        """Execute a query without returning results"""
        with self.get_cursor(retries=retries) as cur:
            cur.execute(query, params)
    
    def fetchone(self, query: str, params: Optional[tuple] = None, retries: int = 3) -> Optional[tuple]:
        """Execute query and fetch one result"""
        with self.get_cursor(retries=retries) as cur:
            cur.execute(query, params)
            return cur.fetchone()
    
    def fetchall(self, query: str, params: Optional[tuple] = None, retries: int = 3) -> List[tuple]:
        """Execute query and fetch all results"""
        with self.get_cursor(retries=retries) as cur:
            cur.execute(query, params)
            return cur.fetchall()
    
    def execute_values(self, query: str, values: List[tuple], retries: int = 3) -> None:
        """
        Execute bulk insert using psycopg2.extras.execute_values
        
        Args:
            query: SQL query with %s placeholder for VALUES
            values: List of tuples to insert
        """
        with self.get_cursor(retries=retries) as cur:
            extras.execute_values(cur, query, values)
    
    def call_function(self, function_name: str, params: Optional[tuple] = None, retries: int = 3) -> Any:
        """
        Call a PostgreSQL function
        
        Args:
            function_name: Name of the function
            params: Function parameters
        
        Returns:
            Function result
        """
        with self.get_cursor(retries=retries) as cur:
            if params:
                placeholders = ', '.join(['%s'] * len(params))
                query = f"SELECT {function_name}({placeholders})"
                cur.execute(query, params)
            else:
                query = f"SELECT {function_name}()"
                cur.execute(query)
            
            result = cur.fetchone()
            return result[0] if result else None
    
    def update_job_status(self, job_id: int, new_status: str, worker_id: str, 
                         error_message: Optional[str] = None) -> bool:
        """
        Update job status using database function
        
        Args:
            job_id: Job ID
            new_status: New status
            worker_id: Worker ID
            error_message: Optional error message
        
        Returns:
            True if successful
        """
        return self.call_function(
            'update_job_status',
            (job_id, new_status, worker_id, error_message)
        )
    
    def get_next_jobs(self, stage: str, required_status: str, 
                     worker_id: str, batch_size: int = 100) -> List[Tuple[int, int]]:
        """
        Get next jobs for processing using database function
        
        Args:
            stage: Pipeline stage
            required_status: Required job status
            worker_id: Worker ID
            batch_size: Number of jobs to fetch
        
        Returns:
            List of (job_id, email_id) tuples
        """
        with self.get_cursor() as cur:
            cur.execute(
                "SELECT * FROM get_next_jobs(%s, %s, %s, %s)",
                (stage, required_status, worker_id, batch_size)
            )
            return cur.fetchall()
    
    def health_check(self) -> bool:
        """Check database connection health"""
        try:
            result = self.fetchone("SELECT 1")
            return result is not None
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    def close(self):
        """Close all connections in pool"""
        if self._pool:
            self._pool.closeall()
            logger.info("Database pool closed")


# Global pool instance
_pool: Optional[DatabasePool] = None


def get_db_pool(config: Optional[DatabaseConfig] = None) -> DatabasePool:
    """Get global database pool instance"""
    global _pool
    if _pool is None:
        if config is None:
            from .config import get_config
            config = get_config().database
        _pool = DatabasePool(config)
    return _pool


def close_db_pool():
    """Close global database pool"""
    global _pool
    if _pool:
        _pool.close()
        _pool = None
