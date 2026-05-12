"""add percentual comissao

Revision ID: 798b99282d0f
Revises:
Create Date: 2026-05-02 22:20:53.979338

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '798b99282d0f'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():

    with op.batch_alter_table('interacoes', schema=None) as batch_op:

        batch_op.create_foreign_key(
            "fk_interacoes_usuario_id",
            "usuarios",
            ["usuario_id"],
            ["id"]
        )

    with op.batch_alter_table('leads', schema=None) as batch_op:

        batch_op.create_foreign_key(
            "fk_leads_usuario_id",
            "usuarios",
            ["usuario_id"],
            ["id"]
        )

    with op.batch_alter_table('mensagens_whatsapp', schema=None) as batch_op:

        batch_op.alter_column(
            'mensagem',
            existing_type=sa.TEXT(),
            nullable=True
        )

    with op.batch_alter_table('tarefas', schema=None) as batch_op:

        batch_op.create_foreign_key(
            "fk_tarefas_usuario_id",
            "usuarios",
            ["usuario_id"],
            ["id"]
        )


def downgrade():

    with op.batch_alter_table('usuarios', schema=None) as batch_op:

        batch_op.drop_column(
            'percentual_comissao'
        )

    with op.batch_alter_table('tarefas', schema=None) as batch_op:

        batch_op.drop_constraint(
            "fk_tarefas_usuario_id",
            type_='foreignkey'
        )

    with op.batch_alter_table('mensagens_whatsapp', schema=None) as batch_op:

        batch_op.alter_column(
            'mensagem',
            existing_type=sa.TEXT(),
            nullable=False
        )

    with op.batch_alter_table('leads', schema=None) as batch_op:

        batch_op.drop_constraint(
            "fk_leads_usuario_id",
            type_='foreignkey'
        )

    with op.batch_alter_table('interacoes', schema=None) as batch_op:

        batch_op.drop_constraint(
            "fk_interacoes_usuario_id",
            type_='foreignkey'
        )