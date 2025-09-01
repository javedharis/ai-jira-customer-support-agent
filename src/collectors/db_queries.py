"""
Database query functions for customer support investigation
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
import asyncpg
from contextlib import asynccontextmanager

from ..core.config import DatabaseConfig


@dataclass
class QueryResult:
    query_name: str
    parameters: Dict[str, Any]
    execution_time: float
    row_count: int
    data: List[Dict[str, Any]]
    success: bool
    error: Optional[str] = None


class DatabaseQuerier:
    """Safe database query executor with predefined functions"""
    
    def __init__(self, db_config: DatabaseConfig):
        self.config = db_config
        self.logger = logging.getLogger(__name__)
        self.connection_pool = None
    
    async def initialize(self):
        """Initialize database connection pool"""
        try:
            self.connection_pool = await asyncpg.create_pool(
                self.config.connection_string,
                min_size=1,
                max_size=self.config.max_connections,
                command_timeout=self.config.query_timeout
            )
            self.logger.info("Database connection pool initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize database pool: {str(e)}")
            raise
    
    async def execute_query(self, query_function: str, parameters: Dict[str, Any]) -> QueryResult:
        """Execute a predefined query function"""
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Get the query function
            if not hasattr(self, query_function):
                raise ValueError(f"Unknown query function: {query_function}")
            
            func = getattr(self, query_function)
            
            # Execute the function
            result_data = await func(**parameters)
            
            execution_time = asyncio.get_event_loop().time() - start_time
            
            return QueryResult(
                query_name=query_function,
                parameters=parameters,
                execution_time=execution_time,
                row_count=len(result_data) if result_data else 0,
                data=result_data or [],
                success=True
            )
            
        except Exception as e:
            execution_time = asyncio.get_event_loop().time() - start_time
            self.logger.error(f"Query {query_function} failed: {str(e)}")
            
            return QueryResult(
                query_name=query_function,
                parameters=parameters,
                execution_time=execution_time,
                row_count=0,
                data=[],
                success=False,
                error=str(e)
            )
    
    @asynccontextmanager
    async def _get_connection(self):
        """Get database connection from pool"""
        if not self.connection_pool:
            await self.initialize()
        
        async with self.connection_pool.acquire() as connection:
            yield connection
    
    async def get_user_account_info(self, user_id: Optional[str] = None, email: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get user account information"""
        if not user_id and not email:
            raise ValueError("Either user_id or email must be provided")
        
        async with self._get_connection() as conn:
            if user_id:
                query = """
                    SELECT 
                        id, email, username, first_name, last_name, 
                        created_at, last_login, is_active, is_verified,
                        account_type, subscription_status
                    FROM users 
                    WHERE id = $1 OR username = $1
                """
                rows = await conn.fetch(query, user_id)
            else:
                query = """
                    SELECT 
                        id, email, username, first_name, last_name, 
                        created_at, last_login, is_active, is_verified,
                        account_type, subscription_status
                    FROM users 
                    WHERE email = $1
                """
                rows = await conn.fetch(query, email)
        
        return [dict(row) for row in rows]
    
    async def get_user_transactions(self, user_id: str, days_back: int = 30) -> List[Dict[str, Any]]:
        """Get user transaction history"""
        start_date = datetime.now() - timedelta(days=days_back)
        
        async with self._get_connection() as conn:
            query = """
                SELECT 
                    t.id, t.user_id, t.transaction_type, t.amount, 
                    t.currency, t.status, t.created_at, t.updated_at,
                    t.description, t.reference_id, t.gateway_response
                FROM transactions t
                WHERE t.user_id = $1 AND t.created_at >= $2
                ORDER BY t.created_at DESC
            """
            rows = await conn.fetch(query, user_id, start_date)
        
        return [dict(row) for row in rows]
    
    async def get_system_errors(self, hours_back: int = 24, error_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recent system errors"""
        start_time = datetime.now() - timedelta(hours=hours_back)
        
        async with self._get_connection() as conn:
            if error_type:
                query = """
                    SELECT 
                        e.id, e.error_type, e.error_message, e.stack_trace,
                        e.user_id, e.request_id, e.created_at, e.resolved_at,
                        e.severity, e.component, e.environment
                    FROM system_errors e
                    WHERE e.created_at >= $1 AND e.error_type ILIKE $2
                    ORDER BY e.created_at DESC
                    LIMIT 1000
                """
                rows = await conn.fetch(query, start_time, f"%{error_type}%")
            else:
                query = """
                    SELECT 
                        e.id, e.error_type, e.error_message, e.stack_trace,
                        e.user_id, e.request_id, e.created_at, e.resolved_at,
                        e.severity, e.component, e.environment
                    FROM system_errors e
                    WHERE e.created_at >= $1
                    ORDER BY e.created_at DESC
                    LIMIT 1000
                """
                rows = await conn.fetch(query, start_time)
        
        return [dict(row) for row in rows]
    
    async def get_feature_usage_stats(self, user_id: str, feature: Optional[str] = None, days_back: int = 7) -> List[Dict[str, Any]]:
        """Get feature usage statistics for a user"""
        start_date = datetime.now() - timedelta(days=days_back)
        
        async with self._get_connection() as conn:
            if feature:
                query = """
                    SELECT 
                        u.feature_name, u.user_id, u.usage_count, 
                        u.first_used, u.last_used, u.total_time_spent
                    FROM feature_usage u
                    WHERE u.user_id = $1 AND u.feature_name ILIKE $2 
                    AND u.last_used >= $3
                    ORDER BY u.last_used DESC
                """
                rows = await conn.fetch(query, user_id, f"%{feature}%", start_date)
            else:
                query = """
                    SELECT 
                        u.feature_name, u.user_id, u.usage_count, 
                        u.first_used, u.last_used, u.total_time_spent
                    FROM feature_usage u
                    WHERE u.user_id = $1 AND u.last_used >= $2
                    ORDER BY u.usage_count DESC, u.last_used DESC
                """
                rows = await conn.fetch(query, user_id, start_date)
        
        return [dict(row) for row in rows]
    
    async def get_configuration_settings(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user configuration settings"""
        async with self._get_connection() as conn:
            query = """
                SELECT 
                    c.setting_key, c.setting_value, c.category,
                    c.created_at, c.updated_at, c.is_default
                FROM user_configurations c
                WHERE c.user_id = $1
                ORDER BY c.category, c.setting_key
            """
            rows = await conn.fetch(query, user_id)
        
        return [dict(row) for row in rows]
    
    async def get_user_sessions(self, user_id: str, days_back: int = 7) -> List[Dict[str, Any]]:
        """Get user session information"""
        start_date = datetime.now() - timedelta(days=days_back)
        
        async with self._get_connection() as conn:
            query = """
                SELECT 
                    s.session_id, s.user_id, s.ip_address, s.user_agent,
                    s.created_at, s.expires_at, s.is_active, s.last_activity
                FROM user_sessions s
                WHERE s.user_id = $1 AND s.created_at >= $2
                ORDER BY s.created_at DESC
            """
            rows = await conn.fetch(query, user_id, start_date)
        
        return [dict(row) for row in rows]
    
    async def get_api_usage(self, user_id: str, hours_back: int = 24) -> List[Dict[str, Any]]:
        """Get API usage statistics"""
        start_time = datetime.now() - timedelta(hours=hours_back)
        
        async with self._get_connection() as conn:
            query = """
                SELECT 
                    a.endpoint, a.method, a.user_id, a.status_code,
                    a.response_time, a.created_at, a.request_size, 
                    a.response_size, a.ip_address
                FROM api_logs a
                WHERE a.user_id = $1 AND a.created_at >= $2
                ORDER BY a.created_at DESC
                LIMIT 1000
            """
            rows = await conn.fetch(query, user_id, start_time)
        
        return [dict(row) for row in rows]
    
    async def get_user_notifications(self, user_id: str, days_back: int = 7) -> List[Dict[str, Any]]:
        """Get user notifications"""
        start_date = datetime.now() - timedelta(days=days_back)
        
        async with self._get_connection() as conn:
            query = """
                SELECT 
                    n.id, n.user_id, n.type, n.title, n.message,
                    n.is_read, n.created_at, n.read_at, n.priority
                FROM notifications n
                WHERE n.user_id = $1 AND n.created_at >= $2
                ORDER BY n.created_at DESC
            """
            rows = await conn.fetch(query, user_id, start_date)
        
        return [dict(row) for row in rows]
    
    async def get_payment_issues(self, user_id: str, days_back: int = 30) -> List[Dict[str, Any]]:
        """Get payment-related issues"""
        start_date = datetime.now() - timedelta(days=days_back)
        
        async with self._get_connection() as conn:
            query = """
                SELECT 
                    p.id, p.user_id, p.payment_method, p.amount, p.currency,
                    p.status, p.failure_reason, p.gateway_error, p.created_at,
                    p.updated_at, p.retry_count
                FROM payments p
                WHERE p.user_id = $1 AND p.created_at >= $2 
                AND p.status IN ('failed', 'declined', 'error')
                ORDER BY p.created_at DESC
            """
            rows = await conn.fetch(query, user_id, start_date)
        
        return [dict(row) for row in rows]
    
    async def close(self):
        """Close database connection pool"""
        if self.connection_pool:
            await self.connection_pool.close()
            self.logger.info("Database connection pool closed")