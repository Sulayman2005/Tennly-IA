<?php
declare(strict_types=1);

namespace DoctrineMigrations;

use Doctrine\DBAL\Schema\Schema;
use Doctrine\Migrations\AbstractMigration;

/**
 * Crée les tables player_snapshot et player_head_to_head, utilisées par le
 * comparateur de joueurs (voir PlayerComparisonService.php) et rafraîchies
 * chaque jour par ml-service/import_upcoming_matches.py. Ces deux tables ne
 * sont pas mappées comme entités Doctrine (accès en SQL brut des deux
 * côtés, PHP et Python), donc jamais générées automatiquement par
 * doctrine:migrations:diff — d'où cette migration écrite à la main,
 * capturant le schéma qui existait déjà de façon non versionnée (créé
 * manuellement sur le VPS le 08/09/2026 en diagnostiquant l'échec du
 * script d'import).
 */
final class Version20260908150000 extends AbstractMigration
{
    public function getDescription(): string
    {
        return 'Crée player_snapshot et player_head_to_head (comparateur de joueurs, hors Doctrine ORM)';
    }

    public function up(Schema $schema): void
    {
        $this->addSql('CREATE TABLE player_snapshot (
            player_id INT NOT NULL,
            serve_score DOUBLE DEFAULT NULL,
            return_score DOUBLE DEFAULT NULL,
            momentum DOUBLE DEFAULT NULL,
            recent_form DOUBLE DEFAULT NULL,
            days_rest DOUBLE DEFAULT NULL,
            fatigue_minutes DOUBLE DEFAULT NULL,
            upset_rate DOUBLE DEFAULT NULL,
            winrate_vs_left DOUBLE DEFAULT NULL,
            winrate_vs_right DOUBLE DEFAULT NULL,
            updated_at DATETIME NOT NULL,
            PRIMARY KEY(player_id),
            CONSTRAINT fk_snapshot_player FOREIGN KEY (player_id) REFERENCES player (id) ON DELETE CASCADE
        ) DEFAULT CHARACTER SET utf8mb4');
        $this->addSql('CREATE TABLE player_head_to_head (
            player_low_id INT NOT NULL,
            player_high_id INT NOT NULL,
            wins_low INT NOT NULL,
            wins_high INT NOT NULL,
            updated_at DATETIME NOT NULL,
            PRIMARY KEY(player_low_id, player_high_id),
            CONSTRAINT fk_h2h_low FOREIGN KEY (player_low_id) REFERENCES player (id) ON DELETE CASCADE,
            CONSTRAINT fk_h2h_high FOREIGN KEY (player_high_id) REFERENCES player (id) ON DELETE CASCADE
        ) DEFAULT CHARACTER SET utf8mb4');
    }

    public function down(Schema $schema): void
    {
        $this->addSql('DROP TABLE player_head_to_head');
        $this->addSql('DROP TABLE player_snapshot');
    }
}
