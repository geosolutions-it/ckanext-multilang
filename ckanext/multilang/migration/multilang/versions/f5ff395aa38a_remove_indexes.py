"""Remove indexes

Revision ID: f5ff395aa38a
Revises: 
Create Date: 2022-04-21 19:25:10.936135

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f5ff395aa38a'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Using op.execute in order not to raise error in case the index/constraint is not there
    op.execute('DROP INDEX IF EXISTS ix_package_multilang_text')
    op.execute('DROP INDEX IF EXISTS ix_group_multilang_text')
    op.execute('DROP INDEX IF EXISTS ix_resource_multilang_text')
    op.execute('DROP INDEX IF EXISTS ix_tag_multilang_text')


def downgrade():
    op.create_index('ix_package_multilang_text', 'package_multilang', ['text'])
    op.create_index('ix_group_multilang_text', 'group_multilang', ['text'])
    op.create_index('ix_resource_multilang_text', 'resource_multilang', ['text'])
    op.create_index('ix_tag_multilang_text', 'tag_multilang', ['text'])
