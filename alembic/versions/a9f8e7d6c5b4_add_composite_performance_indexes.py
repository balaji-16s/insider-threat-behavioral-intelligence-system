"""add composite performance indexes

Revision ID: a9f8e7d6c5b4
Revises: 20c267c19f87
Create Date: 2026-08-13 12:00:00.000000

The most frequent query patterns join a per-employee filter with a time
window, so composite (employee_id, timestamp) indexes let PostgreSQL seek
directly instead of scanning single-column indexes:

- activity_logs(employee_id, occurred_at): every per-employee / chunked
  activity load used by threat models, baselines, anomaly detection, and
  reports.
- risk_scores(employee_id, calculated_at): the DISTINCT ON "latest score
  per employee" queries behind the dashboard, UEBA overview, and analytics.
- alerts(employee_id, status): open-alert dedup and per-employee counts.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a9f8e7d6c5b4'
down_revision: Union[str, None] = '20c267c19f87'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        'ix_activity_logs_employee_occurred',
        'activity_logs',
        ['employee_id', 'occurred_at'],
        unique=False,
    )
    op.create_index(
        'ix_risk_scores_employee_calculated',
        'risk_scores',
        ['employee_id', 'calculated_at'],
        unique=False,
    )
    op.create_index(
        'ix_alerts_employee_status',
        'alerts',
        ['employee_id', 'status'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index('ix_alerts_employee_status', table_name='alerts')
    op.drop_index('ix_risk_scores_employee_calculated', table_name='risk_scores')
    op.drop_index('ix_activity_logs_employee_occurred', table_name='activity_logs')
