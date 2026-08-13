from sqlalchemy import text
from app.workflow.workflow_session import workflow_engine

def run_migrations():
    alter_sql = """
    ALTER TABLE workflow.bpmn_definition 
    ADD COLUMN IF NOT EXISTS name VARCHAR(200),
    ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'Draft',
    ADD COLUMN IF NOT EXISTS updated_on TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ADD COLUMN IF NOT EXISTS published_on TIMESTAMP,
    ADD COLUMN IF NOT EXISTS tags VARCHAR(500);
    """
    with workflow_engine.connect() as connection:
        trans = connection.begin()
        try:
            print("Applying schema alterations to workflow.bpmn_definition...")
            connection.execute(text(alter_sql))
            trans.commit()
            print("Migrations successfully applied!")
        except Exception as e:
            trans.rollback()
            print(f"Migration execution failed: {str(e)}")
            raise e

if __name__ == "__main__":
    run_migrations()
