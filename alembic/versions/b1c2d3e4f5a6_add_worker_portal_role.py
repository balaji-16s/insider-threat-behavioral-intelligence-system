"""add employee portal role and user-employee link

Revision ID: b1c2d3e4f5a6
Revises: a9f8e7d6c5b4
Create Date: 2026-09-14 12:00:00.000000

Introduces the worker (employee) portal:

- Adds the ``EMPLOYEE`` label to the ``userrole`` enum. Portal accounts
  may only ever read their own behaviour, risk score and alerts.
- Adds ``users.employee_id``, linking a login to the employee whose data
  it may display. Nullable, because the existing security-staff roles are
  authorised on role alone and need no employee record.

``ALTER TYPE ... ADD VALUE`` cannot run inside a transaction on older
PostgreSQL and the new label must not be used in the same transaction it
is added in, so it runs in an autocommit block; the column changes then
follow in the normal transactional path.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'b1c2d3e4f5a6'
down_revision: Union[str, None] = 'a9f8e7d6c5b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'EMPLOYEE'")

    op.add_column(
        'users',
        sa.Column('employee_id', postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        'ix_users_employee_id', 'users', ['employee_id'], unique=False
    )
    op.create_foreign_key(
        'fk_users_employee_id',
        'users',
        'employees',
        ['employee_id'],
        ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint('fk_users_employee_id', 'users', type_='foreignkey')
    op.drop_index('ix_users_employee_id', table_name='users')
    op.drop_column('users', 'employee_id')
    # PostgreSQL cannot drop a single enum label, so the EMPLOYEE label is
    # intentionally left in place; it is simply unused after the downgrade.
