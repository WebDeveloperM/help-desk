"""full_schema_migration

Revision ID: 002
Revises: 001
Create Date: 2026-01-16 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create ENUM types
    op.execute("""
        CREATE TYPE role AS ENUM (
            'user',
            'department_head',
            'executor',
            'admin'
        )
    """)
    
    op.execute("""
        CREATE TYPE ticket_status AS ENUM (
            'draft',
            'pending_approval',
            'rejected',
            'approved',
            'assigned',
            'in_progress',
            'waiting_info',
            'completed',
            'closed'
        )
    """)
    
    op.execute("""
        CREATE TYPE ticket_priority AS ENUM (
            'low',
            'normal',
            'high',
            'urgent'
        )
    """)
    
    op.execute("""
        CREATE TYPE notification_type AS ENUM (
            'ticket_created',
            'ticket_approved',
            'ticket_rejected',
            'ticket_assigned',
            'ticket_completed',
            'comment_added',
            'status_changed'
        )
    """)
    
    op.execute("""
        CREATE TYPE action_type AS ENUM (
            'created',
            'updated',
            'status_changed',
            'assigned',
            'comment_added',
            'approved',
            'rejected',
            'completed',
            'closed'
        )
    """)
    
    # Create departments table
    op.create_table(
        'departments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('name_uz', sa.String(length=255), nullable=True),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('parent_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('head_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('ad_path', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['parent_id'], ['departments.id'], ondelete='SET NULL', name='fk_parent_department'),
        sa.UniqueConstraint('code', name='uq_departments_code')
    )
    op.create_index('ix_departments_parent_id', 'departments', ['parent_id'], unique=False)
    op.create_index('ix_departments_code', 'departments', ['code'], unique=False)
    op.create_index('ix_departments_is_active', 'departments', ['is_active'], unique=False)
    
    # Update users table - add new columns
    op.add_column('users', sa.Column('ad_username', sa.String(length=100), nullable=True))
    op.add_column('users', sa.Column('full_name_uz', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('department_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('users', sa.Column('position', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('position_uz', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('phone', sa.String(length=50), nullable=True))
    op.add_column('users', sa.Column('ad_guid', sa.String(length=100), nullable=True))
    op.add_column('users', sa.Column('ad_distinguished_name', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('last_sync_at', sa.DateTime(timezone=True), nullable=True))
    
    # Update full_name to be NOT NULL (change existing NULL to empty string first)
    op.execute("UPDATE users SET full_name = '' WHERE full_name IS NULL")
    op.alter_column('users', 'full_name',
                    existing_type=sa.String(length=510),
                    nullable=False,
                    type_=sa.String(length=255))
    
    # Remove old columns that are no longer needed
    op.drop_column('users', 'username')
    op.drop_column('users', 'first_name')
    op.drop_column('users', 'last_name')
    
    # Create indexes for new columns
    op.create_index('ix_users_ad_username', 'users', ['ad_username'], unique=True)
    op.create_index('ix_users_department_id', 'users', ['department_id'], unique=False)
    op.create_index('ix_users_ad_guid', 'users', ['ad_guid'], unique=False)
    
    # Create foreign key for department_id
    op.create_foreign_key('fk_user_department', 'users', 'departments', ['department_id'], ['id'], ondelete='SET NULL')
    
    # Create unique constraint for ad_username
    op.create_unique_constraint('uq_users_ad_username', 'users', ['ad_username'])
    
    # Create user_roles table
    op.create_table(
        'user_roles',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role', postgresql.ENUM('user', 'department_head', 'executor', 'admin', name='role', create_type=False), nullable=False),
        sa.Column('department_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('user_id', 'role', 'department_id', name='pk_user_roles'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE', name='fk_user_role_user'),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ondelete='CASCADE', name='fk_user_role_department'),
        sa.UniqueConstraint('user_id', 'role', 'department_id', name='uq_user_roles')
    )
    op.create_index('ix_user_roles_user_id', 'user_roles', ['user_id'], unique=False)
    op.create_index('ix_user_roles_role', 'user_roles', ['role'], unique=False)
    op.create_index('ix_user_roles_department_id', 'user_roles', ['department_id'], unique=False)
    
    # Create foreign key for departments.head_user_id (after users table is updated)
    op.create_foreign_key('fk_head_user', 'departments', 'users', ['head_user_id'], ['id'], ondelete='SET NULL')
    
    # Create function for updating updated_at
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    # Create triggers for updated_at
    op.execute("""
        CREATE TRIGGER update_departments_updated_at 
            BEFORE UPDATE ON departments
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)
    
    op.execute("""
        CREATE TRIGGER update_user_roles_updated_at 
            BEFORE UPDATE ON user_roles
            FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """)
    
    # Create function for generating ticket numbers
    op.execute("""
        CREATE OR REPLACE FUNCTION generate_ticket_number()
        RETURNS TRIGGER AS $$
        DECLARE
            prefix TEXT;
            year TEXT;
            counter INTEGER;
            new_number TEXT;
        BEGIN
            SELECT value INTO prefix FROM system_settings WHERE key = 'ticket_number_prefix';
            IF prefix IS NULL THEN
                prefix := 'HD';
            END IF;
            
            year := TO_CHAR(NOW(), 'YYYY');
            
            SELECT COUNT(*) + 1 INTO counter
            FROM tickets
            WHERE EXTRACT(YEAR FROM created_at) = EXTRACT(YEAR FROM NOW());
            
            new_number := prefix || '-' || year || '-' || LPAD(counter::TEXT, 5, '0');
            
            NEW.ticket_number := new_number;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)


def downgrade() -> None:
    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS update_user_roles_updated_at ON user_roles")
    op.execute("DROP TRIGGER IF EXISTS update_departments_updated_at ON departments")
    
    # Drop functions
    op.execute("DROP FUNCTION IF EXISTS generate_ticket_number()")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column()")
    
    # Drop foreign keys
    op.drop_constraint('fk_head_user', 'departments', type_='foreignkey')
    op.drop_constraint('fk_user_department', 'users', type_='foreignkey')
    
    # Drop user_roles table
    op.drop_index('ix_user_roles_department_id', table_name='user_roles')
    op.drop_index('ix_user_roles_role', table_name='user_roles')
    op.drop_index('ix_user_roles_user_id', table_name='user_roles')
    op.drop_table('user_roles')
    
    # Revert users table changes
    op.drop_constraint('uq_users_ad_username', 'users', type_='unique')
    op.drop_index('ix_users_ad_guid', table_name='users')
    op.drop_index('ix_users_department_id', table_name='users')
    op.drop_index('ix_users_ad_username', table_name='users')
    
    # Add back old columns
    op.add_column('users', sa.Column('username', sa.String(length=255), nullable=False, server_default=''))
    op.add_column('users', sa.Column('first_name', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('last_name', sa.String(length=255), nullable=True))
    
    # Revert full_name to nullable
    op.alter_column('users', 'full_name',
                    existing_type=sa.String(length=255),
                    nullable=True,
                    type_=sa.String(length=510))
    
    # Remove new columns
    op.drop_column('users', 'last_sync_at')
    op.drop_column('users', 'ad_distinguished_name')
    op.drop_column('users', 'ad_guid')
    op.drop_column('users', 'phone')
    op.drop_column('users', 'position_uz')
    op.drop_column('users', 'position')
    op.drop_column('users', 'department_id')
    op.drop_column('users', 'full_name_uz')
    op.drop_column('users', 'ad_username')
    
    # Drop departments table
    op.drop_index('ix_departments_is_active', table_name='departments')
    op.drop_index('ix_departments_code', table_name='departments')
    op.drop_index('ix_departments_parent_id', table_name='departments')
    op.drop_table('departments')
    
    # Drop ENUM types
    op.execute("DROP TYPE IF EXISTS action_type")
    op.execute("DROP TYPE IF EXISTS notification_type")
    op.execute("DROP TYPE IF EXISTS ticket_priority")
    op.execute("DROP TYPE IF EXISTS ticket_status")
    op.execute("DROP TYPE IF EXISTS role")
