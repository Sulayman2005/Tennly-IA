<?php

declare(strict_types=1);

namespace DoctrineMigrations;

use Doctrine\DBAL\Schema\Schema;
use Doctrine\Migrations\AbstractMigration;

/**
 * Schéma initial : joueurs, matchs, pronostics, formules, abonnements,
 * utilisateurs (cahier des charges section 4, entités du domaine).
 *
 * Dialecte MySQL/MariaDB (adapté depuis la version PostgreSQL d'origine, à la
 * demande de l'utilisateur qui a déjà un serveur MySQL via XAMPP/WAMP). Cette
 * version-ci n'a PAS pu être rejouée contre un vrai serveur MySQL dans cet
 * environnement (aucun serveur MySQL/MariaDB installable ici, réseau bloqué —
 * voir README), contrairement à la version PostgreSQL qui, elle, a été
 * exécutée avec succès contre une instance réelle. Relis les messages
 * d'erreur de `doctrine:migrations:migrate` attentivement si quelque chose
 * ne passe pas ici : c'est la partie la moins vérifiée du projet.
 */
final class Version20260101000000 extends AbstractMigration
{
    public function getDescription(): string
    {
        return 'Schéma initial Tennly IA : player, tennis_match, prediction, plan, subscription, app_user, refresh_token.';
    }

    public function up(Schema $schema): void
    {
        $this->addSql(<<<'SQL'
            CREATE TABLE app_user (
                id CHAR(36) NOT NULL,
                email VARCHAR(180) NOT NULL,
                roles JSON NOT NULL,
                password VARCHAR(255) NOT NULL,
                first_name VARCHAR(100) NOT NULL,
                last_name VARCHAR(100) NOT NULL,
                created_at DATETIME NOT NULL,
                PRIMARY KEY(id)
            ) ENGINE = InnoDB DEFAULT CHARACTER SET utf8mb4
        SQL);
        $this->addSql('CREATE UNIQUE INDEX uniq_user_email ON app_user (email)');

        $this->addSql(<<<'SQL'
            CREATE TABLE plan (
                id INT AUTO_INCREMENT NOT NULL,
                code VARCHAR(30) NOT NULL,
                name VARCHAR(100) NOT NULL,
                price_cents INT NOT NULL,
                currency VARCHAR(3) NOT NULL,
                billing_period VARCHAR(255) NOT NULL,
                stripe_price_id VARCHAR(120) DEFAULT NULL,
                active TINYINT(1) NOT NULL,
                PRIMARY KEY(id)
            ) ENGINE = InnoDB DEFAULT CHARACTER SET utf8mb4
        SQL);
        $this->addSql('CREATE UNIQUE INDEX uniq_plan_code ON plan (code)');

        $this->addSql(<<<'SQL'
            CREATE TABLE player (
                id INT AUTO_INCREMENT NOT NULL,
                full_name VARCHAR(150) NOT NULL,
                country_code VARCHAR(3) DEFAULT NULL,
                atp_wta_rank INT DEFAULT NULL,
                elo_overall DOUBLE PRECISION NOT NULL,
                elo_hard DOUBLE PRECISION NOT NULL,
                elo_clay DOUBLE PRECISION NOT NULL,
                elo_grass DOUBLE PRECISION NOT NULL,
                dominant_hand VARCHAR(1) DEFAULT NULL,
                birth_date DATE DEFAULT NULL,
                external_ref VARCHAR(60) DEFAULT NULL,
                photo_url VARCHAR(255) DEFAULT NULL,
                PRIMARY KEY(id)
            ) ENGINE = InnoDB DEFAULT CHARACTER SET utf8mb4
        SQL);
        $this->addSql('CREATE UNIQUE INDEX uniq_player_external_ref ON player (external_ref)');

        $this->addSql(<<<'SQL'
            CREATE TABLE tennis_match (
                id INT AUTO_INCREMENT NOT NULL,
                player_a_id INT NOT NULL,
                player_b_id INT NOT NULL,
                winner_id INT DEFAULT NULL,
                tournament_name VARCHAR(150) NOT NULL,
                round VARCHAR(60) NOT NULL,
                surface VARCHAR(255) NOT NULL,
                scheduled_at DATETIME NOT NULL,
                status VARCHAR(255) NOT NULL,
                score_text VARCHAR(60) DEFAULT NULL,
                PRIMARY KEY(id)
            ) ENGINE = InnoDB DEFAULT CHARACTER SET utf8mb4
        SQL);
        $this->addSql('CREATE INDEX idx_match_player_a ON tennis_match (player_a_id)');
        $this->addSql('CREATE INDEX idx_match_player_b ON tennis_match (player_b_id)');
        $this->addSql('CREATE INDEX idx_match_scheduled_at ON tennis_match (scheduled_at)');

        $this->addSql(<<<'SQL'
            CREATE TABLE prediction (
                id INT AUTO_INCREMENT NOT NULL,
                match_id INT NOT NULL,
                favorite_player_id INT NOT NULL,
                probability_favorite DOUBLE PRECISION NOT NULL,
                confidence_level VARCHAR(255) NOT NULL,
                model_version VARCHAR(30) NOT NULL,
                computed_at DATETIME NOT NULL,
                explanation_factors JSON NOT NULL,
                radar_profile JSON NOT NULL,
                market_odds_favorite DOUBLE PRECISION DEFAULT NULL,
                value_edge DOUBLE PRECISION DEFAULT NULL,
                PRIMARY KEY(id)
            ) ENGINE = InnoDB DEFAULT CHARACTER SET utf8mb4
        SQL);
        $this->addSql('CREATE UNIQUE INDEX uniq_prediction_match ON prediction (match_id)');

        $this->addSql(<<<'SQL'
            CREATE TABLE subscription (
                id INT AUTO_INCREMENT NOT NULL,
                user_id CHAR(36) NOT NULL,
                plan_id INT NOT NULL,
                status VARCHAR(255) NOT NULL,
                stripe_customer_id VARCHAR(120) DEFAULT NULL,
                stripe_subscription_id VARCHAR(120) DEFAULT NULL,
                current_period_end DATETIME DEFAULT NULL,
                created_at DATETIME NOT NULL,
                canceled_at DATETIME DEFAULT NULL,
                PRIMARY KEY(id)
            ) ENGINE = InnoDB DEFAULT CHARACTER SET utf8mb4
        SQL);
        $this->addSql('CREATE INDEX idx_subscription_user ON subscription (user_id)');

        $this->addSql(<<<'SQL'
            CREATE TABLE refresh_token (
                id INT AUTO_INCREMENT NOT NULL,
                refresh_token VARCHAR(128) NOT NULL,
                username VARCHAR(255) NOT NULL,
                valid DATETIME NOT NULL,
                PRIMARY KEY(id)
            ) ENGINE = InnoDB DEFAULT CHARACTER SET utf8mb4
        SQL);
        $this->addSql('CREATE UNIQUE INDEX uniq_refresh_token ON refresh_token (refresh_token)');

        $this->addSql('ALTER TABLE tennis_match ADD CONSTRAINT fk_match_player_a FOREIGN KEY (player_a_id) REFERENCES player (id)');
        $this->addSql('ALTER TABLE tennis_match ADD CONSTRAINT fk_match_player_b FOREIGN KEY (player_b_id) REFERENCES player (id)');
        $this->addSql('ALTER TABLE tennis_match ADD CONSTRAINT fk_match_winner FOREIGN KEY (winner_id) REFERENCES player (id)');
        $this->addSql('ALTER TABLE prediction ADD CONSTRAINT fk_prediction_match FOREIGN KEY (match_id) REFERENCES tennis_match (id)');
        $this->addSql('ALTER TABLE prediction ADD CONSTRAINT fk_prediction_favorite FOREIGN KEY (favorite_player_id) REFERENCES player (id)');
        $this->addSql('ALTER TABLE subscription ADD CONSTRAINT fk_subscription_user FOREIGN KEY (user_id) REFERENCES app_user (id)');
        $this->addSql('ALTER TABLE subscription ADD CONSTRAINT fk_subscription_plan FOREIGN KEY (plan_id) REFERENCES plan (id)');
    }

    public function down(Schema $schema): void
    {
        $this->addSql('ALTER TABLE subscription DROP FOREIGN KEY fk_subscription_user');
        $this->addSql('ALTER TABLE subscription DROP FOREIGN KEY fk_subscription_plan');
        $this->addSql('ALTER TABLE prediction DROP FOREIGN KEY fk_prediction_match');
        $this->addSql('ALTER TABLE prediction DROP FOREIGN KEY fk_prediction_favorite');
        $this->addSql('ALTER TABLE tennis_match DROP FOREIGN KEY fk_match_player_a');
        $this->addSql('ALTER TABLE tennis_match DROP FOREIGN KEY fk_match_player_b');
        $this->addSql('ALTER TABLE tennis_match DROP FOREIGN KEY fk_match_winner');
        $this->addSql('DROP TABLE subscription');
        $this->addSql('DROP TABLE refresh_token');
        $this->addSql('DROP TABLE prediction');
        $this->addSql('DROP TABLE tennis_match');
        $this->addSql('DROP TABLE player');
        $this->addSql('DROP TABLE plan');
        $this->addSql('DROP TABLE app_user');
    }
}
