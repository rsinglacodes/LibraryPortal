from typing import Sequence, Union  
import sqlalchemy as sa  
from alembic import op  
revision = 'd1e2f3a4b5c6'  
down_revision = 'c7d8e9f0a1b2'  
branch_labels = None  
depends_on = None  
def upgrade():  
    op.add_column('borrow_transactions', sa.Column('damage_detected', sa.Boolean(), server_default='false', nullable=False))  
    op.add_column('borrow_transactions', sa.Column('damage_types', sa.String(512), nullable=True))  
    op.add_column('borrow_transactions', sa.Column('damage_image', sa.Text(), nullable=True))  
def downgrade():  
    op.drop_column('borrow_transactions', 'damage_image')  
    op.drop_column('borrow_transactions', 'damage_types')  
    op.drop_column('borrow_transactions', 'damage_detected')  
