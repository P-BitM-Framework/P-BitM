import unittest

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.pool import StaticPool

from schema_migrations import MIGRATIONS, apply_schema_migrations


class SchemaMigrationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    """
                    CREATE TABLE sending_profiles (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL
                    )
                    """
                )
            )

    def tearDown(self):
        self.engine.dispose()

    def test_adds_ignore_cert_errors_to_an_existing_database(self):
        apply_schema_migrations(self.engine)

        columns = {
            column["name"]
            for column in inspect(self.engine).get_columns("sending_profiles")
        }
        self.assertIn("ignore_cert_errors", columns)

        with self.engine.connect() as connection:
            default_value = connection.execute(
                text(
                    "SELECT dflt_value FROM pragma_table_info("
                    "'sending_profiles') "
                    "WHERE name = 'ignore_cert_errors'"
                )
            ).scalar_one()
        self.assertEqual(default_value, "0")

    def test_is_idempotent_and_records_the_migration_once(self):
        apply_schema_migrations(self.engine)
        apply_schema_migrations(self.engine)

        with self.engine.connect() as connection:
            count = connection.execute(
                text("SELECT COUNT(*) FROM schema_migrations")
            ).scalar_one()
        self.assertEqual(count, len(MIGRATIONS))


class TargetCompanyMigrationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    """
                    CREATE TABLE target_lists (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL
                    )
                    """
                )
            )
            connection.execute(
                text(
                    """
                    CREATE TABLE targets (
                        id TEXT PRIMARY KEY,
                        target_list_id TEXT NOT NULL,
                        email TEXT NOT NULL,
                        company TEXT
                    )
                    """
                )
            )
            connection.execute(
                text(
                    """
                    CREATE TABLE campaigns (
                        id TEXT PRIMARY KEY,
                        target_list_id TEXT
                    )
                    """
                )
            )
            connection.execute(
                text(
                    """
                    CREATE TABLE victims (
                        id TEXT PRIMARY KEY,
                        campaign_id TEXT NOT NULL,
                        email TEXT NOT NULL
                    )
                    """
                )
            )
            connection.execute(
                text("INSERT INTO target_lists (id, name) VALUES ('tl1', 'Acme')")
            )
            connection.execute(
                text(
                    "INSERT INTO targets (id, target_list_id, email, company) "
                    "VALUES ('t1', 'tl1', 'a@acme.test', 'Acme Corp')"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO campaigns (id, target_list_id) "
                    "VALUES ('c1', 'tl1')"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO victims (id, campaign_id, email) "
                    "VALUES ('v1', 'c1', 'a@acme.test')"
                )
            )

    def tearDown(self):
        self.engine.dispose()

    def test_backfills_target_list_and_victim_company_from_existing_targets(self):
        apply_schema_migrations(self.engine)

        with self.engine.connect() as connection:
            list_company = connection.execute(
                text("SELECT company FROM target_lists WHERE id = 'tl1'")
            ).scalar_one()
            victim_company = connection.execute(
                text("SELECT company FROM victims WHERE id = 'v1'")
            ).scalar_one()

        self.assertEqual(list_company, "Acme Corp")
        self.assertEqual(victim_company, "Acme Corp")


class CampaignProtocolMigrationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        with self.engine.begin() as connection:
            connection.execute(
                text(
                    """
                    CREATE TABLE campaigns (
                        id TEXT PRIMARY KEY,
                        protocol TEXT,
                        advanced_options JSON
                    )
                    """
                )
            )
            connection.execute(
                text(
                    """
                    INSERT INTO campaigns (id, protocol, advanced_options)
                    VALUES (
                        'legacy',
                        'webrtc',
                        '{"protocol":"webrtc","selkies":{"video_quality":"medium"}}'
                    )
                    """
                )
            )

    def tearDown(self):
        self.engine.dispose()

    def test_renames_legacy_protocol_in_columns_and_json(self):
        apply_schema_migrations(self.engine)

        with self.engine.connect() as connection:
            row = connection.execute(
                text(
                    "SELECT protocol, advanced_options FROM campaigns "
                    "WHERE id = 'legacy'"
                )
            ).one()

        self.assertEqual(row.protocol, "selkies")
        self.assertIn('"protocol":"selkies"', row.advanced_options)


if __name__ == "__main__":
    unittest.main()
